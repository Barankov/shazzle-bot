# 🔧 Shazzle Bot для Render.com

Готовый Telegram-бот для бесплатного хостинга Render.com (сервер в США, никаких блокировок).

## 📋 Что нужно перед началом

1. **Аккаунт GitHub** — бесплатный
2. **Аккаунт Render.com** — бесплатный (регистрация через GitHub)
3. **Токен Telegram-бота** — @BotFather → /newbot
4. **Ключ OpenRouter** — openrouter.ai → Keys → Create Key

## 🚀 Пошаговый запуск

### Шаг 1: Создать репозиторий на GitHub

1. Перейди на github.com → нажми **+** → **New repository**
2. Название: `shazzle-bot`
3. **Public** (бесплатно) или **Private** (тоже бесплатно)
4. Нажми **Create repository**

### Шаг 2: Загрузить файлы

На странице репозитория:
1. Нажми **"uploading an existing file"**
2. Перетащи все 4 файла из этого архива:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
3. Нажми **Commit changes**

### Шаг 3: Подключить Render.com

1. Перейди на [render.com](https://render.com)
2. Нажми **Sign Up** → выбери **Continue with GitHub**
3. В дашборде нажми **New +** → **Web Service**
4. Выбери свой репозиторий `shazzle-bot`
5. Настройки:
   - **Name**: `shazzle-bot`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Plan**: Free
6. Нажми **Create Web Service**

### Шаг 4: Добавить переменные окружения (Environment Variables)

В настройках сервиса на Render:
1. Перейди во вкладку **Environment**
2. Добавь 2 переменные:

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | твой токен от @BotFather |
| `OPENROUTER_KEY` | твой ключ с openrouter.ai |

3. Нажми **Save Changes**
4. Render автоматически перезапустит бота

### Шаг 5: Настроить UptimeRobot (чтобы Render не засыпал)

Render бесплатный тир "засыпает" после 15 минут неактивности. Чтобы бот работал 24/7:

1. Перейди на [uptimerobot.com](https://uptimerobot.com)
2. Зарегистрируйся (бесплатно)
3. Нажми **Add New Monitor**
4. Настройки:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Shazzle Bot
   - **URL**: `https://shazzle-bot.onrender.com` (твой URL с Render)
   - **Monitoring Interval**: Every 5 minutes (Free)
5. Нажди **Create Monitor**

Теперь UptimeRobot будет пинговать бота каждые 5 минут, и Render никогда не "заснёт".

### Шаг 6: Проверить

1. Открой своего бота в Telegram
2. Пришли фото сломанной вещи
3. Жди 5-15 секунд — должен прийти диагноз!

## 📊 Лимиты

| Сервис | Лимит |
|--------|-------|
| Render Free | 750 часов/мес (достаточно) |
| OpenRouter Free | ~20-50 запросов/день на модель |
| UptimeRobot Free | Пинг каждые 5 минут |

Если OpenRouter лимит закончится — зайди в `bot.py` на GitHub, измени модель с `meta-llama/llama-4-maverick:free` на `qwen/qwen2.5-vl-32b-instruct:free`, сохрани. Render автоматически перезапустит бота.

## 🛠️ Структура файлов

```
shazzle-bot/
├── bot.py              # Основной скрипт (Flask + Telegram polling)
├── requirements.txt    # Зависимости Python
├── Procfile            # Команда запуска для Render
└── runtime.txt         # Версия Python
```
