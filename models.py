import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Agent(Base):
    __tablename__ = 'agents'

    agent_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    agent_code = Column(Text, nullable=False)
    execution_frequency = Column(Integer, nullable=False)
    last_executed = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Execution(Base):
    __tablename__ = 'executions'

    execution_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey('agents.agent_id'), nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)
    result = Column(Text, nullable=True)
    trade_executed = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
