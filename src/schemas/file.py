# src/schemas/file.py

from datetime import datetime
from pydantic import BaseModel

class FileInfo(BaseModel):
    """
    Shared properties of a file.
    """
    filename: str
    owner_id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True


class RenameRequest(BaseModel):
    """
    Request schema for renaming a file.
    """
    new_name: str
