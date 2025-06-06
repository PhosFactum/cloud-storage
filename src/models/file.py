# src/models/file.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    # В поле filename теперь хранится относительный путь: "user_{owner_id}/…"
    filename = Column(String, unique=True, index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- новое поле для UUID‐токена публичной ссылки ---
    public_token = Column(String, unique=True, index=True, nullable=True)

    owner = relationship("User", back_populates="files")
