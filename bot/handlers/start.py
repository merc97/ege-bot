from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import (
    main_menu_keyboard, parent_menu_keyboard, role_keyboard,
    exam_type_keyboard, subjects_keyboard,
)
from bot.states.states import OnboardingStates
from bot.utils.api_client import APIClient

router = Router()

WELCOME_TEXT = (
    "👋 Привет, <b>{name}</b>!\n\n"
    "Я помогу подготовиться к <b>ЕГЭ и ОГЭ</b>.\n\n"
    "Сначала скажи — ты ученик или родитель? 👇"
)

MAIN_MENU_TEXT = "📚 <b>Главное меню</b>\n\nВыбери действие:"
PARENT_MENU_TEXT = "👨‍👩‍👧 <b>Меню родителя</b>\n\nВыбери действие:"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, api: APIClient):
    await state.clear()
    user = await api.get_user(message.from_user.id)

    if user and user.get("onboarding_done"):
        if user.get("role") == "parent":
            await message.answer(PARENT_MENU_TEXT, reply_markup=parent_menu_keyboard(), parse_mode="HTML")
        else:
            await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")
        return

    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.first_name),
        reply_markup=role_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(OnboardingStates.choosing_role)


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, state: FSMContext, api: APIClient):
    await state.clear()
    user = await api.get_user(callback.from_user.id)
    if user and user.get("role") == "parent":
        await callback.message.edit_text(PARENT_MENU_TEXT, reply_markup=parent_menu_keyboard(), parse_mode="HTML")
    else:
        await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


# ── Onboarding: role ──────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.choosing_role, F.data.startswith("onboard:role:"))
async def choose_role(callback: CallbackQuery, state: FSMContext, api: APIClient):
    role = callback.data.split(":")[2]
    await state.update_data(role=role)

    if role == "parent":
        await callback.message.edit_text(
            "👨‍👩‍👧 <b>Режим родителя</b>\n\n"
            "Ты сможешь следить за прогрессом своего ребёнка и оплатить ему Premium.\n\n"
            "Для привязки попроси ребёнка открыть бот → <b>⚙️ Настройки → Мой код</b> "
            "и отправь этот код мне.\n\n"
            "Введи код ученика:",
            parse_mode="HTML",
        )
        await state.set_state(OnboardingStates.linking_student)
    else:
        await callback.message.edit_text(
            "📘 <b>Выбери экзамен:</b>",
            reply_markup=exam_type_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(OnboardingStates.choosing_exam)
    await callback.answer()


# ── Onboarding: parent linking ────────────────────────────────────────────────

@router.message(OnboardingStates.linking_student)
async def link_student_code(message: Message, state: FSMContext, api: APIClient):
    code = (message.text or "").strip().upper()
    result = await api.link_student(message.from_user.id, code)

    if result.get("error"):
        await message.answer(
            "❌ Код не найден. Проверь код и попробуй ещё раз.\n"
            "<i>Код ученика: ⚙️ Настройки → Мой код</i>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    await api.complete_onboarding(message.from_user.id, role="parent")
    await state.clear()

    student_name = result.get("linked_student_id") and "ученик" or "ученик"
    await message.answer(
        "✅ <b>Привязка выполнена!</b>\n\n"
        "Теперь ты можешь видеть прогресс и историю ответов своего ребёнка.",
        reply_markup=parent_menu_keyboard(),
        parse_mode="HTML",
    )


# ── Onboarding: student exam + subjects ──────────────────────────────────────

@router.callback_query(OnboardingStates.choosing_exam, F.data.startswith("onboard:exam:"))
async def choose_exam(callback: CallbackQuery, state: FSMContext):
    exam = callback.data.split(":")[2]
    await state.update_data(exam=exam, subjects=[])
    label = "ЕГЭ" if exam == "ege" else "ОГЭ"
    await callback.message.edit_text(
        f"✅ Выбран <b>{label}</b>\n\n"
        "Выбери предметы для подготовки.\n"
        "<i>Можно несколько — нажми «Далее» когда закончишь.</i>",
        reply_markup=subjects_keyboard(exam_type=exam),
        parse_mode="HTML",
    )
    await state.set_state(OnboardingStates.choosing_subjects)
    await callback.answer()


@router.callback_query(OnboardingStates.choosing_subjects, F.data.startswith("subject:"))
async def toggle_subject(callback: CallbackQuery, state: FSMContext, api: APIClient):
    data = await state.get_data()
    key = callback.data.split(":")[1]

    if key == "done":
        subjects = data.get("subjects", [])
        if not subjects:
            await callback.answer("Выбери хотя бы один предмет!", show_alert=True)
            return
        exam = data["exam"]
        role = data.get("role", "student")
        await api.complete_onboarding(callback.from_user.id, exam=exam, subjects=subjects, role=role)
        await state.clear()
        await callback.message.edit_text(
            "🎉 <b>Готово!</b>\n\n"
            f"Экзамен: <b>{'ЕГЭ' if exam == 'ege' else 'ОГЭ'}</b>  |  "
            f"Предметов: <b>{len(subjects)}</b>\n\n"
            "Удачи в подготовке! 💪",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer("Настройка завершена!")
        return

    subjects: list[str] = data.get("subjects", [])
    if key in subjects:
        subjects.remove(key)
    else:
        subjects.append(key)
    await state.update_data(subjects=subjects)
    await callback.message.edit_reply_markup(
        reply_markup=subjects_keyboard(exam_type=data["exam"], selected=subjects)
    )
    await callback.answer()
