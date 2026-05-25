from database.session import init_db, get_session
from database.models import User, Task, PriorityEnum, StatusEnum
from datetime import datetime, timedelta

def get_moscow_time():
    return datetime.utcnow() + timedelta(hours=7)

__all__ = ['init_db', 'get_session', 'User', 'Task', 'PriorityEnum', 'StatusEnum', 'get_moscow_time']
