import threading
from app import app
from bot import bot, start_scheduler
from database import init_db

def run_bot():
    print('Bot started and running...')
    bot.infinity_polling()

if __name__ == '__main__':
    print('Initializing database...')
    init_db()
    print('Starting scheduler...')
    start_scheduler()
    
    print('Starting bot thread...')
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print('Starting Flask app...')
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
