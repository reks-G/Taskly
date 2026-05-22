from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from database.models import Base

DATABASE_URL = 'sqlite:///taskcontrol.db'

engine = create_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={
        'check_same_thread': False,
        'timeout': 10
    },
    poolclass=StaticPool,
    pool_pre_ping=True
)

SessionLocal = scoped_session(sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False,
    expire_on_commit=False
))

def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()
