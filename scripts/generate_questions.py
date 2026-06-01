#!/usr/bin/env python3
"""Generate sample EGE questions via OpenRouter → TaskImport JSON."""
import asyncio, json, logging, sys
from pathlib import Path
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

import os
API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL   = "google/gemma-3-4b-it"
OUTPUT  = Path("data/questions/math_ege.json")

TASK_TOPICS = {
    1:  "Простейшие математические выражения, действия с числами",
    2:  "Проценты, доли, дроби в прикладных задачах",
    3:  "Геометрия: площади и объёмы фигур",
    4:  "Чтение графиков и диаграмм",
    5:  "Простейшие уравнения (линейные, дробные)",
    6:  "Числовые последовательности и прогрессии",
    7:  "Вероятность и комбинаторика",
    8:  "Степени и логарифмы",
    9:  "Тригонометрия: значения и формулы",
    10: "Производная и её применение",
    11: "Первообразная и интеграл",
    12: "Задачи на движение, работу, смеси",
}

PROMPT_TMPL = """Ты составляешь задания для ЕГЭ по математике (базовый и профильный уровень).

Сгенерируй РОВНО {n} заданий типа «Задание {num}» по теме: {topic}.

Требования:
- Задания должны быть реалистичными, уровня ЕГЭ
- Ответ — одно число, слово или короткое выражение (без развёрнутых решений)
- Для части заданий добавь варианты ответов (4 варианта, ключи "1","2","3","4")
- Краткая подсказка hint (1 предложение о методе решения)

Верни ТОЛЬКО валидный JSON-массив, без пояснений:
[
  {{
    "question_text": "...",
    "options": {{"1": "...", "2": "...", "3": "...", "4": "..."}} или null,
    "correct_answer": "...",
    "hint": "..."
  }},
  ...
]"""


async def generate_batch(client: httpx.AsyncClient, task_num: int, topic: str, n: int = 5) -> list[dict]:
    prompt = PROMPT_TMPL.format(n=n, num=task_num, topic=topic)
    try:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "X-Title": "EGE Bot Generator"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 2000, "temperature": 0.7},
            timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        # Extract JSON array from response
        start = content.find("[")
        end   = content.rfind("]") + 1
        if start == -1 or end == 0:
            log.warning("No JSON array in response for task %d", task_num)
            return []
        items = json.loads(content[start:end])
        result = []
        for item in items:
            if not item.get("question_text") or not item.get("correct_answer"):
                continue
            result.append({
                "subject":       "math",
                "exam_type":     "ege",
                "task_number":   task_num,
                "topic":         topic,
                "question_text": item["question_text"],
                "options":       item.get("options"),
                "correct_answer": str(item["correct_answer"]).strip(),
                "hint":          item.get("hint"),
                "difficulty":    1,
                "source_id":     None,
            })
        return result
    except Exception as e:
        log.error("Task %d error: %s", task_num, e)
        return []


async def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    all_tasks: list[dict] = []

    async with httpx.AsyncClient() as client:
        for task_num, topic in TASK_TOPICS.items():
            log.info("Generating task %d: %s", task_num, topic)
            batch = await generate_batch(client, task_num, topic, n=5)
            log.info("  → %d questions", len(batch))
            all_tasks.extend(batch)
            await asyncio.sleep(1)

    OUTPUT.write_text(json.dumps(all_tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Done: %d questions → %s", len(all_tasks), OUTPUT)


if __name__ == "__main__":
    asyncio.run(main())
