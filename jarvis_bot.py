import os
import asyncio
import logging
from datetime import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import json

# ============ НАСТРОЙКИ ============

TELEGRAM_TOKEN = “7751101213:AAE4KHao2ExAUb5fW6SmkX4hie2XR1dlKk8”
GROQ_API_KEY = “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”
GROQ_API_URL = “https://api.groq.com/openai/v1/chat/completions”

# Hash Hedge лимиты

ACCOUNT_SIZE = 150000
MAX_DAILY_LOSS = 7500   # 5%
MAX_TOTAL_LOSS = 15000  # 10% Stage 1

# Топ-10 монет

TOP_10 = [“BTCUSDT”, “ETHUSDT”, “BNBUSDT”, “SOLUSDT”, “XRPUSDT”,
“DOGEUSDT”, “ADAUSDT”, “AVAXUSDT”, “TONUSDT”, “LINKUSDT”]

# Хранение данных пользователя

user_data = {
“daily_loss”: 0,
“total_loss”: 0,
“trades”: [],
“stage”: 1,
“mood”: None,
“last_signal”: None
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

# ============ ПОЛУЧЕНИЕ ДАННЫХ ============

def get_crypto_price(symbol):
try:
url = f”https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}”
r = requests.get(url, timeout=5)
data = r.json()
return {
“price”: float(data[“lastPrice”]),
“change”: float(data[“priceChangePercent”]),
“volume”: float(data[“quoteVolume”]),
“high”: float(data[“highPrice”]),
“low”: float(data[“lowPrice”])
}
except:
return None

def get_fear_greed():
try:
r = requests.get(“https://api.alternative.me/fng/”, timeout=5)
data = r.json()
return data[“data”][0][“value”], data[“data”][0][“value_classification”]
except:
return “50”, “Neutral”

def get_sp500():
try:
url = “https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=2d”
headers = {“User-Agent”: “Mozilla/5.0”}
r = requests.get(url, headers=headers, timeout=5)
data = r.json()
closes = data[“chart”][“result”][0][“indicators”][“quote”][0][“close”]
change = ((closes[-1] - closes[-2]) / closes[-2]) * 100
return closes[-1], change
except:
return None, None

def get_btc_dominance():
try:
r = requests.get(“https://api.coingecko.com/api/v3/global”, timeout=5)
data = r.json()
return data[“data”][“market_cap_percentage”][“btc”]
except:
return None

def get_market_data():
“”“Собирает все данные рынка”””
prices = {}
for symbol in TOP_10:
data = get_crypto_price(symbol)
if data:
prices[symbol] = data

```
fg_value, fg_class = get_fear_greed()
sp500_price, sp500_change = get_sp500()
btc_dom = get_btc_dominance()

return {
    "prices": prices,
    "fear_greed": {"value": fg_value, "class": fg_class},
    "sp500": {"price": sp500_price, "change": sp500_change},
    "btc_dominance": btc_dom
}
```

# ============ GROQ АНАЛИЗ ============

def analyze_with_groq(prompt):
headers = {
“Authorization”: f”Bearer {GROQ_API_KEY}”,
“Content-Type”: “application/json”
}

```
system_prompt = """Ты Джарвис — профессиональный торговый ИИ-ассистент с 20-летним опытом.
```

Специализируешься на методе Вайкоффа + ликвидационные зоны + макро анализ.
Торгуешь только уверенные сделки с соотношением риск/прибыль минимум 1:3.
Отвечаешь чётко, по делу, без воды. Используешь эмодзи для наглядности.
Всегда учитываешь лимиты проп-фирмы Hash Hedge.”””

```
data = {
    "model": "llama-3.3-70b-versatile",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ],
    "max_tokens": 1000,
    "temperature": 0.3
}

try:
    r = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
    result = r.json()
    return result["choices"][0]["message"]["content"]
except Exception as e:
    return f"Ошибка анализа: {str(e)}"
```

# ============ ПРОВЕРКА РИСКОВ ============

def check_risk_limits():
daily_used = (user_data[“daily_loss”] / MAX_DAILY_LOSS) * 100
total_used = (user_data[“total_loss”] / MAX_TOTAL_LOSS) * 100

```
if user_data["daily_loss"] >= MAX_DAILY_LOSS:
    return False, "🚫 СТОП! Дневной лимит просадки достигнут ($7,500). Торговля запрещена сегодня!"

if user_data["total_loss"] >= MAX_TOTAL_LOSS:
    return False, "🚫 СТОП! Общий лимит просадки достигнут ($15,000). Срочно свяжитесь с Hash Hedge!"

if daily_used >= 70:
    return True, f"⚠️ Осторожно! Использовано {daily_used:.0f}% дневного лимита. Торгуй очень осторожно!"

return True, f"✅ Лимиты в норме. Дневная просадка: ${user_data['daily_loss']:,.0f} из $7,500"
```

# ============ КОМАНДЫ БОТА ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
keyboard = [
[InlineKeyboardButton(“📊 Анализ рынка”, callback_data=“market”)],
[InlineKeyboardButton(“💰 Мои лимиты”, callback_data=“limits”)],
[InlineKeyboardButton(“🔍 Найти сигнал”, callback_data=“signal”)],
[InlineKeyboardButton(“😊 Психо-чек”, callback_data=“mood”)],
[InlineKeyboardButton(“📈 Журнал сделок”, callback_data=“journal”)]
]
reply_markup = InlineKeyboardMarkup(keyboard)

```
await update.message.reply_text(
    "🤖 *ДЖАРВИС TRADING* — онлайн!\n\n"
    "Твой профессиональный торговый ассистент.\n"
    "Метод Вайкоффа + Ликвидации + Макро анализ\n\n"
    "💼 Аккаунт: Hash Hedge $150,000\n"
    "🎯 Топ-10 крипто монеты\n\n"
    "Выбери действие:",
    parse_mode="Markdown",
    reply_markup=reply_markup
)
```

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
if query.data == "market":
    await query.edit_message_text("⏳ Собираю данные рынка...")
    await market_analysis(query, context)

elif query.data == "limits":
    await show_limits(query, context)

elif query.data == "signal":
    await query.edit_message_text("⏳ Ищу сигналы по трёхмозговой системе...")
    await find_signal(query, context)

elif query.data == "mood":
    await mood_check(query, context)

elif query.data == "journal":
    await show_journal(query, context)

elif query.data.startswith("mood_"):
    mood = query.data.split("_")[1]
    user_data["mood"] = mood
    if mood == "bad":
        await query.edit_message_text(
            "😔 Понял тебя. Сегодня лучше не торговать.\n\n"
            "Плохое настроение = плохие решения = потеря денег.\n"
            "Отдохни, завтра рынок никуда не денется. 💪"
        )
    else:
        await query.edit_message_text(
            "💪 Отлично! Настрой боевой.\n\n"
            "Помни правила:\n"
            "✅ Только уверенные сетапы\n"
            "✅ Риск/прибыль минимум 1:3\n"
            "✅ Следи за лимитами\n\n"
            "Удачной торговли! 🚀"
        )
```

async def market_analysis(query, context):
data = get_market_data()

```
prices_text = ""
for symbol, info in data["prices"].items():
    name = symbol.replace("USDT", "")
    emoji = "🟢" if info["change"] > 0 else "🔴"
    prices_text += f"{emoji} {name}: ${info['price']:,.2f} ({info['change']:+.1f}%)\n"

fg = data["fear_greed"]
sp = data["sp500"]
btc_dom = data["btc_dominance"]

fg_emoji = "😱" if int(fg["value"]) < 25 else "😰" if int(fg["value"]) < 45 else "😐" if int(fg["value"]) < 55 else "😊" if int(fg["value"]) < 75 else "🤑"
sp_emoji = "🟢" if sp["change"] and sp["change"] > 0 else "🔴"

market_text = f"""📊 *АНАЛИЗ РЫНКА — {datetime.now().strftime('%H:%M')}*
```

*Топ-10 Крипто:*
{prices_text}
{fg_emoji} *Страх & Жадность:* {fg[“value”]} — {fg[“class”]}
{sp_emoji} *S&P 500:* {’$’ + f”{sp[‘price’]:,.0f}” if sp[‘price’] else ‘н/д’} ({f”{sp[‘change’]:+.1f}%” if sp[‘change’] else ‘н/д’})
📊 *BTC Доминация:* {f”{btc_dom:.1f}%” if btc_dom else ‘н/д’}”””

```
keyboard = [[InlineKeyboardButton("🔍 Найти сигнал", callback_data="signal"),
             InlineKeyboardButton("🔄 Обновить", callback_data="market")]]
reply_markup = InlineKeyboardMarkup(keyboard)

await query.edit_message_text(market_text, parse_mode="Markdown", reply_markup=reply_markup)
```

async def find_signal(query, context):
can_trade, risk_msg = check_risk_limits()

```
if not can_trade:
    await query.edit_message_text(risk_msg)
    return

data = get_market_data()

prices_summary = ""
for symbol, info in data["prices"].items():
    name = symbol.replace("USDT", "")
    prices_summary += f"{name}: ${info['price']:,.2f} (изм: {info['change']:+.1f}%, объём: ${info['volume']:,.0f})\n"

prompt = f"""Проанализируй рынок по ТРЁХМОЗГОВОЙ СИСТЕМЕ:
```

МОЗГ 1 — ВАЙКОФФ:
Данные монет:
{prices_summary}

МОЗГ 2 — МАКРО КОНТЕКСТ:

- S&P 500: {data[‘sp500’][‘price’]} (изм: {data[‘sp500’][‘change’]}%)
- Страх & Жадность: {data[‘fear_greed’][‘value’]} ({data[‘fear_greed’][‘class’]})
- BTC Доминация: {data[‘btc_dominance’]}%

МОЗГ 3 — ЛИКВИДАЦИОННЫЕ ЗОНЫ:
Проанализируй где могут быть скопления стопов.

ПРАВИЛА HASH HEDGE:

- Аккаунт: $150,000
- Макс дневная просадка: $7,500 (5%)
- Используй соотношение риск/прибыль минимум 1:3
- Плечо максимум 1:5

Если все три мозга согласны — дай конкретный сигнал с точкой входа, стопом и целью.
Если сигнала нет — скажи честно “Сигналов нет, ждём”.
Будь максимально конкретным.”””

```
analysis = analyze_with_groq(prompt)

keyboard = [[InlineKeyboardButton("📸 Отправить график", callback_data="send_chart"),
             InlineKeyboardButton("🔄 Проверить снова", callback_data="signal")],
            [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]]
reply_markup = InlineKeyboardMarkup(keyboard)

await query.edit_message_text(
    f"🧠 *ТРЁХМОЗГОВОЙ АНАЛИЗ*\n\n{analysis}",
    parse_mode="Markdown",
    reply_markup=reply_markup
)
```

async def show_limits(query, context):
can_trade, msg = check_risk_limits()

```
daily_pct = (user_data["daily_loss"] / MAX_DAILY_LOSS) * 100
total_pct = (user_data["total_loss"] / MAX_TOTAL_LOSS) * 100

stage = user_data["stage"]
if stage == 1:
    target = "$12,000 (8%)"
    max_loss = "$15,000 (10%)"
else:
    target = "$9,000 (6%)"
    max_loss = "$12,000 (8%)"

text = f"""💼 *ЛИМИТЫ HASH HEDGE — Stage {stage}*
```

🎯 Цель прибыли: {target}
🛡 Макс общая просадка: {max_loss}
⚡️ Макс дневная просадка: $7,500 (5%)

📊 *Текущее состояние:*
Дневная просадка: ${user_data[‘daily_loss’]:,.0f} / $7,500 ({daily_pct:.0f}%)
Общая просадка: ${user_data[‘total_loss’]:,.0f} / {max_loss} ({total_pct:.0f}%)

{msg}”””

```
keyboard = [
    [InlineKeyboardButton("➕ Добавить убыток", callback_data="add_loss")],
    [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
]
reply_markup = InlineKeyboardMarkup(keyboard)

await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
```

async def mood_check(query, context):
keyboard = [
[InlineKeyboardButton(“💪 Отлично, готов торговать”, callback_data=“mood_good”)],
[InlineKeyboardButton(“😐 Нормально”, callback_data=“mood_ok”)],
[InlineKeyboardButton(“😔 Устал / плохое настроение”, callback_data=“mood_bad”)]
]
reply_markup = InlineKeyboardMarkup(keyboard)

```
await query.edit_message_text(
    "🧠 *ПСИХОЛОГИЧЕСКИЙ ЧЕК*\n\n"
    "80% потерь на пропах — это эмоции.\n"
    "Как ты себя чувствуешь сегодня?",
    parse_mode="Markdown",
    reply_markup=reply_markup
)
```

async def show_journal(query, context):
if not user_data[“trades”]:
text = “📈 *ЖУРНАЛ СДЕЛОК*\n\nПока нет записей.\nОтправь /trade чтобы записать сделку.”
else:
trades_text = “”
total_pnl = 0
for i, trade in enumerate(user_data[“trades”][-5:], 1):
emoji = “✅” if trade[“pnl”] > 0 else “❌”
trades_text += f”{emoji} {trade[‘symbol’]}: ${trade[‘pnl’]:+,.0f}\n”
total_pnl += trade[“pnl”]

```
    text = f"📈 *ЖУРНАЛ СДЕЛОК (последние 5)*\n\n{trades_text}\n💰 Итого P&L: ${total_pnl:+,.0f}"

keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
reply_markup = InlineKeyboardMarkup(keyboard)

await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
```

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Анализ скриншота графика”””
await update.message.reply_text(“⏳ Анализирую график по методу Вайкоффа…”)

```
can_trade, risk_msg = check_risk_limits()
if not can_trade:
    await update.message.reply_text(risk_msg)
    return

data = get_market_data()

prompt = f"""Пользователь прислал скриншот графика для анализа по методу Вайкоффа.
```

Текущие данные рынка:

- S&P 500 изменение: {data[‘sp500’][‘change’]}%
- Страх & Жадность: {data[‘fear_greed’][‘value’]} ({data[‘fear_greed’][‘class’]})
- BTC доминация: {data[‘btc_dominance’]}%

Проанализируй как опытный Вайкофф-трейдер:

1. Определи фазу рынка (Accumulation/Distribution/Markup/Markdown)
1. Найди ключевые уровни поддержки и сопротивления
1. Определи есть ли паттерн Spring или Upthrust
1. Дай конкретную рекомендацию: входить или нет
1. Если входить — укажи точку входа, стоп и цель с соотношением 1:3+

Учитывай правила Hash Hedge: макс дневная просадка $7,500, плечо 1:5.”””

```
analysis = analyze_with_groq(prompt)

await update.message.reply_text(
    f"📊 *АНАЛИЗ ГРАФИКА — ВАЙКОФФ*\n\n{analysis}",
    parse_mode="Markdown"
)
```

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Обработка текстовых сообщений”””
text = update.message.text

```
data = get_market_data()
can_trade, risk_msg = check_risk_limits()

prompt = f"""Пользователь написал: "{text}"
```

Контекст рынка:

- S&P 500: {data[‘sp500’][‘price’]} (изм: {data[‘sp500’][‘change’]}%)
- Страх & Жадность: {data[‘fear_greed’][‘value’]} ({data[‘fear_greed’][‘class’]})
- BTC доминация: {data[‘btc_dominance’]}%
- Статус лимитов: {risk_msg}

Ответь как профессиональный торговый ассистент Джарвис.
Если вопрос о конкретной монете — дай анализ по Вайкоффу.
Если вопрос о стратегии — объясни чётко и по делу.
Максимум 300 слов.”””

```
response = analyze_with_groq(prompt)
await update.message.reply_text(response)
```

async def morning_briefing(context: ContextTypes.DEFAULT_TYPE):
“”“Утренний брифинг”””
chat_id = context.job.chat_id

```
# Сброс дневной просадки
user_data["daily_loss"] = 0

data = get_market_data()

prompt = f"""Сделай утренний торговый брифинг для трейдера.
```

Данные рынка:

- S&P 500: {data[‘sp500’][‘price’]} (изм: {data[‘sp500’][‘change’]}%)
- Страх & Жадность: {data[‘fear_greed’][‘value’]} ({data[‘fear_greed’][‘class’]})
- BTC доминация: {data[‘btc_dominance’]}%

Топ монеты:
{chr(10).join([f”{s.replace(‘USDT’,’’)}: ${i[‘price’]:,.2f} ({i[‘change’]:+.1f}%)” for s,i in data[‘prices’].items()])}

Включи:

1. Общее настроение рынка
1. На что обратить внимание сегодня
1. Какие монеты интересны
1. Предупреждения если есть риски
1. Мотивационное напутствие

Формат: чётко, структурированно, с эмодзи.”””

```
briefing = analyze_with_groq(prompt)

keyboard = [[InlineKeyboardButton("😊 Психо-чек", callback_data="mood"),
             InlineKeyboardButton("📊 Анализ", callback_data="market")]]
reply_markup = InlineKeyboardMarkup(keyboard)

await context.bot.send_message(
    chat_id=chat_id,
    text=f"☀️ *УТРЕННИЙ БРИФИНГ — {datetime.now().strftime('%d.%m.%Y')}*\n\n{briefing}",
    parse_mode="Markdown",
    reply_markup=reply_markup
)
```

async def monitor_markets(context: ContextTypes.DEFAULT_TYPE):
“”“Мониторинг рынка каждые 30 минут”””
chat_id = context.job.chat_id

```
can_trade, risk_msg = check_risk_limits()
if not can_trade:
    return

data = get_market_data()

prompt = f"""Быстрый скан рынка на сигналы Вайкоффа.
```

Данные:
S&P 500 изменение: {data[‘sp500’][‘change’]}%
Страх & Жадность: {data[‘fear_greed’][‘value’]}
BTC доминация: {data[‘btc_dominance’]}%

Монеты:
{chr(10).join([f”{s.replace(‘USDT’,’’)}: ${i[‘price’]:,.2f} (изм: {i[‘change’]:+.1f}%, объём: ${i[‘volume’]:,.0f})” for s,i in data[‘prices’].items()])}

Есть ли СИЛЬНЫЙ сигнал? Критерии:

- Все три мозга согласны (Вайкофф + Макро + Ликвидации)
- Чёткий уровень поддержки/сопротивления
- Риск/прибыль минимум 1:3
- S&P 500 не против направления

Если ЕСТЬ сигнал — опиши его полностью с входом, стопом, целью.
Если НЕТ — ответь только: “NO_SIGNAL”
Не отправляй слабые сигналы.”””

```
analysis = analyze_with_groq(prompt)

if "NO_SIGNAL" not in analysis and len(analysis) > 50:
    keyboard = [[InlineKeyboardButton("📸 Отправить график для подтверждения", callback_data="send_chart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🚨 *ПОТЕНЦИАЛЬНЫЙ СИГНАЛ*\n\n{analysis}\n\n📸 Отправь скриншот графика для финального подтверждения!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
```

async def post_init(application):
“”“Запуск фоновых задач”””
# Утренний брифинг в 8:00
application.job_queue.run_daily(
morning_briefing,
time=datetime.strptime(“08:00”, “%H:%M”).time(),
chat_id=None  # Будет установлен при первом /start
)

# ============ ЗАПУСК ============

def main():
app = Application.builder().token(TELEGRAM_TOKEN).build()

```
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

logger.info("🤖 Джарвис запущен!")
app.run_polling(drop_pending_updates=True)
```

if **name** == “**main**”:
main()
