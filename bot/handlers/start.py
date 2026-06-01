from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import (
    main_menu_keyboard, exam_type_keyboard, subjects_keyboard, back_to_menu_keyboard
)
from bot.states.states import OnboardingStates
from bot.utils.api_client import APIClient

router = Router()

WELCOME_TEXT = (
    "👋 Привет, <b>{name}</b>!\n\n"
    "Я помогу тебе подготовиться к <b>ЕГЭ и ОГЭ</b>.\n\n"
    "• Тренируйся по заданиям в любое время\n"
    "• Получай AI-объяснения своих ошибок\n"
    "• Следи за прогрессом по темам\n\n"
    "Давай настроим бот под тебя — это займёт 10 секунд 👇"
)

MAIN_MENU_TEXT = (
    "📚 <b>Главное меню</b>\n\n"
    "Выбери действие:"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, api: APIClient):
    await state.clear()
    user = await api.get_user(message.from_user.id)

    if user and user.get("onboarding_done"):
        await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")
        return

    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.first_name),
        reply_markup=exam_type_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(OnboardingStates.choosing_exam)


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(OnboardingStates.choosing_exam, F.data.startswith("onboard:exam:"))
async def choose_exam(callback: CallbackQuery, state: FSMContext):
    exam = callback.data.split(":")[2]
    await state.update_data(exam=exam, subjects=[])
    label = "ЕГЭ" if exam == "ege" else "ОГЭ"
    await callback.message.edit_text(
        f"✅ Выбран <b>{label}</b>\n\n"
        "Теперь выбери предметы, которые хочешь готовить.\n"
        "<i>Можно выбрать несколько — нажми «Далее» когда закончишь.</i>",
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
        await api.complete_onboarding(callback.from_user.id, exam, subjects)
        await state.clear()
        await callback.message.edit_text(
            "🎉 <b>Отлично! Всё готово.</b>\n\n"
            f"Экзамен: <b>{'ЕГЭ' if exam == 'ege' else 'ОГЭ'}</b>\n"
            f"Предметы: <b>{len(subjects)}</b>\n\n"
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
