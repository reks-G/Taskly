import threading
from app import app
from bot import bot, start_scheduler
from database import init_db

def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    init_db()
    start_scheduler()
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
