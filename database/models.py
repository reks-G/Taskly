from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

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
    created_at = Column(DateTime, default=datetime.now)
    timezone = Column(String(50), default='UTC')
    
    tasks = relationship('Task', back_populates='user', cascade='all, delete-orphan')

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    due_at = Column(DateTime)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.medium)
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)
    notified = Column(Boolean, default=False)
    
    user = relationship('User', back_populates='tasks')
