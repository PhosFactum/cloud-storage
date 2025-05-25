# src/schemas/user.py

from typing import List, Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserRead(UserBase):
    id: int
    files: List[str] = []  # <-- добавили поле files

    class Config:
        from_attributes = True