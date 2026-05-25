from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import init_db, get_session, Task, StatusEnum, User, get_moscow_time
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

@bot.message_handler(commands=['start'])
def start_handler(message):
    telegram_id = message.from_user.id
    username = message.from_user.username or 'user'
    first_name = message.from_user.first_name or 'User'
    
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        session.add(user)
        session.commit()
        print(f'✅ Новый пользователь зарегистрирован: {first_name} (ID: {telegram_id})')
    
    session.close()
    
    bot.send_message(
        message.chat.id,
        f'Привет, {first_name}! 👋\n\n'
        '🎯 <b>TaskControl</b> - твой персональный менеджер задач\n\n'
        '✨ Создавай задачи\n'
        '⏰ Получай напоминания\n'
        '📊 Отслеживай прогресс\n\n'
        'Открой приложение чтобы начать:',
        reply_markup=webapp_button(),
        parse_mode='HTML'
    )

@bot.message_handler(commands=['tasks'])
def tasks_handler(message):
    telegram_id = message.from_user.id
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    
    if not user:
        bot.send_message(
            message.chat.id,
            'Сначала запустите бота командой /start',
            reply_markup=webapp_button()
        )
        session.close()
        return
    
    tasks = session.query(Task).filter_by(user_id=user.id).filter(
        Task.status.in_([StatusEnum.pending, StatusEnum.in_progress])
    ).order_by(Task.due_at).limit(5).all()
    
    if not tasks:
        bot.send_message(
            message.chat.id,
            '📋 У вас пока нет активных задач\n\nОткройте приложение чтобы создать первую задачу:',
            reply_markup=webapp_button()
        )
    else:
        priority_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}
        message_text = '📋 <b>Ваши активные задачи:</b>\n\n'
        
        for i, task in enumerate(tasks, 1):
            emoji = priority_emoji.get(task.priority.value, '⚪')
            due_text = task.due_at.strftime('%d.%m %H:%M') if task.due_at else 'Без срока'
            message_text += f'{i}. {emoji} <b>{task.title}</b>\n   📅 {due_text}\n\n'
        
        if len(tasks) == 5:
            message_text += '\n<i>Показаны первые 5 задач</i>'
        
        bot.send_message(
            message.chat.id,
            message_text,
            reply_markup=webapp_button(),
            parse_mode='HTML'
        )
    
    session.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('complete_'))
def handle_complete_task(call):
    try:
        task_id = int(call.data.split('_')[1])
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).first()
        
        if task:
            task.status = StatusEnum.completed
            task_title = task.title
            session.commit()
            
            bot.answer_callback_query(call.id, '✅ Задача отмечена как выполненная!')
            bot.edit_message_text(
                f'✅ <b>Задача завершена!</b>\n\n<s>{task_title}</s>',
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML'
            )
        else:
            bot.answer_callback_query(call.id, '❌ Задача не найдена')
        
        session.close()
    except Exception as e:
        print(f'Ошибка обработки callback: {e}')
        bot.answer_callback_query(call.id, '❌ Произошла ошибка')

def check_upcoming_tasks():
    while True:
        try:
            session = get_session()
            now = get_moscow_time()
            
            start_window = now + timedelta(minutes=10)
            end_window = now + timedelta(minutes=20)
            
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
            
            cleanup_old_tasks(session, now)
            
            session.close()
            
        except Exception as e:
            print(f'❌ Ошибка проверки задач: {e}')
        
        time.sleep(300)

def cleanup_old_tasks(session, now):
    try:
        week_ago = now - timedelta(days=7)
        
        old_tasks = session.query(Task).filter(
            Task.due_at.isnot(None),
            Task.due_at < week_ago,
            Task.status.in_([StatusEnum.pending, StatusEnum.in_progress])
        ).all()
        
        if old_tasks:
            for task in old_tasks:
                session.delete(task)
            session.commit()
            print(f'🗑 Удалено {len(old_tasks)} просроченных задач старше недели')
    except Exception as e:
        print(f'❌ Ошибка очистки старых задач: {e}')

def send_deadline_reminder(telegram_id, task):
    time_left = task.due_at - get_moscow_time()
    minutes_left = int(time_left.total_seconds() / 60)
    
    priority_emoji = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🔴'
    }
    
    message = f"""
⏰ <b>Напоминание о задаче</b>

{priority_emoji.get(task.priority.value, '⚪')} <b>{task.title}</b>

⏱ Осталось времени: <b>{minutes_left} минут</b>
📅 Дедлайн: {task.due_at.strftime('%d.%m.%Y в %H:%M')}

{'📝 ' + task.description[:100] + '...' if task.description and len(task.description) > 100 else '📝 ' + task.description if task.description else ''}

<i>Не забудьте выполнить задачу вовремя! 💪</i>
"""
    
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
    scheduler_thread = threading.Thread(target=check_upcoming_tasks, daemon=True)
    scheduler_thread.start()
    print('📅 Планировщик уведомлений запущен')

if __name__ == '__main__':
    init_db()
    start_scheduler()
    print('Bot started')
    bot.infinity_polling()
