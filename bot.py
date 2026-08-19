"""
Shazzle Telegram Bot для Render.com
Бесплатный хостинг, никаких блокировок Telegram API.
"""
import os
import base64
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ═══════════════════════════════════════════════════
# Ключи читаются из переменных окружения (Render → Environment)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
# ═══════════════════════════════════════════════════

SYSTEM_PROMPT = """Ты — Шаззл, эксперт по домашнему ремонту. Проанализируй фото и дай:

🔧 Устройство: [название]
🔍 Диагноз: [описание]
⭐ Сложность: [1-5/5]
💰 Стоимость: [низкая/средняя/высокая]

📋 Инструкция:
1. [шаг]
2. [шаг]
...

🛠️ Инструменты:
- [инструмент]

🔩 Запчасти:
- [запчасть]

🛒 Где купить:
- [🔍 Яндекс.Маркет](https://market.yandex.ru/search?text=ЗАПЧАСТЬ)
- [🛒 Ozon](https://www.ozon.ru/search/?text=ЗАПЧАСТЬ)

📹 Видео: [▶️ YouTube](https://www.youtube.com/results?search_query=как+починить+УСТРОЙСТВО)

📚 iFixit: https://www.ifixit.com/search?query=УСТРОЙСТВО

⚠️ Безопасность:
- [совет]

Правила: отвечай на русском. Если не уверен — скажи честно. Не давай опасных советов. Обращайся на 'ты'."""

# Flask — чтобы Render считал сервис "живым" и не засыпал
app = Flask(__name__)

@app.route("/")
def home():
    return "🔧 Shazzle Bot is running!"


def analyze_photo(photo_bytes: bytes) -> str:
    base64_image = base64.b64encode(photo_bytes).decode("utf-8")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://shazzle.bot",
            "X-Title": "Shazzle Repair Bot"
        },
        json={
            "model": "meta-llama/llama-4-maverick:free",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Что сломалось и как починить?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        },
        timeout=60
    )

    data = response.json()
    return data["choices"][0]["message"]["content"]


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "🔍 Анализирую фото...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()

    try:
        diagnosis = analyze_photo(bytes(photo_bytes))
        await context.bot.send_message(chat_id, diagnosis, parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id, f"❌ Ошибка: {str(e)}\n\nПопробуй ещё раз или напиши текстом.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Пришли мне фото сломанной вещи, и я скажу, что с ней не так и как починить.\n\n"
        "Или напиши, что сломалось — попробую помочь советом."
    )


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🚀 Shazzle Bot запущен на Render!")
    print("Пришли фото в Telegram — получи диагноз.")
    application.run_polling()


if __name__ == "__main__":
    # Flask в отдельном потоке (для keep-alive)
    Thread(target=run_flask).start()
    # Бот в основном потоке
    run_bot()
