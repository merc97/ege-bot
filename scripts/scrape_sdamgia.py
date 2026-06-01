#!/usr/bin/env python3
"""Scraper for sdamgia.ru → TaskImport JSON format.

Usage:
  python scripts/scrape_sdamgia.py --subjects math russian --exam-types ege
  python scripts/scrape_sdamgia.py --subjects all --exam-types ege oge
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SUBJECT_MAP = {
    "math":        "math",
    "russian":     "rus",
    "physics":     "phys",
    "chemistry":   "chem",
    "biology":     "bio",
    "history":     "hist",
    "social":      "soc",
    "english":     "en",
    "informatics": "inf",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}
DELAY = 1.2  # seconds between requests


def base_url(subject: str, exam_type: str) -> str:
    return f"https://{SUBJECT_MAP[subject]}-{exam_type}.sdamgia.ru"


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    await asyncio.sleep(DELAY)
    try:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        logger.warning("HTTP %d for %s", e.response.status_code, url)
        return None
    except Exception as e:
        logger.warning("Fetch error %s: %s", url, e)
        return None


async def get_categories(client: httpx.AsyncClient, base: str) -> list[tuple[int, str, int]]:
    """Returns [(task_number, topic_name, category_id), ...]."""
    html = await fetch(client, base + "/")
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    seen_ids: set[int] = set()
    result: list[tuple[int, str, int]] = []

    for a in soup.select("a[href*='category?id=']"):
        href = a.get("href", "")
        m = re.search(r"id=(\d+)", href)
        if not m:
            continue
        cat_id = int(m.group(1))
        if cat_id in seen_ids:
            continue
        seen_ids.add(cat_id)

        text = a.get_text(" ", strip=True)
        num_m = re.search(r"(\d+)", text)
        task_number = int(num_m.group(1)) if num_m else 0
        result.append((task_number, text, cat_id))

    return sorted(result, key=lambda x: x[0])


def _extract_answer(div: BeautifulSoup) -> str | None:
    """Try several selectors to find the correct answer in a problem div."""
    # 1. Solution block (often hidden via CSS)
    for sel in (".solution", ".sol", ".solution_block"):
        sol = div.select_one(sel)
        if sol:
            text = sol.get_text(" ", strip=True)
            m = re.search(r"[Оо]твет[:\s]+([^\n\.;]{1,100})", text)
            if m:
                ans = m.group(1).strip().rstrip(".")
                if ans:
                    return ans

    # 2. Inline answer span
    for sel in (".ans_inline", ".answer_value", "[class*='answer']"):
        span = div.select_one(sel)
        if span:
            ans = span.get_text(strip=True)
            if ans and len(ans) < 100:
                return ans

    # 3. Bold text after "Ответ"
    full_text = div.get_text(" ", strip=True)
    m = re.search(r"[Оо]твет[:\s]+([^\n\.;]{1,100})", full_text)
    if m:
        ans = m.group(1).strip().rstrip(".")
        if ans:
            return ans

    return None


def parse_problems_from_page(
    html: str, subject: str, exam_type: str, task_number: int, base: str
) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    problems: list[dict] = []

    for div in soup.select("div.prob_maindiv"):
        # Problem ID
        prob_id = div.get("data-id") or div.get("id", "").lstrip("prob_")
        if not prob_id:
            a = div.select_one("a[href*='problem?id=']")
            if a:
                m = re.search(r"id=(\d+)", a.get("href", ""))
                if m:
                    prob_id = m.group(1)
        if not prob_id:
            continue

        # Question text
        pbody = div.select_one(".pbody")
        if not pbody:
            continue
        question_text = pbody.get_text("\n", strip=True)
        if not question_text or len(question_text) < 8:
            continue

        # Multiple choice options (A/B/C/D or 1/2/3/4)
        options: dict | None = None
        opt_items = div.select(".ans_choice_item") or div.select("ul.answer_choices li")
        if opt_items:
            options = {}
            for i, item in enumerate(opt_items, 1):
                options[str(i)] = item.get_text(strip=True)

        # Correct answer
        answer = _extract_answer(div)
        if not answer:
            continue

        # Hint / примечание
        hint: str | None = None
        for sel in (".prim", ".hint", ".note"):
            h = div.select_one(sel)
            if h:
                hint = h.get_text(strip=True)[:500]
                break

        problems.append({
            "subject": subject,
            "exam_type": exam_type,
            "task_number": task_number,
            "question_text": question_text,
            "options": options,
            "correct_answer": answer,
            "hint": hint or None,
            "difficulty": 1,
            "source_id": f"sdamgia_{exam_type}_{prob_id}",
            "source_url": f"{base}/problem?id={prob_id}",
        })

    return problems


async def scrape_category(
    client: httpx.AsyncClient,
    base: str,
    subject: str,
    exam_type: str,
    task_number: int,
    cat_id: int,
    max_pages: int = 20,
) -> list[dict]:
    all_probs: list[dict] = []

    for page in range(1, max_pages + 1):
        url = f"{base}/category?id={cat_id}&page={page}"
        html = await fetch(client, url)
        if not html:
            break

        probs = parse_problems_from_page(html, subject, exam_type, task_number, base)
        if not probs:
            break
        all_probs.extend(probs)

        # Stop if no "next page" link
        soup = BeautifulSoup(html, "lxml")
        if not soup.select_one(f"a[href*='page={page + 1}']"):
            break

    return all_probs


async def scrape_subject(
    subject: str,
    exam_type: str,
    output_dir: Path,
) -> int:
    base = base_url(subject, exam_type)
    output_file = output_dir / f"{subject}_{exam_type}.json"

    # Load existing to allow resume
    existing: list[dict] = []
    existing_ids: set[str] = set()
    if output_file.exists():
        try:
            existing = json.loads(output_file.read_text(encoding="utf-8"))
            existing_ids = {p["source_id"] for p in existing if p.get("source_id")}
            logger.info("Resuming: %d tasks already saved", len(existing))
        except Exception:
            pass

    logger.info("▶ %s %s  (%s)", subject.upper(), exam_type.upper(), base)

    async with httpx.AsyncClient(headers=HEADERS, timeout=30.0) as client:
        categories = await get_categories(client, base)
        if not categories:
            logger.error("No categories found for %s %s", subject, exam_type)
            return 0

        logger.info("  %d categories found", len(categories))
        all_new: list[dict] = []

        for task_number, topic, cat_id in categories:
            logger.info("  Задание %d (%s) cat=%d", task_number, topic[:40], cat_id)
            try:
                probs = await scrape_category(client, base, subject, exam_type, task_number, cat_id)
                new = [p for p in probs if p["source_id"] not in existing_ids]
                all_new.extend(new)
                existing_ids.update(p["source_id"] for p in new)
                logger.info("    +%d new  (session total: %d)", len(new), len(all_new))
            except Exception as e:
                logger.error("    Error: %s", e)

    combined = existing + all_new
    output_file.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("✓ %s %s: %d tasks saved to %s", subject, exam_type, len(combined), output_file)
    return len(combined)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape sdamgia.ru → JSON")
    parser.add_argument(
        "--subjects", nargs="+", default=["math", "russian"],
        choices=list(SUBJECT_MAP.keys()) + ["all"],
    )
    parser.add_argument("--exam-types", nargs="+", default=["ege"], choices=["ege", "oge"])
    parser.add_argument("--output-dir", default="data/questions")
    args = parser.parse_args()

    subjects = list(SUBJECT_MAP.keys()) if "all" in args.subjects else args.subjects
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for subject in subjects:
        for exam_type in args.exam_types:
            count = await scrape_subject(subject, exam_type, output_dir)
            total += count

    logger.info("═══ Done. Total tasks: %d ═══", total)


if __name__ == "__main__":
    asyncio.run(main())
