# src/routes/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud.user import get_users, get_user, update_user, delete_user
from schemas.user import UserRead, UserUpdate
from utils.exceptions import get_error_404
from database import get_db
from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)

@router.get(
    "/",
    response_model=list[UserRead],
    summary="List users",
    response_description="A list of user profiles"
)
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a paginated list of users.
    - **skip**: number of items to skip
    - **limit**: maximum number of users to return
    """
    return get_users(db, skip, limit)

@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get user by ID",
    response_description="The user with the given ID"
)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a single user by their unique ID.
    - **user_id**: integer ID of the user
    """
    user = get_user(db, user_id)
    get_error_404(user)
    return user

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
    current_user: User = Depends(get_current_user),
):
    """
    Update user’s email or password.
    - **user_id**: ID of the user to update
    - **user_in**: fields to change (email and/or password)
    """
    existing = get_user(db, user_id)
    get_error_404(existing)
    return update_user(db, user_id, user_in)

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user"
)
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a user by ID.
    - **user_id**: ID of the user to remove
    """
    existing = get_user(db, user_id)
    get_error_404(existing)
    delete_user(db, user_id)
