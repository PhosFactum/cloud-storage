# src/crud/user.py
from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate, UserUpdate
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, hashed_password: str) -> User:
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, user_in: UserUpdate) -> User | None:
    user = get_user(db, user_id)
    if not user:
        return None

    if user_in.email is not None:
        user.email = user_in.email
    if user_in.password is not None:
        user.hashed_password = pwd_context.hash(user_in.password)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> User | None:
    user = get_user(db, user_id)

    if user:
        db.delete(user)
        db.commit()

    return user