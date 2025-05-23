from typing import Optional
from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None