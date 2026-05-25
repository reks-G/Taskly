from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum

Base = declarative_base()

def get_moscow_time():
    return datetime.utcnow() + timedelta(hours=3)

class PriorityEnum(enum.Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'

class StatusEnum(enum.Enum):
    pending = 'pending'
    in_progress = 'in_progress'
    completed = 'completed'
    overdue = 'overdue'

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    created_at = Column(DateTime, default=get_moscow_time)
    timezone = Column(String(50), default='Europe/Moscow')
    
    tasks = relationship('Task', back_populates='user', cascade='all, delete-orphan')
    
    def get_local_time(self):
        return get_moscow_time()

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=get_moscow_time)
    due_at = Column(DateTime)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.medium)
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)
    notified = Column(Boolean, default=False)
    
    user = relationship('User', back_populates='tasks')
