import os
import sys
import logging
from typing import Dict, Optional
from pathlib import Path

import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Add bot directory to Python path for local imports
sys.path.insert(0, str(Path(__file__).parent))

# Initialize centralized logging from local config
from logging_config import setup_logging, get_logger

setup_logging(service_name="bot")
logger = get_logger(__name__)

# Конфігурація
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

if TELEGRAM_BOT_TOKEN is None or TELEGRAM_BOT_TOKEN.strip() == "":
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the environment variables!")

PHOTO, NAME, PROFESSION, DESCRIPTION = range(4)

user_data_storage: Dict[int, dict] = {}


def get_friends() -> dict:
    """Get a list of all friends from the backend"""
    try:
        response = requests.get(f"{BACKEND_BASE_URL}/friends", timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        logger.error("Error getting friends: %s", e)
        return {"success": False, "error": str(e)}


def get_friend_by_id(friend_id: int) -> dict:
    """Get a friend by ID"""
    try:
        response = requests.get(f"{BACKEND_BASE_URL}/friends/{friend_id}", timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        logger.error("Error getting friend %s: %s", friend_id, e)
        return {"success": False, "error": str(e)}


def create_friend(
    photo_path: str, name: str, profession: str, description: Optional[str] = None
) -> dict:
    """Create a new friend via API"""
    try:
        with open(photo_path, "rb") as photo_file:
            # Explicitly set the content type as image/jpeg
            files = {"photo": ("photo.jpg", photo_file, "image/jpeg")}
            data = {
                "name": name,
                "profession": profession,
            }
            if description:
                data["profession_description"] = description

            response = requests.post(
                f"{BACKEND_BASE_URL}/friends", files=files, data=data, timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        logger.error("Error creating friend: %s", e)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return {"success": False, "error": str(e)}


def ask_llm(friend_id: int, question: str) -> dict:
    """Ask a question about a friend's profession"""
    try:
        response = requests.post(
            f"{BACKEND_BASE_URL}/friends/{friend_id}/ask",
            json={"question": question},
            timeout=15
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        logger.error("Error asking LLM: %s", e)
        return {"success": False, "error": str(e)}


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /start"""
    if not update.message:
        # Handle cases where there is no message in the update
        logger.warning("Update does not contain a message.")
        return

    user = update.effective_user
    if not user:
        await update.message.reply_text(
            "❌ Не вдалося отримати інформацію про користувача."
        )
        return

    welcome_message = (
        f"👋 Привіт, {user.first_name}!\n\n"
        "Я бот для управління списком друзів.\n\n"
        "📋 Доступні команди:\n"
        "/addfriend - Додати нового друга\n"
        "/list - Показати всіх друзів\n"
        "/friend <id> - Показати друга за ID\n"
        "/ask <id> <питання> - Запитати про професію\n"
        "/help - Показати це повідомлення\n"
        "/cancel - Скасувати поточну операцію"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /help"""
    if not update.message:
        logger.warning("Update does not contain a message.")
        return

    help_text = (
        "📚 *Довідка по командах:*\n\n"
        "**/addfriend** - Додати друга\n"
        "Покроковий сценарій:\n"
        "1️⃣ Надішліть фото\n"
        "2️⃣ Введіть ім'я\n"
        "3️⃣ Введіть професію\n"
        "4️⃣ Введіть опис (або пропустіть)\n\n"
        "**/list** - Показати всіх друзів\n"
        "Відображає список з іменами та професіями\n\n"
        "**/friend <id>** - Показати друга\n"
        "Приклад: `/friend 1`\n\n"
        "**/ask <id> <питання>** - Запитати про професію\n"
        "Приклад: `/ask 1 Які основні проблеми в цій професії?`\n"
        "💡 Відповіді на питання про професію\n\n"
        "**/cancel** - Скасувати операцію"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def list_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /list - show all friends"""
    if not update.message:
        # Handle cases where there is no message in the update
        logger.warning("Update does not contain a message.")
        return

    await update.message.reply_text("🔍 Завантажую список друзів...")

    result = get_friends()

    if not result["success"]:
        await update.message.reply_text(
            f"❌ Помилка при отриманні списку:\n{result['error']}"
        )
        return

    friends = result["data"]

    if not friends:
        await update.message.reply_text(
            "📭 Список друзів порожній. Додайте першого за допомогою /addfriend"
        )
        return

    message = "👥 *Список друзів:*\n\n"
    for friend in friends:
        message += (
            f"🆔 ID: `{friend['id']}`\n"
            f"👤 Ім'я: *{friend['name']}*\n"
            f"💼 Професія: {friend['profession']}\n"
        )
        if friend.get("profession_description"):
            message += f"📝 Опис: _{friend['profession_description']}_\n"
        message += "\n"

    message += "\n💡 Використайте `/friend <id>` для деталей"

    await update.message.reply_text(message, parse_mode="Markdown")


async def show_friend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /friend <id> - show a specific friend"""
    if not update.message:
        logger.warning("Update does not contain a message.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Будь ласка, вкажіть ID друга.\nПриклад: `/friend 1`",
            parse_mode="Markdown",
        )
        return

    try:
        friend_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID має бути числом!")
        return

    await update.message.reply_text(f"🔍 Шукаю друга з ID {friend_id}...")

    result = get_friend_by_id(friend_id)

    if not result["success"]:
        await update.message.reply_text(
            f"❌ Друга з ID {friend_id} не знайдено або сталася помилка:\n{result['error']}"
        )
        return

    friend = result["data"]

    details = (
        f"👤 *{friend['name']}*\n\n"
        f"🆔 ID: `{friend['id']}`\n"
        f"💼 Професія: {friend['profession']}\n"
    )

    if friend.get("profession_description"):
        details += f"📝 Опис: {friend['profession_description']}\n"

    details += f"\n🔗 Фото: {BACKEND_BASE_URL}{friend['photo_url']}"

    await update.message.reply_text(details, parse_mode="Markdown")

    try:
        photo_url = f"{BACKEND_BASE_URL}{friend['photo_url']}"
        await update.message.reply_photo(photo=photo_url)
    except Exception as e:
        logger.error("Cannot upload photo: %s", e)
        await update.message.reply_text("⚠️ Не вдалося завантажити фото")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /ask <id> <question> - ask about friend's profession"""
    if not update.message:
        logger.warning("Update does not contain a message.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Formato: /ask <id> <question>\n"
            "Приклад: /ask 1 Які основні проблеми в цій професії?",
            parse_mode="Markdown",
        )
        return

    try:
        friend_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID має бути числом!")
        return

    # Join remaining args as the question
    question = " ".join(context.args[1:])

    if not question or len(question) > 500:
        await update.message.reply_text(
            "❌ Запитання має бути від 1 до 500 символів!"
        )
        return

    await update.message.reply_text(f"🤔 Обробляю запитання для друга #{friend_id}...")

    result = ask_llm(friend_id, question)

    if not result["success"]:
        await update.message.reply_text(
            f"❌ Помилка: {result['error']}"
        )
        return

    answer = result["data"].get("answer", "No answer received")
    await update.message.reply_text(f"💬 *Відповідь:*\n\n{answer}", parse_mode="Markdown")


async def add_friend_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process of adding a friend"""
    if not update.message or not update.effective_user:
        logger.warning("Update does not contain a message or user.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    user_data_storage[user_id] = {}

    await update.message.reply_text(
        "📸 Крок 1/4: Надішліть фото друга\n\n" "Використайте /cancel для скасування",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PHOTO


async def add_friend_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process photo"""
    if not update.message or not update.effective_user:
        logger.warning("Update does not contain a message or user.")
        return ConversationHandler.END

    user_id = update.effective_user.id

    photo_file = await update.message.photo[-1].get_file()

    photo_path = f"temp_photo_{user_id}.jpg"
    await photo_file.download_to_drive(photo_path)

    user_data_storage[user_id]["photo_path"] = photo_path

    await update.message.reply_text(
        "✅ Фото отримано!\n\n" "👤 Крок 2/4: Введіть ім'я друга"
    )
    return NAME


async def add_friend_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process name"""
    if not update.message or not update.effective_user:
        logger.warning("Update does not contain a message or user.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    name = update.message.text.strip() if update.message.text else ""

    if not name or len(name) > 255:
        await update.message.reply_text(
            "❌ Ім'я має містити від 1 до 255 символів. Спробуйте ще раз:"
        )
        return NAME

    user_data_storage[user_id]["name"] = name

    await update.message.reply_text(
        f"✅ Ім'я: {name}\n\n" "💼 Крок 3/4: Введіть професію друга"
    )
    return PROFESSION


async def add_friend_profession(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Process profession"""
    if not update.message or not update.effective_user:
        logger.warning("Update does not contain a message or user.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    profession = update.message.text.strip() if update.message.text else ""

    if not profession or len(profession) > 255:
        await update.message.reply_text(
            "❌ Професія має містити від 1 до 255 символів. Спробуйте ще раз:"
        )
        return PROFESSION

    user_data_storage[user_id]["profession"] = profession

    keyboard = [["Пропустити"]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )

    await update.message.reply_text(
        f"✅ Професія: {profession}\n\n"
        "📝 Крок 4/4: Введіть опис професії (необов'язково)\n\n"
        "Або натисніть 'Пропустити'",
        reply_markup=reply_markup,
    )
    return DESCRIPTION


async def add_friend_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Process description and create friend"""
    if not update.message or not update.effective_user:
        logger.warning("Update does not contain a message or user.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    description = update.message.text.strip() if update.message.text else ""

    if description.lower() != "пропустити":
        user_data_storage[user_id]["description"] = description

    await update.message.reply_text(
        "⏳ Створюю друга...", reply_markup=ReplyKeyboardRemove()
    )

    data = user_data_storage[user_id]

    result = create_friend(
        photo_path=data["photo_path"],
        name=data["name"],
        profession=data["profession"],
        description=data.get("description", ""),
    )

    try:
        os.remove(data["photo_path"])
    except OSError as e:
        logger.error("Cannot delete temporary photo: %s", e)

    del user_data_storage[user_id]

    if result["success"]:
        friend = result["data"]
        success_message = (
            "✅ *Друга успішно створено!*\n\n"
            f"🆔 ID: `{friend['id']}`\n"
            f"👤 Ім'я: *{friend['name']}*\n"
            f"💼 Професія: {friend['profession']}\n"
        )
        if friend.get("profession_description"):
            success_message += f"📝 Опис: {friend['profession_description']}\n"

        await update.message.reply_text(success_message, parse_mode="Markdown")
        await update.message.reply_text(
            "💡 Використайте /list для перегляду всіх друзів"
        )
    else:
        await update.message.reply_text(
            f"❌ Помилка при створенні друга:\n{result['error']}\n\n"
            "Спробуйте ще раз командою /addfriend"
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасування процесу додавання"""
    if not update.message or not update.effective_user:
        logger.warning("Update does not contain a message or user.")
        return ConversationHandler.END

    user_id = update.effective_user.id

    # Видалення тимчасового фото якщо існує
    if user_id in user_data_storage:
        if "photo_path" in user_data_storage[user_id]:
            try:
                os.remove(user_data_storage[user_id]["photo_path"])
            except Exception as e:
                logger.error(f"Cannot delete temporary photo: {e}")
        del user_data_storage[user_id]

    await update.message.reply_text(
        "❌ Операцію скасовано.\n\n"
        "Використайте /help для перегляду доступних команд.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    """Start the bot"""
    logger.info("Starting Telegram bot...")
    logger.info("Backend URL: %s", BACKEND_BASE_URL)

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler для додавання друга
    add_friend_handler = ConversationHandler(
        entry_points=[CommandHandler("addfriend", add_friend_start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, add_friend_photo)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_friend_name)],
            PROFESSION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_friend_profession)
            ],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_friend_description)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Додавання handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_friends))
    application.add_handler(CommandHandler("friend", show_friend))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(add_friend_handler)

    # Запуск бота (long polling)
    logger.info("Bot started! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
