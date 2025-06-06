# src/schemas/file.py

from datetime import datetime
from pydantic import BaseModel


class FileInfo(BaseModel):
    """
    Отдаётся при загрузке (upload) или при списке.
    Поле filename — это относительный путь: "user_{owner_id}/…"
    """
    filename: str
    owner_id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True


class RenameRequest(BaseModel):
    """
    При запросе на переименование (перемещение) файла:
      • new_name — это новый путь (относительно user_{owner_id}), например:
        "docs2/new_report.pdf" или просто "photo.jpg" (в корне user_{owner_id}/).
    """
    new_name: str


class FileDetail(FileInfo):
    """
    Детальная информация о файле + размер.
    """
    size: int


class FileStats(BaseModel):
    """
    Объём и количество файлов пользователя.
    """
    total_files: int
    total_size: int


class PublicLinkResponse(BaseModel):
    """
    Ответ при генерации публичной ссылки:
    {
        "filename": "user_3/docs/a.txt",
        "public_token": "550e8400-e29b-41d4-a716-446655440000",
        "public_url": "http://localhost:8002/files/public/550e8400-e29b-41d4-a716-446655440000"
    }
    """
    filename: str
    public_token: str
    public_url: str
