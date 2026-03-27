from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import BOT_TOKEN, SUBMISSIONS_PATH, SURVEY_PATH
from bot.submissions import save_submission
from bot.survey import Question, Survey, load_survey
from bot.validators import validate_answer, validate_choice

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

ASKING = 1


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Update %s caused: %s", update, context.error)


def _session_survey(context: ContextTypes.DEFAULT_TYPE) -> Survey:
    s = context.user_data.get("session_survey")
    if isinstance(s, Survey):
        return s
    return load_survey(SURVEY_PATH)


def _choice_keyboard(question: Question) -> InlineKeyboardMarkup:
    choices = question.spec.get("choices") or []
    row: list[InlineKeyboardButton] = []
    rows: list[list[InlineKeyboardButton]] = []
    for i, label in enumerate(choices):
        row.append(InlineKeyboardButton(label, callback_data=f"ans:{i}"))
        if len(row) >= 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def _send_current_question(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, survey: Survey
) -> None:
    idx = context.user_data["q_index"]
    if idx >= len(survey.questions):
        return
    q = survey.questions[idx]
    n = len(survey.questions)
    text = f"Question {idx + 1} of {n}\n\n{q.text}"
    if q.type == "choice":
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=_choice_keyboard(q),
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text=text)


async def _finish_survey(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    survey: Survey,
    user,
    *,
    reply_message=None,
) -> int:
    ud = context.user_data
    record = {
        "submission_id": str(uuid.uuid4()),
        "telegram_user_id": user.id if user else None,
        "username": getattr(user, "username", None),
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "answers": list(ud.get("answers", [])),
    }
    save_submission(SUBMISSIONS_PATH, record)
    ud.clear()
    msg = survey.done_message
    if reply_message is not None:
        await reply_message.reply_text(msg)
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg)
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    ud = context.user_data
    ud.clear()
    survey = load_survey(SURVEY_PATH)
    ud["session_survey"] = survey
    ud["q_index"] = 0
    ud["answers"] = []
    if not survey.questions:
        await update.message.reply_text("No questions are configured in the survey file.")
        return ConversationHandler.END
    parts: list[str] = []
    if survey.welcome:
        parts.append(escape(survey.welcome))
    if survey.title:
        parts.append(f"<b>{escape(survey.title)}</b>")
    body = "\n\n".join(parts).strip()
    if body:
        await update.message.reply_text(body, parse_mode="HTML")
    await _send_current_question(context, update.effective_chat.id, survey)
    return ASKING


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Survey cancelled. Send /start to begin again.")
    context.user_data.clear()
    return ConversationHandler.END


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ASKING
    survey = _session_survey(context)
    ud = context.user_data
    idx = ud.get("q_index", 0)
    if idx >= len(survey.questions):
        return ConversationHandler.END
    q = survey.questions[idx]
    if q.type == "choice":
        await update.message.reply_text("Please use the buttons for this question.")
        return ASKING
    ok, value, err = validate_answer(q, update.message.text)
    if not ok:
        await update.message.reply_text(err or "Invalid answer.")
        return ASKING
    ud.setdefault("answers", []).append(
        {
            "question_id": q.id,
            "question_text": q.text,
            "answer": value,
        }
    )
    ud["q_index"] = idx + 1
    if ud["q_index"] >= len(survey.questions):
        return await _finish_survey(
            context,
            update.effective_chat.id,
            survey,
            update.effective_user,
            reply_message=update.message,
        )
    await _send_current_question(context, update.effective_chat.id, survey)
    return ASKING


async def on_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return ASKING
    survey = _session_survey(context)
    ud = context.user_data
    idx = ud.get("q_index", 0)
    if idx >= len(survey.questions):
        await query.answer()
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        return ConversationHandler.END
    q = survey.questions[idx]
    if q.type != "choice":
        await query.answer()
        return ASKING
    try:
        choice_i = int(query.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await query.answer(text="Invalid button.", show_alert=True)
        return ASKING
    ok, value, err = validate_choice(q, choice_i)
    if not ok:
        await query.answer(text=err or "Invalid choice.", show_alert=True)
        return ASKING
    await query.answer()
    ud.setdefault("answers", []).append(
        {
            "question_id": q.id,
            "question_text": q.text,
            "answer": value,
        }
    )
    ud["q_index"] = idx + 1
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    chat_id = query.message.chat_id if query.message else query.from_user.id
    if ud["q_index"] >= len(survey.questions):
        return await _finish_survey(
            context, chat_id, survey, query.from_user, reply_message=None
        )
    await _send_current_question(context, chat_id, survey)
    return ASKING


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Missing BOT_TOKEN. Copy .env.example to .env and set the token.")
    if not SURVEY_PATH.is_file():
        raise SystemExit(f"Survey file not found: {SURVEY_PATH}")
    survey = load_survey(SURVEY_PATH)
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_text),
                CallbackQueryHandler(on_choice, pattern=r"^ans:\d+$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="survey",
        persistent=False,
    )
    app.add_handler(conv)
    app.add_error_handler(_error_handler)
    log.info("Bot starting, survey has %s questions", len(survey.questions))
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
