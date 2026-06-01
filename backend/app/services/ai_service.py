import hashlib
import logging

import httpx
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_PROMPT = (
    "Ученик решал задание ЕГЭ/ОГЭ.\n"
    "Предмет: {subject}\n"
    "Задание №{task_number}: {question_text}\n"
    "Правильный ответ: {correct_answer}\n"
    "Ответ ученика: {user_answer}\n\n"
    "Объясни ошибку кратко (2-3 предложения) и дай конкретную подсказку. Без вступлений."
)

SUBJECT_RU = {
    "math": "Математика",
    "russian": "Русский язык",
    "physics": "Физика",
    "chemistry": "Химия",
    "biology": "Биология",
    "history": "История",
    "social": "Обществознание",
    "english": "Английский язык",
    "informatics": "Информатика",
}


class AIService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    def _cache_key(self, task_id: int, user_answer: str) -> str:
        h = hashlib.md5(user_answer.lower().strip().encode()).hexdigest()[:8]
        return f"ai:exp:{task_id}:{h}"

    async def get_explanation(
        self,
        task_id: int,
        subject: str,
        task_number: int | None,
        question_text: str,
        correct_answer: str,
        user_answer: str,
    ) -> str | None:
        cache_key = self._cache_key(task_id, user_answer)
        cached = await self.redis.get(cache_key)
        if cached:
            return cached

        prompt = _PROMPT.format(
            subject=SUBJECT_RU.get(subject, subject),
            task_number=task_number or "—",
            question_text=question_text,
            correct_answer=correct_answer,
            user_answer=user_answer,
        )

        try:
            explanation = await self._call_openrouter(prompt)
        except Exception as e:
            logger.warning("AI explanation failed for task %d: %s", task_id, e)
            return None

        if explanation:
            await self.redis.setex(cache_key, 7 * 86400, explanation)
        return explanation

    async def _call_openrouter(self, prompt: str) -> str | None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://ege-bot.ru",
                    "X-Title": "EGE Prep Bot",
                },
                json={
                    "model": settings.AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": settings.AI_MAX_TOKENS,
                    "temperature": settings.AI_TEMPERATURE,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
