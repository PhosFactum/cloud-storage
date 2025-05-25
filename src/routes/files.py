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
    get_file_details,
    get_user_file_stats,
)
from schemas.file import FileInfo, RenameRequest, FileDetail, FileStats
from utils.exceptions import get_error_404

router = APIRouter(
    prefix="/files",
    tags=["Files"],
    dependencies=[Depends(get_current_user)],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get(
    "/stats",
    response_model=FileStats,
    summary="Get user file statistics",
    response_description="Total number of files and their combined size in bytes"
)
async def file_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_files, total_size = get_user_file_stats(db, current_user.id)
    return FileStats(total_files=total_files, total_size=total_size)


@router.get(
    "/{filename}/info",
    response_model=FileDetail,
    summary="Get file detail",
    response_description="Filename, owner, upload time, and size"
)
async def file_info(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = get_file_details(db, filename)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    size = os.path.getsize(path)
    return FileDetail(
        filename=record.filename,
        owner_id=record.owner_id,
        uploaded_at=record.uploaded_at,
        size=size
    )


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
    record = crud_get_file(db, filename)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

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
    target = os.path.join(UPLOAD_DIR, file.filename)
    with open(target, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    file_record = create_file(db, file.filename, current_user.id)
    return file_record


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
    record = crud_get_file(db, filename)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

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
    record = crud_get_file(db, filename)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)

    delete_file_record(db, filename)
