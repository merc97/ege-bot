from typing import Any

import httpx


class APIClient:
    def __init__(self, base_url: str, api_key: str):
        self._base = base_url.rstrip("/")
        self._headers = {"X-Api-Key": api_key}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=15.0)

    async def register_user(
        self, telegram_id: int, username: str | None, first_name: str, last_name: str | None
    ) -> dict:
        async with self._client() as c:
            r = await c.post("/api/v1/users/register", json={
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
            })
            r.raise_for_status()
            return r.json()

    async def get_user(self, telegram_id: int) -> dict | None:
        async with self._client() as c:
            r = await c.get(f"/api/v1/users/{telegram_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def complete_onboarding(self, telegram_id: int, exam: str, subjects: list[str]) -> dict:
        async with self._client() as c:
            r = await c.put(f"/api/v1/users/{telegram_id}/onboarding", json={
                "selected_exam": exam,
                "selected_subjects": subjects,
            })
            r.raise_for_status()
            return r.json()

    async def create_session(self, telegram_id: int, subject: str, exam_type: str, mode: str) -> dict:
        async with self._client() as c:
            r = await c.post("/api/v1/sessions/", json={
                "telegram_id": telegram_id,
                "subject": subject,
                "exam_type": exam_type,
                "mode": mode,
            })
            r.raise_for_status()
            return r.json()

    async def get_next_task(self, session_id: int, telegram_id: int, subject: str, exam_type: str) -> dict | None:
        user = await self.get_user(telegram_id)
        if not user:
            return None
        async with self._client() as c:
            r = await c.get("/api/v1/tasks/next", params={
                "user_id": user["id"],
                "subject": subject,
                "exam_type": exam_type,
                "session_id": session_id,
            })
            r.raise_for_status()
            return r.json()

    async def submit_answer(
        self, session_id: int, task_id: int, user_answer: str, time_spent: int | None
    ) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/v1/sessions/{session_id}/answer", json={
                "task_id": task_id,
                "user_answer": user_answer,
                "time_spent": time_spent,
                "want_ai": True,
            })
            r.raise_for_status()
            return r.json()

    async def finish_session(self, session_id: int) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/v1/sessions/{session_id}/finish")
            r.raise_for_status()
            return r.json()

    async def get_history(self, telegram_id: int, page: int = 1, page_size: int = 5) -> dict | None:
        async with self._client() as c:
            r = await c.get(f"/api/v1/users/{telegram_id}/history",
                            params={"page": page, "page_size": page_size})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def get_progress(self, telegram_id: int) -> dict | None:
        async with self._client() as c:
            r = await c.get(f"/api/v1/sessions/progress/{telegram_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def get_admin_stats(self) -> dict:
        async with self._client() as c:
            r = await c.get("/api/v1/admin/stats")
            r.raise_for_status()
            return r.json()

    async def grant_premium(self, telegram_id: int, days: int) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/v1/admin/grant/{telegram_id}", params={"days": days})
            r.raise_for_status()
            return r.json()

    async def activate_subscription(
        self,
        telegram_id: int,
        provider: str,
        payment_id: str,
        amount: int,
        currency: str = "XTR",
        days: int = 30,
    ) -> dict:
        async with self._client() as c:
            r = await c.post("/api/v1/subscriptions/activate", json={
                "telegram_id": telegram_id,
                "provider": provider,
                "payment_id": payment_id,
                "amount": amount,
                "currency": currency,
                "days": days,
            })
            r.raise_for_status()
            return r.json()
