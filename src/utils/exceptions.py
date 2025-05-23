# app/utils/exceptions.py
from fastapi import HTTPException, status

def get_error_404(resource):
    """
    Checking resource: if None - throws HTTP 404
    """
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return resource
