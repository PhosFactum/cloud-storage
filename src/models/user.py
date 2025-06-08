from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # файлы пользователя
    files = relationship(
        "File",
        back_populates="owner",
        cascade="all, delete",
    )
    # директории пользователя — back_populates совпадает с `owner` в Directory
    directories = relationship(
        "Directory",
        back_populates="owner",
        cascade="all, delete",
    )
