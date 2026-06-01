# EGE Bot — Техническое описание

> Актуально на июнь 2026. Точка входа бота: `bot/main.py`. Управление продакшном: `systemd` (сервис `ege-bot`), контейнеры: `docker compose`.

---

## 1. Обзор

Telegram-бот для подготовки к ЕГЭ/ОГЭ. Пользователь выбирает предмет и режим (практика / мини-экзамен), получает задания, вводит ответ — бот проверяет и при ошибке даёт AI-объяснение через OpenRouter. Родители могут подключить аккаунт ребёнка и следить за прогрессом. Подписка Premium снимает дневной лимит AI-объяснений.

---

## 2. Стек технологий

| Компонент | Технология |
|---|---|
| Язык | Python 3.11 |
| Telegram (бот) | aiogram 3.x (asyncio, FSM, Redis storage) |
| Бэкенд API | FastAPI 0.115 + uvicorn |
| База данных | PostgreSQL 16 (asyncpg + SQLAlchemy 2.0 async) |
| Миграции | Alembic |
| Кэш / FSM-хранилище | Redis 7 |
| AI-объяснения | OpenRouter (`google/gemma-3-4b-it` или дешевле) |
| Валидация конфигов | pydantic-settings |
| HTTP-клиент | httpx (async) |
| Прокси | nginx (HTTP; SSL добавляется через certbot) |
| Контейнеризация | Docker + Docker Compose |
| Автозапуск | systemd (`ege-bot.service`) |
| Watchdog | systemd timer (`ege-bot-watchdog.timer`, каждые 2 мин) |
| Бэкапы | systemd timer (`ege-bot-backup.timer`, раз в сутки) |

---

## 3. Архитектура

```
Telegram ←→ aiogram Bot (bot/)
                │
                │ HTTP (X-Api-Key)
                ▼
          FastAPI Backend (backend/)
                │
         ┌──────┴──────┐
         ▼             ▼
    PostgreSQL 16    Redis 7
```

Бот и бэкенд — отдельные контейнеры. Бот не обращается к БД напрямую — только через REST API бэкенда. Redis используется двояко: как FSM-хранилище aiogram и как кэш AI-объяснений (TTL 7 дней).

---

## 4. Структура проекта

```
ege-bot/
├── bot/                        — Telegram-бот (aiogram)
│   ├── main.py                 — точка входа, регистрация роутеров
│   ├── config.py               — pydantic-settings (BOT_TOKEN, BACKEND_URL, API_KEY, ...)
│   ├── handlers/
│   │   ├── start.py            — /start, онбординг (роль → экзамен → предметы)
│   │   ├── test.py             — флоу решения заданий (практика / мини-экзамен)
│   │   ├── progress.py         — прогресс по предметам + кнопка истории
│   │   ├── history.py          — история ответов с пагинацией (5 шт/стр)
│   │   ├── parent.py           — панель родителя: прогресс/история ученика, оплата
│   │   ├── settings.py         — смена экзамена, предметов, «Мой код» для родителя
│   │   ├── faq.py              — FAQ (разные для ученика и родителя)
│   │   ├── subscribe.py        — покупка Premium (Stars + YooKassa stub)
│   │   └── admin.py            — /admin, /grant, /stats
│   ├── keyboards/
│   │   └── inline.py           — все InlineKeyboardMarkup
│   ├── middlewares/
│   │   └── user_middleware.py  — авторегистрация пользователя при каждом апдейте
│   ├── states/
│   │   └── states.py           — FSM: OnboardingStates, TestStates
│   └── utils/
│       └── api_client.py       — httpx-клиент к бэкенду
│
├── backend/                    — FastAPI-бэкенд
│   ├── app/
│   │   ├── main.py             — FastAPI app, CORS, роутеры
│   │   ├── config.py           — pydantic-settings
│   │   ├── database.py         — AsyncSessionLocal, get_session, get_redis
│   │   ├── api/v1/
│   │   │   ├── users.py        — регистрация, онбординг, история, привязка родитель↔ученик
│   │   │   ├── sessions.py     — create/answer/finish + GET progress
│   │   │   ├── tasks.py        — get_next (умный подбор слабых тем), get_by_id
│   │   │   ├── subscriptions.py — POST /activate (после оплаты Stars)
│   │   │   └── admin.py        — stats, import tasks, grant premium
│   │   ├── models/
│   │   │   ├── user.py         — users (role, linked_student_id, subscription, ...)
│   │   │   ├── task.py         — tasks (subject, exam_type, task_number, options, ...)
│   │   │   ├── session.py      — test_sessions + session_answers (со снапшотами вопросов)
│   │   │   └── progress.py     — user_progress + subscriptions
│   │   ├── schemas/            — Pydantic схемы для всех моделей
│   │   └── services/
│   │       ├── user_service.py     — CRUD пользователей, can_use_ai, link_parent
│   │       ├── session_service.py  — submit_answer (проверка + AI + снапшот + прогресс)
│   │       ├── task_service.py     — get_next (слабые темы приоритетнее)
│   │       ├── progress_service.py — сводная статистика по предметам
│   │       └── ai_service.py       — OpenRouter, Redis-кэш объяснений (TTL 7 дней)
│   ├── alembic/versions/
│   │   ├── 001_initial.py      — базовая схема
│   │   ├── 002_session_answers_snapshots.py — снапшоты вопросов
│   │   └── 003_user_roles.py   — роли родитель/ученик
│   ├── entrypoint.sh           — wait-for-postgres → alembic upgrade head → uvicorn
│   └── requirements.txt
│
├── data/
│   ├── nginx/default.conf      — nginx конфиг
│   └── questions/              — JSON-файлы с заданиями (не в git)
├── scripts/
│   ├── backup.sh               — pg_dump + архивация + ротация
│   ├── watchdog.sh             — проверяет bot/backend контейнеры, рестарт при падении
│   └── generate_questions.py   — генератор заданий через OpenRouter (для первого наполнения)
├── docker-compose.yml
├── Makefile
└── .env                        — секреты (не в git)
```

---

## 5. Запуск и управление

```bash
# Первый запуск на сервере
cp .env.example .env       # заполнить переменные
make init                  # build → up → migrate → import-questions

# Управление
sudo systemctl start|stop|restart ege-bot
sudo systemctl status ege-bot
sudo docker compose logs -f bot --tail=100
sudo docker compose logs -f backend --tail=100

# Миграции вручную
make migrate

# Рестарт только бота
make restart-bot

# Загрузить новые задания
make import-questions

# Посмотреть все команды
make help
```

---

## 6. Переменные окружения (.env)

| Переменная | Обязательная | Описание |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram Bot API токен |
| `ADMIN_IDS` | ✅ | Telegram ID администраторов через запятую |
| `POSTGRES_DB` | ✅ | Имя БД (по умолч. `ege_bot`) |
| `POSTGRES_USER` | ✅ | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | ✅ | Пароль PostgreSQL |
| `DATABASE_URL` | ✅ | `postgresql://user:pass@postgres:5432/ege_bot` |
| `REDIS_URL` | ✅ | `redis://redis:6379/0` |
| `API_KEY` | ✅ | Внутренний токен бот↔бэкенд (Bearer) |
| `BACKEND_URL` | ✅ | `http://backend:8000` |
| `OPENROUTER_API_KEY` | ✅ | Ключ OpenRouter для AI-объяснений |
| `AI_MODEL` | нет | Модель OpenRouter (по умолч. `qwen/qwen2.5-3b-instruct`) |
| `AI_MAX_TOKENS` | нет | Макс. токенов AI-объяснения (по умолч. `150`) |
| `AI_TEMPERATURE` | нет | Температура (по умолч. `0.3`) |
| `YOOKASSA_SHOP_ID` | нет | YooKassa (Sprint 5) |
| `YOOKASSA_SECRET_KEY` | нет | YooKassa (Sprint 5) |
| `DEBUG` | нет | `false` в проде |
| `LOG_LEVEL` | нет | `INFO` / `DEBUG` |

---

## 7. База данных

**Соединение**: SQLAlchemy 2.0 async + asyncpg. Все запросы асинхронные, connection pool управляется SQLAlchemy.

### Таблицы

| Таблица | Назначение |
|---|---|
| `users` | telegram_id, role (student/parent), linked_student_id, subscription_type/end, onboarding, selected_exam/subjects, referral_code, daily_ai_used |
| `tasks` | задания: subject, exam_type, task_number, question_text, options (JSON), correct_answer, hint, source_id |
| `test_sessions` | сессии: user_id, subject, exam_type, mode, total_questions, correct_answers, status |
| `session_answers` | ответы: session_id, task_id, **question_text** (снапшот), **correct_answer_snapshot**, user_answer, is_correct, ai_explanation, shown_at, answered_at |
| `user_progress` | прогресс: user_id, subject, task_number, total/correct_attempts, last_practiced_at |
| `subscriptions` | история платежей: user_id, plan, provider, payment_id, amount, currency, started_at, expires_at, status |

> `session_answers` хранит снапшоты — текст вопроса и правильный ответ копируются при каждом ответе. Это позволяет отображать историю даже если задание изменится.

---

## 8. Жизненный цикл запроса (тест)

```
Пользователь → 📚 Начать тест
  → выбор предмета → выбор режима (практика / мини-экзамен)
  → api.create_session()
  → api.get_next_task():
      TaskService.get_next():
        1. Сначала задания из слабых тем (accuracy < 50%)
        2. Если нет — любое незавершённое задание сессии
  → бот показывает вопрос + варианты (или свободный ввод)
  → api.submit_answer():
      normalize(user_answer) == normalize(correct_answer)?
      если нет + want_ai + can_use_ai():
        → AIService.get_explanation()  ← кэш Redis TTL 7д
        → increment_ai_usage()
      → SessionAnswer(с снапшотами)
      → update TestSession counters
      → upsert UserProgress
  → бот показывает результат + AI-объяснение (если есть)
  → следующий вопрос / завершить сессию
```

---

## 9. Роли пользователей

### Ученик (role = "student")

Стандартный флоу: онбординг → экзамен → предметы → тренировка.

- Свободный доступ к заданиям
- 3 AI-объяснения в сутки (бесплатно)
- Premium — безлимитные AI-объяснения (150 Stars / 30 дней)
- **Мой код** (⚙️ Настройки → Мой код) — 8-значный `referral_code` для передачи родителю

### Родитель (role = "parent")

Отдельный флоу: онбординг → ввод кода ученика → привязка.

- Видит прогресс и историю ответов ученика в реальном времени
- Может оплатить Premium за ученика (payload `premium_stars_student_{tg_id}`)
- Свой FAQ с родительскими вопросами
- Не имеет доступа к решению заданий

### Привязка родитель ↔ ученик

1. Ученик: ⚙️ Настройки → **Мой код** → отправляет 8 символов родителю
2. Родитель: регистрация → вводит код → `POST /api/v1/users/{id}/link-student`
3. `users.linked_student_id` = `id` ученика

---

## 10. AI-объяснения

**Провайдер**: OpenRouter (любая дешёвая модель, по умолч. `qwen/qwen2.5-3b-instruct`).

**Промпт**:
```
Ученик решал задание ЕГЭ/ОГЭ.
Предмет: {subject_ru}
Задание №{task_number}: {question_text}
Правильный ответ: {correct_answer}
Ответ ученика: {user_answer}

Объясни ошибку кратко (2-3 предложения) и дай подсказку. Без вступлений.
```

**Кэш**: Redis, ключ `ai:exp:{task_id}:{md5(user_answer)[:8]}`, TTL 7 дней.
Одна и та же ошибка одного пользователя к одному заданию не тратит повторный API-вызов.

**Лимиты**:
- Бесплатно: 3 объяснения в сутки (`daily_ai_used`, сброс по `daily_ai_reset_at`)
- Premium: безлимит

---

## 11. Подписки и оплата

### Telegram Stars (реализовано)

```
Пользователь → ⭐ Подписка → Купить за Stars
  → answer_invoice(currency="XTR", amount=150)
  → PreCheckoutQuery → approve
  → SuccessfulPayment:
      payload = "premium_stars_{tg_id}"          — за себя
      payload = "premium_stars_student_{tg_id}"  — за ученика (родитель)
  → POST /api/v1/subscriptions/activate
      → user.subscription_type = "premium"
      → user.subscription_end = now + 30 дней
      → INSERT subscriptions (provider="stars", payment_id=charge_id)
```

### YooKassa (Sprint 5 — не реализовано)

Заглушка в `subscribe.py`. Требует: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`.

---

## 12. Импорт заданий

Задания хранятся в `data/questions/*.json`. Формат:

```json
[
  {
    "subject": "math",
    "exam_type": "ege",
    "task_number": 1,
    "topic": "Простейшие выражения",
    "question_text": "Найдите значение выражения...",
    "options": {"1": "2", "2": "4", "3": "6", "4": "8"},
    "correct_answer": "4",
    "hint": "Используйте порядок действий",
    "difficulty": 1
  }
]
```

Загрузка: `make import-questions` → `python -m app.scripts.import_questions`.
Скрипт пропускает уже загруженные задания (дедупликация по `source_id`), не запускается если БД не пуста.

**Генерация через AI** (для тестирования):
```bash
OPENROUTER_API_KEY=sk-or-... python scripts/generate_questions.py \
  --subjects math russian --exam-types ege
```

---

## 13. Умный подбор заданий

`TaskService.get_next()` — два уровня:

1. **Слабые темы** (приоритет): задания по `task_number`, где `correct/total < 50%` у пользователя, исключая уже отвеченные в текущей сессии, случайный порядок
2. **Общий пул**: любое активное задание предмета, не отвеченное в сессии, случайный порядок

---

## 14. Перенос на другой сервер

```bash
# На старом сервере — бэкап
sudo docker compose exec postgres \
  pg_dump -U ege ege_bot | gzip > backup_$(date +%Y%m%d).sql.gz
# Скопировать: backup_*.sql.gz и .env

# На новом сервере
git clone git@github.com:merc97/ege-bot.git
cd ege-bot
cp .env.example .env     # вставить значения из старого .env
# Установить docker: sudo apt install docker.io docker-compose-v2
# Добавить в docker группу: sudo usermod -aG docker $USER && newgrp docker
make build
make up
# Восстановить БД:
gunzip -c backup_*.sql.gz | sudo docker compose exec -T postgres \
  psql -U ege ege_bot
# Активировать автозапуск:
sudo systemctl enable ege-bot ege-bot-watchdog.timer ege-bot-backup.timer
sudo systemctl start ege-bot-watchdog.timer ege-bot-backup.timer
```

---

## 15. Логи и отладка

```bash
# Логи контейнеров
sudo docker compose logs -f bot --tail=100
sudo docker compose logs -f backend --tail=100

# Все сервисы
make logs

# Состояние контейнеров
sudo docker compose ps

# Подключиться к PostgreSQL
make psql

# Systemd
sudo systemctl status ege-bot
journalctl -u ege-bot -n 50 -f
```

**Watchdog** (каждые 2 мин): если `bot` или `backend` упали — рестартует `ege-bot.service`. Пишет в syslog: `logger -t ege-bot-watchdog`.

```bash
grep ege-bot-watchdog /var/log/syslog | tail -20
```

---

## 16. Бэкапы

Автоматический ежесуточный бэкап через `systemd` таймер (`ege-bot-backup.timer`, 03:00).

Бэкапы хранятся в `/var/backups/ege-bot/`, ротация — последние 7 дней.

```bash
# Ручной бэкап
/home/lexa/ege-bot/scripts/backup.sh

# Список бэкапов
ls -lh /var/backups/ege-bot/

# Восстановление
gunzip -c /var/backups/ege-bot/ege_bot_2026-06-01.sql.gz | \
  sudo docker compose exec -T postgres psql -U ege ege_bot
```

---

## 17. FAQ для администраторов

**Q: Как выдать Premium пользователю вручную?**
`/grant <telegram_id> 30` в Telegram-боте. Или через API:
```bash
curl -X POST http://localhost/api/v1/admin/grant/{telegram_id}?days=30 \
  -H "X-Api-Key: <API_KEY>"
```

**Q: Как загрузить новые задания?**
Положить JSON в `data/questions/`, затем `make import-questions`.
Для полной перезагрузки — очистить таблицу `tasks` и запустить снова.

**Q: Как посмотреть статистику?**
`/stats` в Telegram-боте (только ADMIN_IDS). Показывает: пользователей, Premium, заданий, сессий.

**Q: Как привязать домен и включить HTTPS?**
1. Установить certbot: `sudo apt install certbot python3-certbot-nginx`
2. Получить сертификат: `sudo certbot --nginx -d ege-bot.ru`
3. Обновить `data/nginx/default.conf` — раскомментировать SSL-блок
4. `make restart-backend` (перезагрузит nginx)

**Q: Бот перестал отвечать — что делать?**
```bash
sudo docker compose ps              # проверить статусы
sudo docker compose logs bot --tail=50  # найти ошибку
sudo systemctl restart ege-bot      # или так
```

**Q: Как сменить AI-модель?**
В `.env` изменить `AI_MODEL` на любую модель OpenRouter. Дешёвые варианты: `google/gemma-3-4b-it` (бесплатно), `mistralai/mistral-nemo` ($0.03/1M tok).
После изменения: `make restart-backend`.

**Q: Как посмотреть историю конкретного пользователя через API?**
```bash
curl "http://localhost/api/v1/users/{telegram_id}/history?page=1&page_size=20" \
  -H "X-Api-Key: <API_KEY>"
```

**Q: Как сделать бэкап прямо сейчас?**
```bash
/home/lexa/ege-bot/scripts/backup.sh
```
