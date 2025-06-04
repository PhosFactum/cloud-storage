# src/crud/file.py

import os
import uuid
from sqlalchemy.orm import Session
from models.file import File

UPLOAD_DIR = "uploads"


def get_file_details(db: Session, filename: str) -> File | None:
    """
    Return the File ORM object by filename, or None.
    """
    return db.query(File).filter(File.filename == filename).first()


def get_user_file_stats(db: Session, owner_id: int) -> tuple[int, int]:
    """
    Return (count, sum_size) of all files for this owner.
    """
    files = db.query(File).filter(File.owner_id == owner_id).all()
    total_files = len(files)
    total_size = 0
    for f in files:
        path = os.path.join(UPLOAD_DIR, f.filename)
        if os.path.exists(path):
            total_size += os.path.getsize(path)
    return total_files, total_size


def get_files_by_owner(db: Session, owner_id: int):
    return db.query(File).filter(File.owner_id == owner_id).all()


def rename_file_record(db: Session, old_name: str, new_name: str):
    file = db.query(File).filter(File.filename == old_name).first()
    if file:
        file.filename = new_name
        db.commit()
        db.refresh(file)
    return file


def create_file(db: Session, filename: str, owner_id: int) -> File:
    file = File(filename=filename, owner_id=owner_id)
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


def get_file(db: Session, filename: str):
    return db.query(File).filter(File.filename == filename).first()


def delete_file_record(db: Session, filename: str):
    file = get_file(db, filename)
    if file:
        db.delete(file)
        db.commit()


# --- New: create public link for an existing file ---
def create_public_link(db: Session, filename: str) -> File | None:
    """
    Generate a new unique UUID4 token for the given filename,
    save it in the DB (public_token) and return the updated File.
    """
    file = db.query(File).filter(File.filename == filename).first()
    if not file:
        return None

    token = str(uuid.uuid4())
    file.public_token = token
    db.commit()
    db.refresh(file)
    return file


def get_file_by_token(db: Session, token: str) -> File | None:
    """
    Return File ORM object whose public_token == token, or None.
    """
    return db.query(File).filter(File.public_token == token).first()
