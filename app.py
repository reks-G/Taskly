from flask import Flask, render_template, request, redirect, url_for
from database import get_session, User, Task, PriorityEnum, StatusEnum, init_db, get_moscow_time
from datetime import datetime, timedelta
from functools import lru_cache
import threading
import json
import hmac
import hashlib
from urllib.parse import parse_qs

BOT_TOKEN = '8534316351:AAE-aCnUKL0jBNDlDV1jRaUjH_45Nhocggc'
WEBAPP_URL = 'https://taskcontrol-qu0a.onrender.com'

PRIORITY_LEVELS = {
    'low': '🟢',
    'medium': '🟡',
    'high': '🔴'
}

STATUS_TYPES = {
    'pending': 'В ожидании',
    'in_progress': 'В работе',
    'completed': 'Завершено',
    'overdue': 'Просрочено'
}

app = Flask(__name__)

def get_telegram_user():
    telegram_id = request.args.get('telegram_id')
    if telegram_id:
        try:
            return int(telegram_id)
        except:
            pass
    
    init_data = request.headers.get('X-Telegram-Init-Data')
    if init_data:
        try:
            parsed = parse_qs(init_data)
            if 'user' in parsed:
                user_data = json.loads(parsed['user'][0])
                return user_data.get('id')
        except:
            pass
    
    return 123456

def get_or_create_user(telegram_id):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    
    if not user:
        user = User(telegram_id=telegram_id, username='user', first_name='User')
        session.add(user)
        session.commit()
    
    user_id = user.id
    session.close()
    return user_id

@app.route('/')
def index():
    telegram_id = get_telegram_user()
    filter_type = request.args.get('filter', 'all')
    view_mode = request.args.get('view', 'list')
    
    user_id = get_or_create_user(telegram_id)
    
    session = get_session()
    query = session.query(Task).filter_by(user_id=user_id)
    
    now = get_moscow_time()
    if filter_type == 'today':
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        query = query.filter(Task.due_at >= today_start, Task.due_at < today_end)
    elif filter_type == 'week':
        week_end = now + timedelta(days=7)
        query = query.filter(Task.due_at >= now, Task.due_at < week_end)
    elif filter_type == 'overdue':
        query = query.filter(
            Task.due_at < now,
            Task.due_at.isnot(None),
            Task.status.in_([StatusEnum.pending, StatusEnum.in_progress])
        )
    elif filter_type == 'active':
        query = query.filter(Task.status.in_([StatusEnum.pending, StatusEnum.in_progress]))
    
    tasks = query.order_by(Task.due_at).all()
    session.close()
    
    return render_template('index.html', 
                         tasks=tasks, 
                         filter_type=filter_type,
                         view_mode=view_mode,
                         telegram_id=telegram_id,
                         priority_levels=PRIORITY_LEVELS,
                         status_types=STATUS_TYPES)

@app.route('/create', methods=['GET', 'POST'])
def create_task():
    telegram_id = get_telegram_user()
    errors = []
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        due_at_str = request.form.get('due_at', '')
        
        if not title:
            errors.append('Task title is required')
        elif len(title) > 500:
            errors.append('Task title must be less than 500 characters')
        
        if priority not in ['low', 'medium', 'high']:
            errors.append('Invalid priority value')
        
        due_at = None
        if due_at_str:
            try:
                due_at = datetime.fromisoformat(due_at_str)
            except ValueError:
                errors.append('Invalid date format')
        
        if not errors:
            user_id = get_or_create_user(telegram_id)
            session = get_session()
            
            task = Task(
                user_id=user_id,
                title=title,
                description=description if description else None,
                due_at=due_at,
                priority=PriorityEnum[priority]
            )
            
            session.add(task)
            
            try:
                session.commit()
            except Exception as e:
                session.rollback()
            finally:
                session.close()
            
            return redirect(url_for('index', telegram_id=telegram_id))
    
    default_datetime = get_moscow_time().strftime('%Y-%m-%dT%H:%M')
    return render_template('create.html', telegram_id=telegram_id, errors=errors, default_datetime=default_datetime)

@app.route('/task/<int:task_id>')
def task_detail(task_id):
    telegram_id = get_telegram_user()
    
    session = get_session()
    task = session.query(Task).filter_by(id=task_id).first()
    session.close()
    
    if not task:
        return redirect(url_for('index', telegram_id=telegram_id))
    
    return render_template('detail.html', 
                         task=task, 
                         telegram_id=telegram_id,
                         priority_levels=PRIORITY_LEVELS,
                         status_types=STATUS_TYPES)

@app.route('/task/<int:task_id>/complete')
def complete_task(task_id):
    telegram_id = get_telegram_user()
    
    session = get_session()
    task = session.query(Task).filter_by(id=task_id).first()
    
    if task:
        task.status = StatusEnum.completed
        session.commit()
    
    session.close()
    return redirect(url_for('index', telegram_id=telegram_id))

@app.route('/task/<int:task_id>/delete')
def delete_task(task_id):
    telegram_id = get_telegram_user()
    
    session = get_session()
    task = session.query(Task).filter_by(id=task_id).first()
    
    if task:
        session.delete(task)
        session.commit()
    
    session.close()
    return redirect(url_for('index', telegram_id=telegram_id))

@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
def edit_task(task_id):
    telegram_id = get_telegram_user()
    
    session = get_session()
    task = session.query(Task).filter_by(id=task_id).first()
    
    if not task:
        session.close()
        return redirect(url_for('index', telegram_id=telegram_id))
    
    errors = []
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        due_at_str = request.form.get('due_at', '')
        
        if not title:
            errors.append('Название задачи обязательно')
        elif len(title) > 500:
            errors.append('Название задачи должно быть меньше 500 символов')
        
        if priority not in ['low', 'medium', 'high']:
            errors.append('Неверное значение приоритета')
        
        due_at = None
        if due_at_str:
            try:
                due_at = datetime.fromisoformat(due_at_str)
            except ValueError:
                errors.append('Неверный формат даты')
        
        if not errors:
            task.title = title
            task.description = description if description else None
            task.due_at = due_at
            task.priority = PriorityEnum[priority]
            
            session.commit()
            session.close()
            
            return redirect(url_for('task_detail', task_id=task_id, telegram_id=telegram_id))
    
    session.close()
    return render_template('edit.html', 
                         task=task, 
                         telegram_id=telegram_id, 
                         errors=errors)

@app.route('/calendar')
def calendar():
    telegram_id = get_telegram_user()
    user_id = get_or_create_user(telegram_id)
    
    session = get_session()
    tasks = session.query(Task).filter_by(user_id=user_id).filter(Task.due_at.isnot(None)).order_by(Task.due_at).all()
    session.close()
    
    return render_template('calendar.html', 
                         tasks=tasks, 
                         telegram_id=telegram_id,
                         priority_levels=PRIORITY_LEVELS,
                         status_types=STATUS_TYPES)

@app.route('/notifications')
def notifications():
    telegram_id = get_telegram_user()
    user_id = get_or_create_user(telegram_id)
    
    session = get_session()
    now = get_moscow_time()
    notification_window = now + timedelta(hours=24)
    
    tasks = session.query(Task).filter_by(user_id=user_id).filter(
        Task.due_at.isnot(None),
        Task.due_at >= now,
        Task.due_at <= notification_window,
        Task.status.in_([StatusEnum.pending, StatusEnum.in_progress])
    ).order_by(Task.due_at).all()
    
    notifications_list = []
    for task in tasks:
        time_left = task.due_at - now
        hours_left = int(time_left.total_seconds() / 3600)
        minutes_left = int((time_left.total_seconds() % 3600) / 60)
        
        if hours_left > 0:
            time_text = f"через {hours_left} ч {minutes_left} мин"
        else:
            time_text = f"через {minutes_left} мин"
        
        notifications_list.append({
            'task': task,
            'time_left': time_text,
            'hours_left': hours_left,
            'is_urgent': hours_left < 2
        })
    
    session.close()
    
    return render_template('notifications.html', 
                         notifications=notifications_list,
                         telegram_id=telegram_id,
                         priority_levels=PRIORITY_LEVELS,
                         status_types=STATUS_TYPES)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
