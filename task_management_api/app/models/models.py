from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQL_Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PriorityEnum(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

class StatusEnum(Enum):
    TO_DO = 'to_do'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    tasks = relationship('Task', back_populates='owner')

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    due_date = Column(DateTime)
    priority = Column(SQL_Enum(PriorityEnum), default=PriorityEnum.LOW)
    status = Column(SQL_Enum(StatusEnum), default=StatusEnum.TO_DO)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    owner = relationship('User', back_populates='tasks') 
    category = relationship('Category', back_populates='tasks') 

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'))
    tasks = relationship('Task', back_populates='category') 