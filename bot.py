import os
import base64
import asyncio
import requests
import logging
import json
import sys
import time
import traceback
from aiohttp import web
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "").strip()
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", f"https://{RENDER_HOST}/webhook" if RENDER_HOST else "")

# Проверка ключей при старте
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не задан!")
    sys.exit(1)
if not OPENROUTER_KEY:
    logger.error("OPENROUTER_KEY не задан!")
    sys.exit(1)

logger.info(f"Webhook URL: {WEBHOOK_URL}")
logger.info(f"OpenRouter key (первые 8 симв): {OPENROUTER_KEY[:8]}...")

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

# Список бесплатных vision-моделей (по приоритету)
VISION_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "meta-llama/llama-4-maverick:free",
]


def call_openrouter(base64_image: str, model: str) -> dict:
    """Делает запрос к OpenRouter. Возвращает JSON или бросает исключение."""
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://shazzle.bot",
            "X-Title": "Shazzle Repair Bot"
        },
        json={
            "model": model,
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
        timeout=90
    )

    # Логируем статус и тело ответа
    logger.info(f"OpenRouter status: {response.status_code}")
    if response.status_code != 200:
        logger.error(f"OpenRouter error body: {response.text[:500]}")
        response.raise_for_status()

    data = response.json()
    logger.info(f"OpenRouter response keys: {list(data.keys())}")

    if "choices" not in data:
        logger.error(f"OpenRouter response (no choices): {json.dumps(data, ensure_ascii=False)[:500]}")
        raise ValueError(f"Нет 'choices' в ответе. Ключи: {list(data.keys())}")

    return data


def analyze_photo(photo_bytes: bytes) -> str:
    base64_image = base64.b64encode(photo_bytes).decode("utf-8")

    last_error = None
    for model in VISION_MODELS:
        try:
            logger.info(f"Пробую модель: {model}")
            data = call_openrouter(base64_image, model)
            content = data["choices"][0]["message"]["content"]
            logger.info(f"Модель {model} ответила успешно")
            return content
        except Exception as e:
            logger.warning(f"Модель {model} не сработала: {e}")
            last_error = e
            time.sleep(1)  # Небольшая пауза перед fallback

    raise last_error if last_error else Exception("Все модели отказали")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "🔍 Анализирую фото...")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        diagnosis = await asyncio.to_thread(analyze_photo, bytes(photo_bytes))
        await context.bot.send_message(chat_id, diagnosis, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {traceback.format_exc()}")
        await context.bot.send_message(
            chat_id,
            f"❌ Ошибка анализа: {str(e)[:300]}\n\n"
            f"Возможные причины:\n"
            f"• Лимит OpenRouter исчерпан (попробуй позже)\n"
            f"• Неверный ключ OpenRouter\n"
            f"• Модель временно недоступна\n\n"
            f"Попробуй ещё раз через минуту."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Пришли мне фото сломанной вещи, и я скажу, что с ней не так и как починить."
    )


async def health(request):
    return web.Response(text="🔧 Shazzle Bot is running!")


async def webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        logger.error(f"Webhook error: {traceback.format_exc()}")
        return web.Response(text="ERROR", status=500)


application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


async def on_startup(app):
    await application.initialize()
    await application.start()
    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook установлен: {WEBHOOK_URL}")


async def on_cleanup(app):
    await application.stop()
    await application.shutdown()


aio_app = web.Application()
aio_app.router.add_get("/", health)
aio_app.router.add_post("/webhook", webhook)
aio_app.on_startup.append(on_startup)
aio_app.on_cleanup.append(on_cleanup)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(aio_app, host="0.0.0.0", port=port)