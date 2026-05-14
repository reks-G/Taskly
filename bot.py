from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import init_db, get_session, Task, StatusEnum
import threading
import time
from datetime import datetime, timedelta

BOT_TOKEN = '8534316351:AAE-aCnUKL0jBNDlDV1jRaUjH_45Nhocggc'
WEBAPP_URL = 'https://taskcontrol-qu0a.onrender.com'

bot = TeleBot(BOT_TOKEN, parse_mode='HTML')

def webapp_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('🚀 Открыть TaskControl', web_app=WebAppInfo(url=WEBAPP_URL)))
    return markup

def send_notification(telegram_id, message_text):
    """Отправить уведомление пользователю"""
    try:
        bot.send_message(telegram_id, message_text, reply_markup=webapp_button())
        return True
    except Exception as e:
        print(f'Ошибка отправки уведомления: {e}')
        return False

def notify_task_created(telegram_id, task_title):
    """Уведомление о создании задачи"""
    message = f'✅ <b>Задача создана</b>\n\n📝 {task_title}'
    return send_notification(telegram_id, message)

def notify_task_completed(telegram_id, task_title):
    """Уведомление о завершении задачи"""
    message = f'🎉 <b>Задача завершена!</b>\n\n✓ {task_title}'
    return send_notification(telegram_id, message)

def notify_task_deleted(telegram_id, task_title):
    """Уведомление об удалении задачи"""
    message = f'🗑 <b>Задача удалена</b>\n\n{task_title}'
    return send_notification(telegram_id, message)

def notify_task_updated(telegram_id, task_title):
    """Уведомление об обновлении задачи"""
    message = f'📝 <b>Задача обновлена</b>\n\n{task_title}'
    return send_notification(telegram_id, message)

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(
        message.chat.id,
        f'Привет, {message.from_user.first_name}!\n\n'
        'Открой TaskControl Mini App для управления задачами:',
        reply_markup=webapp_button()
    )

# ============================================
# ПЛАНИРОВЩИК УВЕДОМЛЕНИЙ
# ============================================

def check_upcoming_tasks():
    """Проверить задачи с приближающимся дедлайном"""
    while True:
        try:
            session = get_session()
            now = datetime.now()
            
            # Найти задачи с дедлайном через 25-35 минут (окно 10 минут)
            start_window = now + timedelta(minutes=25)
            end_window = now + timedelta(minutes=35)
            
            tasks = session.query(Task).filter(
                Task.due_at >= start_window,
                Task.due_at <= end_window,
                Task.status.in_([StatusEnum.pending, StatusEnum.in_progress]),
                Task.notified == False
            ).all()
            
            for task in tasks:
                try:
                    telegram_id = task.user.telegram_id
                    send_deadline_reminder(telegram_id, task)
                    
                    task.notified = True
                    session.commit()
                    
                    print(f'✅ Отправлено напоминание для задачи: {task.title}')
                    
                except Exception as e:
                    print(f'❌ Ошибка отправки уведомления для задачи {task.id}: {e}')
            
            session.close()
            
        except Exception as e:
            print(f'❌ Ошибка проверки задач: {e}')
        
        # Проверять каждые 5 минут
        time.sleep(300)

def send_deadline_reminder(telegram_id, task):
    """Отправить красивое напоминание о дедлайне"""
    # Рассчитать оставшееся время
    time_left = task.due_at - datetime.now()
    minutes_left = int(time_left.total_seconds() / 60)
    
    # Определить эмодзи приоритета
    priority_emoji = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🔴'
    }
    
    # Красивое сообщение
    message = f"""
⏰ <b>Напоминание о задаче</b>

{priority_emoji.get(task.priority.value, '⚪')} <b>{task.title}</b>

⏱ Осталось времени: <b>{minutes_left} минут</b>
📅 Дедлайн: {task.due_at.strftime('%d.%m.%Y в %H:%M')}

{'📝 ' + task.description[:100] + '...' if task.description and len(task.description) > 100 else '📝 ' + task.description if task.description else ''}

<i>Не забудьте выполнить задачу вовремя! 💪</i>
"""
    
    # Кнопка для открытия задачи
    markup = InlineKeyboardMarkup()
    task_url = f"{WEBAPP_URL}/task/{task.id}?telegram_id={telegram_id}"
    
    markup.add(
        InlineKeyboardButton(
            '👁 Открыть задачу',
            web_app=WebAppInfo(url=task_url)
        )
    )
    markup.add(
        InlineKeyboardButton(
            '✅ Отметить выполненной',
            callback_data=f'complete_{task.id}'
        )
    )
    
    try:
        bot.send_message(
            telegram_id,
            message,
            parse_mode='HTML',
            reply_markup=markup
        )
    except Exception as e:
        print(f'Ошибка отправки сообщения: {e}')

def start_scheduler():
    """Запустить планировщик в фоновом потоке"""
    scheduler_thread = threading.Thread(target=check_upcoming_tasks, daemon=True)
    scheduler_thread.start()
    print('📅 Планировщик уведомлений запущен')

if __name__ == '__main__':
    init_db()
    start_scheduler()
    print('Bot started')
    bot.infinity_polling()
