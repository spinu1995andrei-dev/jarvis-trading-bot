import os
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- НАСТРОЙКИ (Берутся из Railway Variables) ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Параметры проп-аккаунта
ACCOUNT_SIZE = 150000
MAX_DAILY_LOSS = 7500
MAX_TOTAL_LOSS = 15000
TOP_10 = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT']

# Хранилище данных (сбрасывается при перезагрузке)
user_data = {'daily_loss': 0, 'total_loss': 0, 'trades': [], 'stage': 1, 'mood': None, 'chat_id': None}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ПОЛУЧЕНИЕ ДАННЫХ ---
def get_crypto_price(symbol):
    try:
        r = requests.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}', timeout=5)
        d = r.json()
        return {'price': float(d['lastPrice']), 'change': float(d['priceChangePercent'])}
    except:
        return None

def get_fear_greed():
    try:
        r = requests.get('https://api.alternative.me/fng/', timeout=5)
        d = r.json()
        return d['data'][0]['value'], d['data'][0]['value_classification']
    except:
        return '50', 'Neutral'

def get_market_data():
    prices = {}
    for s in TOP_10:
        d = get_crypto_price(s)
        if d: prices[s] = d
    fg_val, fg_cls = get_fear_greed()
    return {'prices': prices, 'fear_greed': {'value': fg_val, 'class': fg_cls}}

# --- ИИ АНАЛИЗ (GROQ) ---
def analyze_with_groq(prompt):
    if not GROQ_API_KEY:
        return "Ошибка: Не задан GROQ_API_KEY в настройках Railway."
    headers = {'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'}
    system = 'Ты Джарвис — элитный ИИ-трейдер. Используй метод Вайкоффа. Давай конкретные точки входа/выхода.'
    data = {
        'model': 'llama-3.3-70b-versatile',
        'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]
    }
    try:
        r = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f'Ошибка связи с ИИ: {str(e)}'

# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['chat_id'] = update.effective_chat.id
    kb = [
        [InlineKeyboardButton('📊 Анализ рынка', callback_data='market')],
        [InlineKeyboardButton('🎯 Сигнал Вайкофф', callback_data='signal')],
        [InlineKeyboardButton('💰 Лимиты', callback_data='limits')],
        [InlineKeyboardButton('🧠 Психо-чек', callback_data='mood')]
    ]
    await update.message.reply_text('🤖 **ДЖАРВИС НА СВЯЗИ**\nСистема мониторинга проп-счета готова.', 
                                  reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data == 'market':
        data = get_market_data()
        txt = f"📊 **РЫНОК {datetime.now().strftime('%H:%M')}**\n\n"
        for sym, info in data['prices'].items():
            icon = '📈' if info['change'] > 0 else '📉'
            txt += f"`{sym.replace('USDT', '')}`: ${info['price']} ({info['change']}% {icon})\n"
        await q.edit_message_text(txt, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Меню', callback_data='menu')]]))

    elif q.data == 'signal':
        await q.edit_message_text('🔍 Джарвис сканирует рынок...')
        data = get_market_data()
        prompt = f"Цены: {str(data['prices'])}. Найди лучший сетап по Вайкоффу. Будь краток."
        result = analyze_with_groq(prompt)
        await q.edit_message_text(f"🎯 **СИГНАЛ:**\n\n{result}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Меню', callback_data='menu')]]))

    elif q.data == 'limits':
        txt = f"📈 **СТАТУС**\nДепозит: ${ACCOUNT_SIZE}\nДневной стоп: ${MAX_DAILY_LOSS}\nОбщий стоп: ${MAX_TOTAL_LOSS}"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Меню', callback_data='menu')]]))

    elif q.data == 'mood':
        kb = [[InlineKeyboardButton('🔥 Готов', callback_data='mood_ok')], [InlineKeyboardButton('❌ Устал', callback_data='mood_bad')]]
        await q.edit_message_text('Как твое состояние?', reply_markup=InlineKeyboardMarkup(kb))

    elif q.data in ['mood_ok', 'mood_bad', 'menu']:
        if q.data == 'mood_bad':
            await q.edit_message_text('⚠️ Отдыхай. Рынок подождет.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Меню', callback_data='menu')]]))
        else:
            kb = [[InlineKeyboardButton('📊 Анализ рынка', callback_data='market')], [InlineKeyboardButton('🎯 Сигнал Вайкофф', callback_data='signal')], [InlineKeyboardButton('💰 Лимиты', callback_data='limits')], [InlineKeyboardButton('🧠 Психо-чек', callback_data='mood')]]
            await q.edit_message_text('Выбери действие:', reply_markup=InlineKeyboardMarkup(kb))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = analyze_with_groq(update.message.text)
    await update.message.reply_text(res)

def main():
    if not TELEGRAM_TOKEN: return
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
