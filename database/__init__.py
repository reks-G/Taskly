from database.session import init_db, get_session
from database.models import User, Task, PriorityEnum, StatusEnum
from datetime import datetime
import pytz

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

def get_moscow_time():
    return datetime.now(MOSCOW_TZ).replace(tzinfo=None)

__all__ = ['init_db', 'get_session', 'User', 'Task', 'PriorityEnum', 'StatusEnum', 'get_moscow_time']
