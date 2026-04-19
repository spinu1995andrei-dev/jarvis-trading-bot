import os
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes,
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
ACCOUNT_SIZE = 150000
MAX_DAILY_LOSS = 7500
MAX_TOTAL_LOSS = 15000
TOP_10 = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAX
user_data = {'daily_loss': 0, 'total_loss': 0, 'trades': [], 'stage': 1, 'mood': None, 'chat_
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def get_crypto_price(symbol):
try:
r = requests.get('https://api.binance.com/api/v3/ticker/24hr?symbol=' + symbol, timeo
d = r.json()
return {'price': float(d['lastPrice']), 'change': float(d['priceChangePercent']), 'vo
except:
return None
def get_fear_greed():
try:
r = requests.get('https://api.alternative.me/fng/', timeout=5)
d = r.json()
return d['data'][0]['value'], d['data'][0]['value_classification']
except:
return '50', 'Neutral'
def get_sp500():
try:
url = 'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=2d
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
d = r.json()
closes = d['chart']['result'][0]['indicators']['quote'][0]['close']
change = ((closes[-1] - closes[-2]) / closes[-2]) * 100
return closes[-1], change
except:
return None, None
def get_market_data():
prices = {}
for s in TOP_10:
d = get_crypto_price(s)
if d:
prices[s] = d
fg_val, fg_cls = get_fear_greed()
sp_price, sp_change = get_sp500()
return {'prices': prices, 'fear_greed': {'value': fg_val, 'class': fg_cls}, 'sp500': {'pr
def analyze_with_groq(prompt):
headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
system = 'Ты Джарвис - профессиональный торговый ИИ с 20-летним опытом. Метод Вайкоффа +
data = {'model': 'llama-3.3-70b-versatile', 'messages': [{'role': 'system', 'content': sy
try:
r = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
return r.json()['choices'][0]['message']['content']
except Exception as e:
return 'Ошибка: ' + str(e)
def check_limits():
if user_data['daily_loss'] >= MAX_DAILY_LOSS:
return False, 'СТОП! Дневной лимит $7500 достигнут!'
if user_data['total_loss'] >= MAX_TOTAL_LOSS:
return False, 'СТОП! Общий лимит $15000 достигнут!'
return True, 'Лимиты OK. Дневная просадка: $' + str(user_data['daily_loss']) + ' из $7500
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_data['chat_id'] = update.effective_chat.id
kb = [[InlineKeyboardButton('Анализ рынка', callback_data='market')],
[InlineKeyboardButton('Найти сигнал', callback_data='signal')],
[InlineKeyboardButton('Мои лимиты', callback_data='limits')],
[InlineKeyboardButton('Психо-чек', callback_data='mood')]]
await update.message.reply_text('ДЖАРВИС TRADING\n\nМетод Вайкоффа + Ликвидации + Макро\n
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
q = update.callback_query
await q.answer()
if q.data == 'market':
await q.edit_message_text('Собираю данные...')
data = get_market_data()
txt = 'РЫНОК ' + datetime.now().strftime('%H:%M') + '\n\n'
for sym, info in data['prices'].items():
name = sym.replace('USDT', '')
em = '+' if info['change'] > 0 else ''
txt += name + ': $' + str(round(info['price'], 2)) + ' (' + em + str(round(info['
fg = data['fear_greed']
sp = data['sp500']
txt += '\nСтрах/Жадность: ' + str(fg['value']) + ' - ' + fg['class']
if sp['price']:
txt += '\nS&P 500: $' + str(round(sp['price'])) + ' (' + str(round(sp['change'],
kb = [[InlineKeyboardButton('Найти сигнал', callback_data='signal'), InlineKeyboardBu
await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
elif q.data == 'signal':
can, risk_msg = check_limits()
if not can:
await q.edit_message_text(risk_msg)
return
await q.edit_message_text('Анализирую по трехмозговой системе...')
data = get_market_data()
prices_txt = ''
for sym, info in data['prices'].items():
prices_txt += sym.replace('USDT', '') + ': $' + str(round(info['price'], 2)) + '
prompt = 'ТРЕХМОЗГОВОЙ АНАЛИЗ:\n\nМОЗГ1-ВАЙКОФФ:\n' + prices_txt + '\nМОЗГ2-МАКРО:\nS
result = analyze_with_groq(prompt)
kb = [[InlineKeyboardButton('Обновить', callback_data='signal'), InlineKeyboardButton
await q.edit_message_text('СИГНАЛ\n\n' + result, reply_markup=InlineKeyboardMarkup(kb
elif q.data == 'limits':
can, msg = check_limits()
txt = 'ЛИМИТЫ Hash Hedge Stage ' + str(user_data['stage']) + '\n\nЦель: $12,000 (8%)\
await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButt
elif q.data == 'mood':
kb = [[InlineKeyboardButton('Готов торговать', callback_data='mood_good')],
[InlineKeyboardButton('Нормально', callback_data='mood_ok')],
[InlineKeyboardButton('Устал/плохое настроение', callback_data='mood_bad')]]
await q.edit_message_text('ПСИХО-ЧЕК\n\n80% потерь - это эмоции.\nКак себя чувствуешь
elif q.data == 'mood_bad':
await q.edit_message_text('Сегодня лучше не торговать.\nОтдохни - рынок никуда elif q.data in ['mood_good', 'mood_ok']:
await q.edit_message_text('Отлично! Помни:\n- Только уверенные сетапы\n- R:R минимум
elif q.data == 'menu':
kb = [[InlineKeyboardButton('Анализ рынка', callback_data='market')],
[InlineKeyboardButton('Найти сигнал', callback_data='signal')],
[InlineKeyboardButton('Мои лимиты', callback_data='limits')],
[InlineKeyboardButton('Психо-чек', callback_data='mood')]]
await q.edit_message_text('ДЖАРВИС TRADING\n\nВыбери действие:', reply_markup=InlineK
не ден
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text('Анализирую график...')
data = get_market_data()
prompt = 'Пользователь прислал скриншот графика. Проанализируй по Вайкоффу:\n1. Фаза рынк
result = analyze_with_groq(prompt)
await update.message.reply_text('АНАЛИЗ ВАЙКОФФ\n\n' + result)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_data['chat_id'] = update.effective_chat.id
data = get_market_data()
can, risk = check_limits()
prompt = 'Вопрос трейдера: ' + update.message.text + '\n\nРынок: S&P500 ' + str(data['sp5
result = analyze_with_groq(prompt)
await update.message.reply_text(result)
async def monitor(context: ContextTypes.DEFAULT_TYPE):
if not user_data.get('chat_id'):
return
can, _ = check_limits()
if not can:
return
data = get_market_data()
prices_txt = ''
for sym, info in data['prices'].items():
prices_txt += sym.replace('USDT', '') + ': $' + str(round(info['price'], 2)) + ' (' +
prompt = 'Скан рынка. Есть сильный сигнал Вайкофф?\n' + prices_txt + '\nS&P500: ' + str(d
result = analyze_with_groq(prompt)
if 'NO_SIGNAL' not in result and len(result) > 50:
await context.bot.send_message(chat_id=user_data['chat_id'], text='СИГНАЛ НАЙДЕН\n\n'
def main():
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.job_queue.run_repeating(monitor, interval=1800, first=60)
logger.info('Джарвис запущен!')
app.run_polling(drop_pending_updates=True)
if __name__ == '__main__':
