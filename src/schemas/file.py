# src/schemas/file.py

from datetime import datetime
from pydantic import BaseModel


class FileInfo(BaseModel):
    filename: str
    owner_id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True


class RenameRequest(BaseModel):
    new_name: str


class FileDetail(FileInfo):
    """
    Detailed info about a single file, including its size.
    """
    size: int


class FileStats(BaseModel):
    """
    Aggregated statistics for a user's files.
    """
    total_files: int
    total_size: int


class PublicLinkResponse(BaseModel):
    """
    Response schema for a newly created public link.
    """
    filename: str
    public_token: str
    public_url: str
