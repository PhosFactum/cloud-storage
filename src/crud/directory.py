from sqlalchemy.orm import Session
from models.directory import Directory

def create_directory(db: Session, path: str, owner_id: int) -> Directory:
    d = Directory(path=path, owner_id=owner_id)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d

def get_directories_for_user(db: Session, owner_id: int) -> list[Directory]:
    return db.query(Directory).filter(Directory.owner_id == owner_id).all()
