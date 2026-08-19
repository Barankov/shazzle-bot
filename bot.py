import os
import base64
import asyncio
import requests
from aiohttp import web
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", f"https://{RENDER_HOST}/webhook" if RENDER_HOST else "")

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
        diagnosis = await asyncio.to_thread(analyze_photo, bytes(photo_bytes))
        await context.bot.send_message(chat_id, diagnosis, parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Пришли мне фото сломанной вещи, и я скажу, что с ней не так и как починить."
    )

async def health(request):
    return web.Response(text="🔧 Shazzle Bot is running!")

async def webhook(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response(text="OK")

application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

async def on_startup(app):
    await application.initialize()
    await application.start()
    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)

async def on_cleanup(app):
    await application.stop()
    await application.shutdown()

app = web.Application()
app.router.add_get("/", health)
app.router.add_post("/webhook", webhook)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)