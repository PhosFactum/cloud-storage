# src/crud/file.py
from sqlalchemy.orm import Session
from models.file import File

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
