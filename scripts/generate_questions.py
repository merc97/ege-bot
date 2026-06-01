#!/usr/bin/env python3
"""Generate sample EGE questions via OpenRouter → TaskImport JSON."""
import asyncio, json, logging, sys
from pathlib import Path
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

import os
API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL   = "google/gemma-4-31b-it:free"
OUTPUT  = Path("data/questions/math_ege.json")

TASK_TOPICS = {
    1:  "Простые арифметические вычисления: целые числа, десятичные дроби, порядок действий",
    2:  "Проценты и дроби в практических задачах (скидки, налоги, концентрации)",
    3:  "Геометрия: площади плоских фигур и объёмы тел (прямоугольник, треугольник, цилиндр, куб)",
    4:  "Анализ диаграмм и графиков: столбчатые, круговые, линейные",
    5:  "Линейные и простые дробные уравнения с одним неизвестным",
    6:  "Арифметические и геометрические прогрессии: n-й член и сумма",
    7:  "Простейшая комбинаторика и вероятность",
    8:  "Степени и логарифмы: вычисление значений",
    9:  "Тригонометрические значения стандартных углов (sin, cos, tg)",
    10: "Нахождение критических точек и экстремумов функции через производную",
    11: "Простейшие первообразные и определённые интегралы",
    12: "Текстовые задачи на движение и работу",
}

PROMPT_TMPL = """Ты — составитель заданий ЕГЭ по математике. Сгенерируй РОВНО {n} заданий типа «Задание {num}» по теме: {topic}.

КРИТИЧЕСКИ ВАЖНО: каждый ответ должен быть математически точным. Перед записью ответа ПРОВЕРЬ вычисления.

Правила:
- Задания простые, уровень базового ЕГЭ
- Только числовые ответы или короткие выражения (не «x = 5», а «5»)
- Не используй задания с графиками или рисунками
- options: либо объект {{"1":"...","2":"...","3":"...","4":"..."}} либо null
- Если даёшь варианты — правильный ответ должен быть среди них, и correct_answer = текст варианта (не номер)
- hint: 1 предложение — метод решения

Верни ТОЛЬКО валидный JSON без markdown и пояснений:
[
  {{
    "question_text": "текст задания",
    "options": null,
    "correct_answer": "ответ",
    "hint": "подсказка"
  }}
]"""


async def generate_batch(client: httpx.AsyncClient, task_num: int, topic: str, n: int = 8) -> list[dict]:
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
            # Нормализуем options: список → словарь
            opts = item.get("options")
            if isinstance(opts, list):
                opts = {str(i + 1): v for i, v in enumerate(opts)}
            elif not isinstance(opts, dict):
                opts = None
            item["options"] = opts
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
