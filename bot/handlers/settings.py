from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline import SUBJECTS, EGE_SUBJECTS, OGE_SUBJECTS, back_to_menu_keyboard
from bot.utils.api_client import APIClient

router = Router()


def settings_menu_keyboard(exam_type: str, subjects: list[str]) -> object:
    exam_label = "ЕГЭ" if exam_type == "ege" else "ОГЭ"
    subj_labels = ", ".join(SUBJECTS.get(s, s) for s in subjects) if subjects else "все"
    builder = InlineKeyboardBuilder()
    builder.button(text=f"📘 Экзамен: {exam_label}", callback_data="settings:change_exam")
    builder.button(text="📚 Изменить предметы", callback_data="settings:change_subjects")
    builder.button(text="🔙 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def settings_exam_keyboard(current: str) -> object:
    builder = InlineKeyboardBuilder()
    for key, label in [("ege", "📘 ЕГЭ"), ("oge", "📗 ОГЭ")]:
        mark = "✅ " if key == current else ""
        builder.button(text=f"{mark}{label}", callback_data=f"settings:exam:{key}")
    builder.button(text="🔙 Назад", callback_data="menu:settings")
    builder.adjust(2)
    return builder.as_markup()


def settings_subjects_keyboard(exam_type: str, selected: list[str]) -> object:
    available = EGE_SUBJECTS if exam_type == "ege" else OGE_SUBJECTS
    builder = InlineKeyboardBuilder()
    for key in available:
        mark = "✅ " if key in selected else ""
        builder.button(text=f"{mark}{SUBJECTS[key]}", callback_data=f"settings:subject:{key}")
    builder.button(text="💾 Сохранить", callback_data="settings:subjects_save")
    builder.button(text="🔙 Назад", callback_data="menu:settings")
    builder.adjust(2)
    return builder.as_markup()


@router.callback_query(F.data == "menu:settings")
async def settings_menu(callback: CallbackQuery, state: FSMContext, api: APIClient):
    await state.clear()
    user = await api.get_user(callback.from_user.id)
    exam_type = (user or {}).get("selected_exam") or "ege"
    subjects = (user or {}).get("selected_subjects") or []

    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        f"Экзамен: <b>{'ЕГЭ' if exam_type == 'ege' else 'ОГЭ'}</b>\n"
        f"Предметы: <b>{len(subjects)}</b> выбрано",
        reply_markup=settings_menu_keyboard(exam_type, subjects),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "settings:change_exam")
async def change_exam(callback: CallbackQuery, api: APIClient):
    user = await api.get_user(callback.from_user.id)
    current = (user or {}).get("selected_exam") or "ege"
    await callback.message.edit_text(
        "📘 <b>Выберите экзамен:</b>",
        reply_markup=settings_exam_keyboard(current),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:exam:"))
async def set_exam(callback: CallbackQuery, state: FSMContext, api: APIClient):
    exam = callback.data.split(":")[2]
    user = await api.get_user(callback.from_user.id)
    subjects = (user or {}).get("selected_subjects") or []

    # Сохраняем новый экзамен, предметы не меняем
    await api.complete_onboarding(callback.from_user.id, exam, subjects)
    exam_label = "ЕГЭ" if exam == "ege" else "ОГЭ"
    await callback.answer(f"Экзамен изменён на {exam_label}", show_alert=False)

    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        f"Экзамен: <b>{exam_label}</b>\n"
        f"Предметы: <b>{len(subjects)}</b> выбрано",
        reply_markup=settings_menu_keyboard(exam, subjects),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "settings:change_subjects")
async def change_subjects(callback: CallbackQuery, state: FSMContext, api: APIClient):
    user = await api.get_user(callback.from_user.id)
    exam_type = (user or {}).get("selected_exam") or "ege"
    subjects = (user or {}).get("selected_subjects") or []
    await state.update_data(settings_exam=exam_type, settings_subjects=list(subjects))
    await callback.message.edit_text(
        "📚 <b>Выберите предметы:</b>\n"
        "<i>Нажми на предмет чтобы добавить/убрать, затем «Сохранить»</i>",
        reply_markup=settings_subjects_keyboard(exam_type, subjects),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:subject:"))
async def toggle_subject(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":")[2]
    data = await state.get_data()
    subjects: list[str] = list(data.get("settings_subjects", []))
    exam_type: str = data.get("settings_exam", "ege")

    if key in subjects:
        subjects.remove(key)
    else:
        subjects.append(key)
    await state.update_data(settings_subjects=subjects)

    await callback.message.edit_reply_markup(
        reply_markup=settings_subjects_keyboard(exam_type, subjects)
    )
    await callback.answer()


@router.callback_query(F.data == "settings:subjects_save")
async def save_subjects(callback: CallbackQuery, state: FSMContext, api: APIClient):
    data = await state.get_data()
    subjects: list[str] = data.get("settings_subjects", [])
    exam_type: str = data.get("settings_exam", "ege")

    if not subjects:
        await callback.answer("Выбери хотя бы один предмет!", show_alert=True)
        return

    await api.complete_onboarding(callback.from_user.id, exam_type, subjects)
    await state.clear()
    await callback.answer("Сохранено!", show_alert=False)

    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        f"Экзамен: <b>{'ЕГЭ' if exam_type == 'ege' else 'ОГЭ'}</b>\n"
        f"Предметы: <b>{len(subjects)}</b> выбрано",
        reply_markup=settings_menu_keyboard(exam_type, subjects),
        parse_mode="HTML",
    )
