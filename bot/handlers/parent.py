from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.handlers.history import _format_item, history_keyboard
from bot.handlers.progress import SUBJECT_LABELS, _progress_bar
from bot.keyboards.inline import back_to_menu_keyboard
from bot.utils.api_client import APIClient

router = Router()


def parent_student_keyboard(has_student: bool) -> object:
    builder = InlineKeyboardBuilder()
    if has_student:
        builder.button(text="📊 Прогресс ребёнка", callback_data="parent:progress")
        builder.button(text="📋 История ответов", callback_data="parent:history:1")
        builder.button(text="⭐ Оплатить Premium ребёнку", callback_data="parent:pay")
        builder.button(text="🔗 Сменить ученика", callback_data="parent:relink")
    else:
        builder.button(text="🔗 Привязать ученика", callback_data="parent:relink")
    builder.button(text="🔙 Меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "parent:dashboard")
async def parent_dashboard(callback: CallbackQuery, api: APIClient):
    student = await api.get_linked_student(callback.from_user.id)
    await callback.answer()

    if not student:
        await callback.message.edit_text(
            "👨‍👩‍👧 <b>Панель родителя</b>\n\n"
            "Ученик не привязан. Нажми «Привязать ученика» и введи его код.\n"
            "<i>Код ученика: в боте → ⚙️ Настройки → Мой код</i>",
            reply_markup=parent_student_keyboard(False),
            parse_mode="HTML",
        )
        return

    name = student.get("first_name", "Ученик")
    exam = student.get("selected_exam", "—").upper()
    subjects = student.get("selected_subjects") or []
    sub_type = "⭐ Premium" if student.get("subscription_type") == "premium" else "Бесплатный"

    await callback.message.edit_text(
        f"👨‍👩‍👧 <b>Ваш ученик: {name}</b>\n\n"
        f"Экзамен: <b>{exam}</b>  |  Предметов: <b>{len(subjects)}</b>\n"
        f"Подписка: <b>{sub_type}</b>",
        reply_markup=parent_student_keyboard(True),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "parent:progress")
async def parent_student_progress(callback: CallbackQuery, api: APIClient):
    data = await api.get_student_progress(callback.from_user.id)
    await callback.answer()

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 История", callback_data="parent:history:1")
    builder.button(text="🔙 Назад", callback_data="parent:dashboard")
    builder.adjust(1)

    if not data or not data.get("subjects"):
        await callback.message.edit_text(
            "📊 <b>Прогресс ученика</b>\n\nПока нет данных — ребёнок ещё не решал задания.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
        return

    lines = ["📊 <b>Прогресс ученика</b>\n"]
    for subj in sorted(data["subjects"], key=lambda x: x["accuracy"], reverse=True):
        label = SUBJECT_LABELS.get(subj["subject"], subj["subject"])
        acc = int(subj["accuracy"] * 100)
        bar = _progress_bar(acc)
        lines.append(f"{label}\n{bar} {acc}% ({subj['correct_attempts']}/{subj['total_attempts']})")
        if subj.get("weak_tasks"):
            lines.append(f"  ⚠️ Слабые: {', '.join(f'№{t}' for t in subj['weak_tasks'])}")
        lines.append("")
    lines.append(f"🎯 Сессий: <b>{data['total_sessions']}</b>")

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=builder.as_markup(), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("parent:history:"))
async def parent_student_history(callback: CallbackQuery, api: APIClient):
    page = int(callback.data.split(":")[2])
    data = await api.get_student_history(callback.from_user.id, page=page)
    await callback.answer()

    builder = InlineKeyboardBuilder()
    if data and page > 1:
        builder.button(text="◀️", callback_data=f"parent:history:{page - 1}")
    if data:
        builder.button(text=f"{data['page']}/{data['pages']}", callback_data="history:noop")
    if data and page < data.get("pages", 1):
        builder.button(text="▶️", callback_data=f"parent:history:{page + 1}")
    builder.button(text="🔙 Назад", callback_data="parent:dashboard")
    builder.adjust(3, 1)

    if not data or data["total"] == 0:
        await callback.message.edit_text(
            "📋 <b>История ученика</b>\n\nПока нет записей.",
            reply_markup=builder.as_markup(), parse_mode="HTML",
        )
        return

    lines = [f"📋 <b>История ученика</b>  (стр. {data['page']}/{data['pages']}, всего {data['total']})\n"]
    for idx, item in enumerate(data["items"], start=(page - 1) * 5 + 1):
        lines.append(_format_item(idx, item))
        lines.append("")

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=builder.as_markup(), parse_mode="HTML",
    )


@router.callback_query(F.data == "parent:pay")
async def parent_pay(callback: CallbackQuery, api: APIClient):
    from aiogram.types import LabeledPrice
    student = await api.get_linked_student(callback.from_user.id)
    if not student:
        await callback.answer("Сначала привяжи ученика!", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer_invoice(
        title="EGE Bot Premium для ученика — 1 месяц",
        description=f"Premium для {student.get('first_name', 'ученика')}: безлимитные AI-объяснения",
        payload=f"premium_stars_student_{student['telegram_id']}",
        currency="XTR",
        prices=[LabeledPrice(label="Premium 1 месяц", amount=150)],
    )


@router.callback_query(F.data == "parent:relink")
async def parent_relink(callback: CallbackQuery):
    from aiogram.fsm.context import FSMContext
    from bot.states.states import OnboardingStates
    await callback.answer()
    await callback.message.edit_text(
        "🔗 Введи новый код ученика:\n"
        "<i>Код ученика: ⚙️ Настройки → Мой код</i>",
        parse_mode="HTML",
    )
