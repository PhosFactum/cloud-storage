from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crud.user import get_users, get_user, update_user, delete_user
from schemas.user import UserRead, UserUpdate
from utils.exceptions import get_error_404
from database import get_db


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserRead])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_users(db, skip, limit)


@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    get_error_404(user)
    return user


@router.put("/{user_id}", response_model=UserRead)
def edit_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    existing = get_user(db, user_id)
    get_error_404(existing)
    return update_user(db, user_id, user_in)


@router.delete("/{user_id}", status_code=204)
def remove_user(user_id: int, db: Session = Depends(get_db)):
    existing = get_user(db, user_id)
    get_error_404(existing)
    delete_user(db, user_id)