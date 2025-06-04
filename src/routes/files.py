# src/routes/files.py

from fastapi import (
    APIRouter,
    UploadFile,
    File as FileParam,         # переименовали, чтобы не перекрывать имя File из модели
    HTTPException,
    Depends,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
    create_public_link,
    get_file_by_token,
)
from schemas.file import (
    FileInfo,
    RenameRequest,
    FileDetail,
    FileStats,
    PublicLinkResponse,
)
from utils.exceptions import get_error_404

router = APIRouter(
    prefix="/files",
    tags=["Files"],
    dependencies=[Depends(get_current_user)],  # по умолчанию все эндпоинты требуют авторизации
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get(
    "/stats",
    response_model=FileStats,
    summary="Get user file statistics",
    response_description="Total number of files and their combined size in bytes",
)
async def file_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the total count of files and the sum of their sizes (in bytes)
    for the current user.
    """
    total_files, total_size = get_user_file_stats(db, current_user.id)
    return FileStats(total_files=total_files, total_size=total_size)


@router.get(
    "/{filename}/info",
    response_model=FileDetail,
    summary="Get file detail",
    response_description="Filename, owner, upload time, and size",
)
async def file_info(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return detailed metadata for a single file:
    - **filename**: the file’s name
    - **owner_id**: ID of the file’s owner
    - **uploaded_at**: timestamp
    - **size**: file size in bytes
    """
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
        size=size,
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
    file: UploadFile = FileParam(...),  # теперь FileParam вместо File
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file and associate it with the current user.
    Returns the file metadata (filename, owner_id, uploaded_at).
    """
    target = os.path.join(UPLOAD_DIR, file.filename)
    # Сохраняем бинарник на диск
    with open(target, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        file_record = create_file(db, file.filename, current_user.id)
    except IntegrityError:
        # Если в БД уже есть запись с таким же именем
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File with this name already exists"
        )
    return file_record  # благодаря orm_mode → FileInfo


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
    """
    Delete a file owned by the current user.
    """
    record = crud_get_file(db, filename)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)

    delete_file_record(db, filename)


# === НОВЫЕ МАРШРУТЫ ДЛЯ ПУБЛИЧНОЙ ССЫЛКИ ===

@router.post(
    "/{filename}/public-link",
    response_model=PublicLinkResponse,
    summary="Generate a public link for a file",
    response_description="Filename, token and full public URL",
)
async def make_public_link(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create or overwrite a public UUID‑token for an existing file.
    Returns JSON: {"filename":..., "public_token":..., "public_url": "..."}.
    """
    record = crud_get_file(db, filename)
    get_error_404(record)

    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated = create_public_link(db, filename)
    if not updated:
        raise HTTPException(status_code=404, detail="File not found")

    # Формируем полный URL (по умолчанию localhost:8002; замените на ваш хост/порт при необходимости)
    public_url = f"http://localhost:8002/files/public/{updated.public_token}"
    return PublicLinkResponse(
        filename=updated.filename,
        public_token=updated.public_token,
        public_url=public_url,
    )


# Этот эндпоинт НЕ находится под Depends(get_current_user) – он монтируется отдельно ниже
@router.get(
    "/public/{token}",
    response_class=FileResponse,
    summary="Download file by public token",
    response_description="Binary content of the file",
    dependencies=[],  # убираем зависимость get_current_user, чтобы был доступ без авторизации
)
async def download_by_public_token(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Allow anyone to download a file by its public UUID‑token.
    """
    record = get_file_by_token(db, token)
    if not record:
        raise HTTPException(status_code=404, detail="Invalid or expired public token")

    path = os.path.join(UPLOAD_DIR, record.filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=path,
        filename=record.filename,
        media_type="application/octet-stream",
    )
