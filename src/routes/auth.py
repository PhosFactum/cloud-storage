# src/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from schemas.user import UserCreate, UserRead
from schemas.token import Token
from crud.user import get_user_by_email, create_user
from auth.jwt import create_access_token, verify_password
from auth.dependencies import get_current_user
from database import get_db
import models.user as models
import schemas.user as schemas

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    response_description="User profile without password"
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    - **user_in**: JSON payload with `email` and `password`.
    - **Returns**: the created user (id and email).
    """
    if get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return create_user(db, user_in)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive a JWT",
    response_description="Access token and its type"
)
def login(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Authenticate existing user.
    - **user_in**: JSON payload with `email` and `password`.
    - **Returns**: JSON with `access_token` and `token_type`.
    """
    user = get_user_by_email(db, user_in.email)
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.email)
    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
    response_description="Current user’s id, email and their filenames"
)
def read_current_user(
    current_user: models.User = Depends(get_current_user),
):
    """
    Return the current user's profile and list of their filenames.
    """
    filenames = [f.filename for f in current_user.files]
    return schemas.UserRead(
        id=current_user.id,
        email=current_user.email,
        files=filenames
    )

