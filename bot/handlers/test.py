import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import (
    test_subject_keyboard, test_mode_keyboard, answer_options_keyboard,
    next_question_keyboard, main_menu_keyboard
)
from bot.states.states import TestStates
from bot.utils.api_client import APIClient

router = Router()

SUBJECT_LABELS = {
    "math": "Математика", "russian": "Русский язык", "physics": "Физика",
    "chemistry": "Химия", "biology": "Биология", "history": "История",
    "social": "Обществознание", "english": "Английский", "informatics": "Информатика",
}


@router.callback_query(F.data == "menu:test")
async def test_menu(callback: CallbackQuery, state: FSMContext, api: APIClient):
    await state.clear()
    user = await api.get_user(callback.from_user.id)
    exam_type = user.get("selected_exam", "ege") if user else "ege"
    subjects = user.get("selected_subjects") if user else None
    await state.update_data(exam_type=exam_type)

    await callback.message.edit_text(
        "📚 <b>Выберите предмет:</b>",
        reply_markup=test_subject_keyboard(exam_type, subjects),
        parse_mode="HTML",
    )
    await state.set_state(TestStates.choosing_subject)
    await callback.answer()


@router.callback_query(TestStates.choosing_subject, F.data.startswith("test:subject:"))
async def choose_subject(callback: CallbackQuery, state: FSMContext):
    subject = callback.data.split(":")[2]
    await state.update_data(subject=subject)
    await callback.message.edit_text(
        "🎯 <b>Выберите режим:</b>\n\n"
        "• <b>Практика</b> — решаем по одному, без ограничений\n"
        "• <b>Мини-экзамен</b> — 10 вопросов подряд, итог в конце",
        reply_markup=test_mode_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(TestStates.choosing_mode)
    await callback.answer()


@router.callback_query(TestStates.choosing_mode, F.data.startswith("mode:"))
async def choose_mode_start(callback: CallbackQuery, state: FSMContext, api: APIClient):
    mode = callback.data.split(":")[1]
    data = await state.get_data()

    try:
        session = await api.create_session(
            telegram_id=callback.from_user.id,
            subject=data["subject"],
            exam_type=data["exam_type"],
            mode=mode,
        )
    except Exception:
        await callback.answer("Ошибка соединения, попробуй позже.", show_alert=True)
        return

    await state.update_data(session_id=session["id"], mode=mode, question_count=0)
    await state.set_state(TestStates.in_progress)
    await callback.answer()
    await _send_next_question(callback.message, state, api, edit=True)


async def _send_next_question(msg, state: FSMContext, api: APIClient, edit: bool = False) -> None:
    data = await state.get_data()
    task = await api.get_next_task(
        session_id=data["session_id"],
        telegram_id=msg.chat.id,
        subject=data["subject"],
        exam_type=data["exam_type"],
    )
    if not task:
        await _finish_flow(msg, state, api, edit=edit)
        return

    await state.update_data(
        current_task_id=task["id"],
        task_has_options=bool(task.get("options")),
        task_start=time.time(),
    )

    subj_name = SUBJECT_LABELS.get(data["subject"], data["subject"])
    task_num = f"Задание {task['task_number']}" if task.get("task_number") else "Задание"
    text = f"📌 <b>{subj_name} · {task_num}</b>\n\n{task['question_text']}"

    if task.get("options"):
        opts: dict = task["options"]
        for k, v in opts.items():
            text += f"\n\n<b>{k})</b> {v}"
        kb = answer_options_keyboard(list(opts.keys()))
    else:
        kb = None
        text += "\n\n✏️ <i>Введите ваш ответ числом или словом:</i>"

    if edit:
        await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(TestStates.in_progress, F.data.startswith("test:answer:"))
async def handle_choice_answer(callback: CallbackQuery, state: FSMContext, api: APIClient):
    user_answer = callback.data.split(":")[2]
    await callback.answer()
    await _process_answer(callback.message, state, api, user_answer, edit=True)


@router.message(TestStates.in_progress)
async def handle_text_answer(message: Message, state: FSMContext, api: APIClient):
    data = await state.get_data()
    if data.get("task_has_options"):
        await message.answer("⚠️ Пожалуйста, используй кнопки выше.")
        return
    await _process_answer(message, state, api, message.text or "", edit=False)


async def _process_answer(msg, state: FSMContext, api: APIClient, user_answer: str, edit: bool) -> None:
    data = await state.get_data()
    elapsed = int(time.time() - data.get("task_start", time.time()))

    try:
        result = await api.submit_answer(
            session_id=data["session_id"],
            task_id=data["current_task_id"],
            user_answer=user_answer,
            time_spent=elapsed,
        )
    except Exception:
        await msg.answer("Ошибка отправки ответа. Попробуй снова.")
        return

    if result["is_correct"]:
        text = "✅ <b>Верно!</b> Отличная работа."
    else:
        text = (
            f"❌ <b>Неверно.</b>\n"
            f"Правильный ответ: <code>{result['correct_answer']}</code>"
        )
        if result.get("hint"):
            text += f"\n\n💡 <i>{result['hint']}</i>"
        if result.get("ai_explanation"):
            text += f"\n\n🤖 <b>Разбор ошибки:</b>\n{result['ai_explanation']}"

    q_count = data.get("question_count", 0) + 1
    await state.update_data(question_count=q_count)

    max_q = 10 if data.get("mode") == "exam" else 9999
    kb = next_question_keyboard(is_last=(q_count >= max_q), session_id=data["session_id"])

    if edit:
        await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("test:next:"))
async def next_question(callback: CallbackQuery, state: FSMContext, api: APIClient):
    await callback.answer()
    await _send_next_question(callback.message, state, api, edit=True)


@router.callback_query(F.data.startswith("test:finish:"))
async def finish_test(callback: CallbackQuery, state: FSMContext, api: APIClient):
    await callback.answer()
    await _finish_flow(callback.message, state, api, edit=True)


async def _finish_flow(msg, state: FSMContext, api: APIClient, edit: bool = False) -> None:
    data = await state.get_data()
    try:
        session = await api.finish_session(data["session_id"])
    except Exception:
        await msg.answer("Ошибка завершения сессии.")
        await state.clear()
        return

    total = session["total_questions"]
    correct = session["correct_answers"]
    pct = round(correct / total * 100) if total > 0 else 0

    if pct >= 80:
        icon, comment = "🏆", "Отличный результат! Ты готов к экзамену."
    elif pct >= 50:
        icon, comment = "📈", "Неплохо! Есть куда расти."
    else:
        icon, comment = "📚", "Стоит повторить эту тему ещё раз."

    text = (
        f"{icon} <b>Сессия завершена!</b>\n\n"
        f"✅ Верно: <b>{correct}</b> из <b>{total}</b> ({pct}%)\n\n"
        f"{comment}"
    )
    if edit:
        await msg.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    else:
        await msg.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await state.clear()
