import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

# Use DATABASE_URL from environment (e.g., from Railway) or fall back to local SQLite
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///drift.db')

# Fix PostgreSQL URL scheme if needed (Railway might use postgres:// instead of postgresql://)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create engine with appropriate connection arguments
if DATABASE_URL.startswith('postgresql://'):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})

SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
