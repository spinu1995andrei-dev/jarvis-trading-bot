import os
import asyncio
import logging
from datetime import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TELEGRAM_TOKEN = os.environ.get(“TELEGRAM_TOKEN”)
GROQ_API_KEY = os.environ.get(“GROQ_API_KEY”)
GROQ_API_URL = “https://api.groq.com/openai/v1/chat/completions”

ACCOUNT_SIZE = 150000
MAX_DAILY_LOSS = 7500
MAX_TOTAL_LOSS = 15000

TOP_10 = [“BTCUSDT”, “ETHUSDT”, “BNBUSDT”, “SOLUSDT”, “XRPUSDT”,
“DOGEUSDT”, “ADAUSDT”, “AVAXUSDT”, “TONUSDT”, “LINKUSDT”]

user_data = {
“daily_loss”: 0,
“total_loss”: 0,
“trades”: [],
“stage”: 1,
“mood”: None,
“chat_id”: None
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

def get_crypto_price(symbol):
try:
url = “https://api.binance.com/api/v3/ticker/24hr?symbol=” + symbol
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
prices = {}
for symbol in TOP_10:
data = get_crypto_price(symbol)
if data:
prices[symbol] = data
fg_value, fg_class = get_fear_greed()
sp500_price, sp500_change = get_sp500()
btc_dom = get_btc_dominance()
return {
“prices”: prices,
“fear_greed”: {“value”: fg_value, “class”: fg_class},
“sp500”: {“price”: sp500_price, “change”: sp500_change},
“btc_dominance”: btc_dom
}

def analyze_with_groq(prompt):
headers = {
“Authorization”: “Bearer “ + GROQ_API_KEY,
“Content-Type”: “application/json”
}
system_prompt = “Ты Джарвис - профессиональный торговый ИИ-ассистент с 20-летним опытом. Специализируешься на методе Вайкоффа + ликвидационные зоны + макро анализ. Торгуешь только уверенные сделки с соотношением риск/прибыль минимум 1:3. Отвечаешь четко, по делу, без воды. Используешь эмодзи для наглядности. Всегда учитываешь лимиты проп-фирмы Hash Hedge.”
data = {
“model”: “llama-3.3-70b-versatile”,
“messages”: [
{“role”: “system”, “content”: system_prompt},
{“role”: “user”, “content”: prompt}
],
“max_tokens”: 1000,
“temperature”: 0.3
}
try:
r = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
result = r.json()
return result[“choices”][0][“message”][“content”]
except Exception as e:
return “Ошибка анализа: “ + str(e)

def check_risk_limits():
daily_used = (user_data[“daily_loss”] / MAX_DAILY_LOSS) * 100
total_used = (user_data[“total_loss”] / MAX_TOTAL_LOSS) * 100
if user_data[“daily_loss”] >= MAX_DAILY_LOSS:
return False, “СТОП! Дневной лимит просадки достигнут ($7,500). Торговля запрещена сегодня!”
if user_data[“total_loss”] >= MAX_TOTAL_LOSS:
return False, “СТОП! Общий лимит просадки достигнут. Срочно свяжитесь с Hash Hedge!”
if daily_used >= 70:
return True, “Осторожно! Использовано “ + str(round(daily_used)) + “% дневного лимита.”
return True, “Лимиты в норме. Дневная просадка: $” + str(user_data[“daily_loss”]) + “ из $7,500”

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_data[“chat_id”] = update.effective_chat.id
keyboard = [
[InlineKeyboardButton(“Анализ рынка”, callback_data=“market”)],
[InlineKeyboardButton(“Мои лимиты”, callback_data=“limits”)],
[InlineKeyboardButton(“Найти сигнал”, callback_data=“signal”)],
[InlineKeyboardButton(“Психо-чек”, callback_data=“mood”)],
[InlineKeyboardButton(“Журнал сделок”, callback_data=“journal”)]
]
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text(
“ДЖАРВИС TRADING online!\n\nТвой профессиональный торговый ассистент.\nМетод Вайкоффа + Ликвидации + Макро анализ\n\nАккаунт: Hash Hedge $150,000\nТоп-10 крипто монеты\n\nВыбери действие:”,
reply_markup=reply_markup
)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if query.data == “market”:
await query.edit_message_text(“Собираю данные рынка…”)
await market_analysis(query, context)
elif query.data == “limits”:
await show_limits(query, context)
elif query.data == “signal”:
await query.edit_message_text(“Ищу сигналы по трехмозговой системе…”)
await find_signal(query, context)
elif query.data == “mood”:
await mood_check(query, context)
elif query.data == “journal”:
await show_journal(query, context)
elif query.data.startswith(“mood_”):
mood = query.data.split(”_”)[1]
user_data[“mood”] = mood
if mood == “bad”:
await query.edit_message_text(“Понял тебя. Сегодня лучше не торговать.\n\nПлохое настроение = плохие решения = потеря денег.\nОтдохни, завтра рынок никуда не денется.”)
else:
await query.edit_message_text(“Отлично! Настрой боевой.\n\nПомни правила:\nТолько уверенные сетапы\nРиск/прибыль минимум 1:3\nСледи за лимитами\n\nУдачной торговли!”)

async def market_analysis(query, context):
data = get_market_data()
prices_text = “”
for symbol, info in data[“prices”].items():
name = symbol.replace(“USDT”, “”)
emoji = “+” if info[“change”] > 0 else “-”
prices_text += name + “: $” + str(round(info[“price”], 2)) + “ (” + str(round(info[“change”], 1)) + “%)\n”
fg = data[“fear_greed”]
sp = data[“sp500”]
btc_dom = data[“btc_dominance”]
sp_price = str(round(sp[“price”])) if sp[“price”] else “н/д”
sp_change = str(round(sp[“change”], 1)) + “%” if sp[“change”] else “н/д”
btc_str = str(round(btc_dom, 1)) + “%” if btc_dom else “н/д”
market_text = “АНАЛИЗ РЫНКА - “ + datetime.now().strftime(”%H:%M”) + “\n\nТоп-10 Крипто:\n” + prices_text + “\nСтрах и Жадность: “ + str(fg[“value”]) + “ - “ + fg[“class”] + “\nS&P 500: $” + sp_price + “ (” + sp_change + “)\nBTC Доминация: “ + btc_str
keyboard = [[InlineKeyboardButton(“Найти сигнал”, callback_data=“signal”),
InlineKeyboardButton(“Обновить”, callback_data=“market”)]]
reply_markup = InlineKeyboardMarkup(keyboard)
await query.edit_message_text(market_text, reply_markup=reply_markup)

async def find_signal(query, context):
can_trade, risk_msg = check_risk_limits()
if not can_trade:
await query.edit_message_text(risk_msg)
return
data = get_market_data()
prices_summary = “”
for symbol, info in data[“prices”].items():
name = symbol.replace(“USDT”, “”)
prices_summary += name + “: $” + str(round(info[“price”], 2)) + “ (изм: “ + str(round(info[“change”], 1)) + “%, объем: $” + str(round(info[“volume”])) + “)\n”
prompt = “Проанализируй рынок по ТРЕХМОЗГОВОЙ СИСТЕМЕ:\n\nМОЗГ 1 - ВАЙКОФФ:\nДанные монет:\n” + prices_summary + “\nМОЗГ 2 - МАКРО КОНТЕКСТ:\n- S&P 500: “ + str(data[“sp500”][“price”]) + “ (изм: “ + str(data[“sp500”][“change”]) + “%)\n- Страх и Жадность: “ + str(data[“fear_greed”][“value”]) + “ (” + data[“fear_greed”][“class”] + “)\n- BTC Доминация: “ + str(data[“btc_dominance”]) + “%\n\nМОЗГ 3 - ЛИКВИДАЦИОННЫЕ ЗОНЫ:\nПроанализируй где могут быть скопления стопов.\n\nПРАВИЛА HASH HEDGE:\n- Аккаунт: $150,000\n- Макс дневная просадка: $7,500 (5%)\n- Используй соотношение риск/прибыль минимум 1:3\n- Плечо максимум 1:5\n\nЕсли все три мозга согласны - дай конкретный сигнал с точкой входа, стопом и целью.\nЕсли сигнала нет - скажи честно ‘Сигналов нет, ждем’.”
analysis = analyze_with_groq(prompt)
keyboard = [[InlineKeyboardButton(“Обновить”, callback_data=“signal”),
InlineKeyboardButton(“Главное меню”, callback_data=“back_main”)]]
reply_markup = InlineKeyboardMarkup(keyboard)
await query.edit_message_text(“ТРЕХМОЗГОВОЙ АНАЛИЗ\n\n” + analysis, reply_markup=reply_markup)

async def show_limits(query, context):
can_trade, msg = check_risk_limits()
daily_pct = round((user_data[“daily_loss”] / MAX_DAILY_LOSS) * 100)
total_pct = round((user_data[“total_loss”] / MAX_TOTAL_LOSS) * 100)
text = “ЛИМИТЫ HASH HEDGE - Stage “ + str(user_data[“stage”]) + “\n\nЦель прибыли: $12,000 (8%)\nМакс общая просадка: $15,000 (10%)\nМакс дневная просадка: $7,500 (5%)\n\nТекущее состояние:\nДневная просадка: $” + str(user_data[“daily_loss”]) + “ / $7,500 (” + str(daily_pct) + “%)\nОбщая просадка: $” + str(user_data[“total_loss”]) + “ / $15,000 (” + str(total_pct) + “%)\n\n” + msg
keyboard = [[InlineKeyboardButton(“Назад”, callback_data=“back_main”)]]
reply_markup = InlineKeyboardMarkup(keyboard)
await query.edit_message_text(text, reply_markup=reply_markup)

async def mood_check(query, context):
keyboard = [
[InlineKeyboardButton(“Отлично, готов торговать”, callback_data=“mood_good”)],
[InlineKeyboardButton(“Нормально”, callback_data=“mood_ok”)],
[InlineKeyboardButton(“Устал / плохое настроение”, callback_data=“mood_bad”)]
]
reply_markup = InlineKeyboardMarkup(keyboard)
await query.edit_message_text(
“ПСИХОЛОГИЧЕСКИЙ ЧЕК\n\n80% потерь на пропах - это эмоции.\nКак ты себя чувствуешь сегодня?”,
reply_markup=reply_markup
)

async def show_journal(query, context):
if not user_data[“trades”]:
text = “ЖУРНАЛ СДЕЛОК\n\nПока нет записей.”
else:
trades_text = “”
total_pnl = 0
for trade in user_data[“trades”][-5:]:
emoji = “+” if trade[“pnl”] > 0 else “-”
trades_text += emoji + “ “ + trade[“symbol”] + “: $” + str(trade[“pnl”]) + “\n”
total_pnl += trade[“pnl”]
text = “ЖУРНАЛ СДЕЛОК (последние 5)\n\n” + trades_text + “\nИтого P&L: $” + str(total_pnl)
keyboard = [[InlineKeyboardButton(“Назад”, callback_data=“back_main”)]]
reply_markup = InlineKeyboardMarkup(keyboard)
await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(“Анализирую график по методу Вайкоффа…”)
can_trade, risk_msg = check_risk_limits()
if not can_trade:
await update.message.reply_text(risk_msg)
return
data = get_market_data()
prompt = “Пользователь прислал скриншот графика для анализа по методу Вайкоффа.\n\nТекущие данные рынка:\n- S&P 500 изменение: “ + str(data[“sp500”][“change”]) + “%\n- Страх и Жадность: “ + str(data[“fear_greed”][“value”]) + “ (” + data[“fear_greed”][“class”] + “)\n- BTC доминация: “ + str(data[“btc_dominance”]) + “%\n\nПроанализируй как опытный Вайкофф-трейдер:\n1. Определи фазу рынка\n2. Найди ключевые уровни\n3. Определи есть ли паттерн Spring или Upthrust\n4. Дай конкретную рекомендацию: входить или нет\n5. Если входить - укажи точку входа, стоп и цель с соотношением 1:3+”
analysis = analyze_with_groq(prompt)
await update.message.reply_text(“АНАЛИЗ ГРАФИКА - ВАЙКОФФ\n\n” + analysis)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_data[“chat_id”] = update.effective_chat.id
text = update.message.text
data = get_market_data()
can_trade, risk_msg = check_risk_limits()
prompt = “Пользователь написал: “ + text + “\n\nКонтекст рынка:\n- S&P 500: “ + str(data[“sp500”][“price”]) + “ (изм: “ + str(data[“sp500”][“change”]) + “%)\n- Страх и Жадность: “ + str(data[“fear_greed”][“value”]) + “ (” + data[“fear_greed”][“class”] + “)\n- BTC доминация: “ + str(data[“btc_dominance”]) + “%\n- Статус лимитов: “ + risk_msg + “\n\nОтветь как профессиональный торговый ассистент Джарвис. Максимум 300 слов.”
response = analyze_with_groq(prompt)
await update.message.reply_text(response)

async def monitor_markets(context: ContextTypes.DEFAULT_TYPE):
if not user_data.get(“chat_id”):
return
can_trade, risk_msg = check_risk_limits()
if not can_trade:
return
data = get_market_data()
prices_summary = “”
for symbol, info in data[“prices”].items():
name = symbol.replace(“USDT”, “”)
prices_summary += name + “: $” + str(round(info[“price”], 2)) + “ (изм: “ + str(round(info[“change”], 1)) + “%, объем: $” + str(round(info[“volume”])) + “)\n”
prompt = “Быстрый скан рынка на сигналы Вайкоффа.\n\nДанные:\nS&P 500 изменение: “ + str(data[“sp500”][“change”]) + “%\nСтрах и Жадность: “ + str(data[“fear_greed”][“value”]) + “\nBTC доминация: “ + str(data[“btc_dominance”]) + “%\n\nМонеты:\n” + prices_summary + “\nЕсть ли СИЛЬНЫЙ сигнал? Критерии:\n- Все три мозга согласны\n- Четкий уровень поддержки/сопротивления\n- Риск/прибыль минимум 1:3\n- S&P 500 не против направления\n\nЕсли ЕСТЬ сигнал - опиши его полностью.\nЕсли НЕТ - ответь только: NO_SIGNAL”
analysis = analyze_with_groq(prompt)
if “NO_SIGNAL” not in analysis and len(analysis) > 50:
await context.bot.send_message(
chat_id=user_data[“chat_id”],
text=“ПОТЕНЦИАЛЬНЫЙ СИГНАЛ\n\n” + analysis + “\n\nОтправь скриншот графика для финального подтверждения!”
)

def main():
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
job_queue = app.job_queue
job_queue.run_repeating(monitor_markets, interval=1800, first=60)
logger.info(“Джарвис запущен!”)
app.run_polling(drop_pending_updates=True)

if **name** == “**main**”:
main()
