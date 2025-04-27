from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from ..models.models import PriorityEnum, StatusEnum

class UserBase(BaseModel):
    username: str
    email: str
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: PriorityEnum = PriorityEnum.LOW
    status: StatusEnum = StatusEnum.TO_DO

class TaskCreate(TaskBase):
    category_id: Optional[int] = None

class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: int
    category_id: Optional[int] = None

    class Config:
        orm_mode = True

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    created_at: datetime
    user_id: int
    tasks: List[Task] = []

    class Config:
        orm_mode = True 