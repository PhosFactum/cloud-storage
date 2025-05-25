# src/routes/files.py

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import shutil
import os

from database import get_db
from auth.dependencies import get_current_user
from models.user import User
from crud.file import (
    create_file,
    get_file as crud_get_file,
    delete_file_record,
    get_files_by_owner,
    rename_file_record,
)
from schemas.file import FileInfo, RenameRequest

router = APIRouter(
    prefix="/files",
    tags=["Files"],
    dependencies=[Depends(get_current_user)],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get(
    "/",
    response_model=list[str],
    summary="List user files",
    response_description="Filenames the user may download",
)
async def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return a list of filenames uploaded by the current user.
    """
    files = get_files_by_owner(db, current_user.id)
    return [f.filename for f in files]


@router.get(
    "/download/{filename}",
    response_class=FileResponse,
    summary="Download a file",
    response_description="Binary content of the requested file",
)
async def download_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download a file by its filename, if owned by the current user.
    """
    record = crud_get_file(db, filename)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post(
    "/upload",
    response_model=FileInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    response_description="Uploaded file metadata",
)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file and associate it with the current user.
    Returns the file metadata (filename, owner_id, uploaded_at).
    """
    target = os.path.join(UPLOAD_DIR, file.filename)
    with open(target, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    file_record = create_file(db, file.filename, current_user.id)
    return file_record  # FileInfo via orm_mode


@router.put(
    "/{filename}",
    response_model=dict,
    summary="Rename a file",
    response_description="Old and new filename",
)
async def rename_file(
    filename: str,
    req: RenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rename a file owned by the current user.
    - **filename**: current name of the file
    - **new_name**: desired new filename
    """
    record = crud_get_file(db, filename)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    old_path = os.path.join(UPLOAD_DIR, filename)
    new_path = os.path.join(UPLOAD_DIR, req.new_name)
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="New filename already exists")

    os.rename(old_path, new_path)
    rename_file_record(db, filename, req.new_name)
    return {"old_name": filename, "new_name": req.new_name}


@router.delete(
    "/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
)
async def delete_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a file owned by the current user.
    """
    record = crud_get_file(db, filename)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    # remove from disk
    path = os.path.join(UPLOAD_DIR, filename)
    os.remove(path)
    # remove from db
    delete_file_record(db, filename)
