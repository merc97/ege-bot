from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.api_client import APIClient

router = Router()

SUBJECT_LABELS = {
    "math": "Математика", "russian": "Русский", "physics": "Физика",
    "chemistry": "Химия", "biology": "Биология", "history": "История",
    "social": "Обществознание", "english": "Английский", "informatics": "Информатика",
}


def history_keyboard(page: int, pages: int) -> object:
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="◀️", callback_data=f"history:page:{page - 1}")
    builder.button(text=f"{page}/{pages}", callback_data="history:noop")
    if page < pages:
        builder.button(text="▶️", callback_data=f"history:page:{page + 1}")
    builder.button(text="🔙 Назад", callback_data="menu:progress")
    builder.adjust(3, 1)
    return builder.as_markup()


def _format_item(i: int, item: dict) -> str:
    subj = SUBJECT_LABELS.get(item.get("subject", ""), item.get("subject", "—"))
    task_n = item.get("task_number")
    label = f"Задание {task_n}" if task_n else "Задание"
    icon = "✅" if item.get("is_correct") else "❌"
    answered_at = (item.get("answered_at") or "")[:16].replace("T", " ")

    question = (item.get("question_text") or "")[:120]
    if len(item.get("question_text") or "") > 120:
        question += "…"

    lines = [
        f"{i}. {icon} <b>{subj} · {label}</b>  <i>{answered_at}</i>",
        f"   {question}",
        f"   Твой ответ: <code>{item.get('user_answer', '—')}</code>  "
        f"Верный: <code>{item.get('correct_answer_snapshot', '—')}</code>",
    ]
    if item.get("ai_explanation"):
        exp = item["ai_explanation"][:180]
        if len(item["ai_explanation"]) > 180:
            exp += "…"
        lines.append(f"   🤖 {exp}")
    return "\n".join(lines)


async def _show_history(callback: CallbackQuery, api: APIClient, page: int) -> None:
    data = await api.get_history(callback.from_user.id, page=page, page_size=5)

    if not data or data["total"] == 0:
        await callback.message.edit_text(
            "📋 <b>История ответов</b>\n\nПока нет записей. Порешай задания!",
            reply_markup=history_keyboard(1, 1),
            parse_mode="HTML",
        )
        return

    lines = [f"📋 <b>История ответов</b>  (стр. {data['page']}/{data['pages']}, всего {data['total']})\n"]
    for idx, item in enumerate(data["items"], start=(page - 1) * 5 + 1):
        lines.append(_format_item(idx, item))
        lines.append("")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=history_keyboard(data["page"], data["pages"]),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:history")
async def history_first(callback: CallbackQuery, api: APIClient):
    await callback.answer()
    await _show_history(callback, api, page=1)


@router.callback_query(F.data.startswith("history:page:"))
async def history_page(callback: CallbackQuery, api: APIClient):
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await _show_history(callback, api, page=page)


@router.callback_query(F.data == "history:noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
