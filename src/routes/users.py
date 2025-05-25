# src/routes/users.py

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from crud.user import get_users, get_user, update_user, delete_user
from schemas.user import UserRead, UserUpdate
from utils.exceptions import get_error_404
from database import get_db
from auth.dependencies import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/",
    response_model=List[UserRead],
    summary="List users",
    response_description="A list of user profiles with their filenames"
)
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    users = get_users(db, skip, limit)
    result: List[UserRead] = []
    for u in users:
        filenames = [f.filename for f in u.files]
        result.append(
            UserRead(
                id=u.id,
                email=u.email,
                files=filenames
            )
        )
    return result


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get user by ID",
    response_description="The user with the given ID and their filenames"
)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    u = get_user(db, user_id)
    get_error_404(u)
    filenames = [f.filename for f in u.files]
    return UserRead(
        id=u.id,
        email=u.email,
        files=filenames
    )


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Update a user",
    response_description="The updated user profile"
)
def edit_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
):
    existing = get_user(db, user_id)
    get_error_404(existing)
    updated = update_user(db, user_id, user_in)
    filenames = [f.filename for f in updated.files]
    return UserRead(
        id=updated.id,
        email=updated.email,
        files=filenames
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user"
)
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    existing = get_user(db, user_id)
    get_error_404(existing)
    delete_user(db, user_id)
