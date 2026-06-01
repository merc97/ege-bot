from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import back_to_menu_keyboard
from bot.utils.api_client import APIClient

router = Router()

SUBJECT_LABELS = {
    "math": "📐 Математика", "russian": "📝 Русский язык", "physics": "⚡ Физика",
    "chemistry": "🧪 Химия", "biology": "🌿 Биология", "history": "🏛 История",
    "social": "🤝 Обществознание", "english": "🇬🇧 Английский", "informatics": "💻 Информатика",
}


@router.callback_query(F.data == "menu:progress")
async def show_progress(callback: CallbackQuery, api: APIClient):
    data = await api.get_progress(callback.from_user.id)
    await callback.answer()

    if not data or not data.get("subjects"):
        await callback.message.edit_text(
            "📊 <b>Прогресс</b>\n\n"
            "Пока нет данных. Реши хотя бы несколько заданий!",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    lines = ["📊 <b>Твой прогресс</b>\n"]
    for subj in sorted(data["subjects"], key=lambda x: x["accuracy"], reverse=True):
        label = SUBJECT_LABELS.get(subj["subject"], subj["subject"])
        acc = int(subj["accuracy"] * 100)
        bar = _progress_bar(acc)
        lines.append(f"{label}\n{bar} {acc}% ({subj['correct_attempts']}/{subj['total_attempts']})")
        if subj.get("weak_tasks"):
            weak = ", ".join(f"№{t}" for t in subj["weak_tasks"])
            lines.append(f"  ⚠️ Слабые задания: {weak}")
        lines.append("")

    lines.append(f"🎯 Всего сессий: <b>{data['total_sessions']}</b>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("progress"))
async def cmd_progress(message: Message, api: APIClient):
    data = await api.get_progress(message.from_user.id)
    if not data or not data.get("subjects"):
        await message.answer("Пока нет данных — сначала порешай задания!")
        return
    subj = data["subjects"][0]
    acc = int(subj["accuracy"] * 100)
    await message.answer(f"Твоя точность по {subj['subject']}: {acc}%")


def _progress_bar(pct: int) -> str:
    filled = round(pct / 10)
    return "█" * filled + "░" * (10 - filled)
