from fastapi import (
    APIRouter,
    UploadFile,
    File as FileParam,         # чтобы не пересекаться с моделью File
    HTTPException,
    Depends,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import shutil
import os
import uuid

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
    unpack_and_register_directory,
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
)

# Общая папка для всех загрузок
UPLOAD_ROOT = "uploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)


@router.get(
    "/stats",
    response_model=FileStats,
    summary="Get user file statistics",
    response_description="Total number of files and their combined size in bytes",
    dependencies=[Depends(get_current_user)],
)
async def file_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Возвращает общее количество и суммарный размер (в байтах)
    всех файлов, принадлежащих текущему пользователю.
    """
    total_files, total_size = get_user_file_stats(db, current_user.id)
    return FileStats(total_files=total_files, total_size=total_size)


@router.get(
    "/",
    response_model=list[str],
    summary="List user files (relative paths)",
    response_description="Filenames (relative paths) the user may download",
    dependencies=[Depends(get_current_user)],
)
async def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Возвращает список относительных путей всех файлов текущего пользователя,
    например: ["user_3/readme.txt", "user_3/docs/report.pdf", …]
    """
    files = get_files_by_owner(db, current_user.id)
    return [f.filename for f in files]


@router.get(
    "/{file_path:path}/info",
    response_model=FileDetail,
    summary="Get file detail",
    response_description="Filename, owner, upload time, and size",
    dependencies=[Depends(get_current_user)],
)
async def file_info(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Возвращает детальную информацию по конкретному файлу:
      • **file_path** — относительный путь: "user_{id}/…"
    """
    record = get_file_details(db, file_path)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    path_on_disk = os.path.join(UPLOAD_ROOT, record.filename)
    if not os.path.exists(path_on_disk):
        raise HTTPException(status_code=404, detail="File not found on disk")

    size = os.path.getsize(path_on_disk)
    return FileDetail(
        filename=record.filename,
        owner_id=record.owner_id,
        uploaded_at=record.uploaded_at,
        size=size,
    )


@router.get(
    "/download/{file_path:path}",
    response_class=FileResponse,
    summary="Download a file",
    response_description="Binary content of the requested file",
    dependencies=[Depends(get_current_user)],
)
async def download_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Скачивание файла по относительному пути (например, "user_3/docs/a.txt"),
    если он принадлежит текущему пользователю.
    """
    record = crud_get_file(db, file_path)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    path_on_disk = os.path.join(UPLOAD_ROOT, record.filename)
    if not os.path.exists(path_on_disk):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=path_on_disk,
        filename=os.path.basename(record.filename),
        media_type="application/octet-stream",
    )


@router.post(
    "/upload",
    response_model=FileInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a single file",
    response_description="Uploaded file metadata",
    dependencies=[Depends(get_current_user)],
)
async def upload_file(
    file: UploadFile = FileParam(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Загрузка одного файла:
      • Сохраняем файл в "uploads/user_{id}/{filename}"
      • Создаём запись в БД
    """
    user_prefix = f"user_{current_user.id}/"
    rel_path = user_prefix + file.filename  # e.g. "user_5/readme.pdf"
    abs_path = os.path.join(UPLOAD_ROOT, rel_path)

    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        file_record = create_file(db, rel_path, current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File with this name already exists",
        )
    return file_record  # автоматически сериализуется в FileInfo


@router.post(
    "/upload-dir",
    response_model=list[FileInfo],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a directory as ZIP‑archive",
    response_description="Returns list of metadata for all uploaded files",
    dependencies=[Depends(get_current_user)],
)
async def upload_directory(
    zip_file: UploadFile = FileParam(..., description="ZIP‑архив с файлами и папками"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Загрузка «директории» через ZIP:
      1. Сохраняем файл архива временно в uploads/tmp_uploads/tmp_{uuid}.zip
      2. Распаковываем весь архив во временную папку
      3. Для каждого файла внутри архива:
         a) Перемещаем его в uploads/user_{owner_id}/… сохраняя вложенность
         b) Создаём запись в БД (create_file)
      4. Удаляем сам ZIP
      5. Возвращаем список всех созданных записей (FileInfo)
    """
    tmp_dir = os.path.join(UPLOAD_ROOT, "tmp_uploads")
    os.makedirs(tmp_dir, exist_ok=True)

    unique_name = f"tmp_{uuid.uuid4().hex}.zip"
    abs_zip_path = os.path.join(tmp_dir, unique_name)
    with open(abs_zip_path, "wb") as buffer:
        shutil.copyfileobj(zip_file.file, buffer)

    created = unpack_and_register_directory(db, abs_zip_path, current_user.id)

    try:
        os.remove(abs_zip_path)
    except Exception:
        pass

    return created


@router.put(
    "/{file_path:path}",
    response_model=FileInfo,
    summary="Rename (or move) a file",
    response_description="Updated file metadata",
    dependencies=[Depends(get_current_user)],
)
async def rename_file(
    file_path: str,
    req: RenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Переименовать (или переместить) файл:
      • **file_path** — текущий относительный путь (e.g. "user_3/docs/a.txt")
      • **req.new_name** — новый путь относительно "user_{id}/", например "reports/new.pdf"
      Итоговый относительный путь: "user_{id}/reports/new.pdf"
    """
    record = crud_get_file(db, file_path)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    new_rel = f"user_{current_user.id}/{req.new_name}"
    old_abs = os.path.join(UPLOAD_ROOT, record.filename)
    new_abs = os.path.join(UPLOAD_ROOT, new_rel)

    if not os.path.exists(old_abs):
        raise HTTPException(status_code=404, detail="File not found on disk")
    if os.path.exists(new_abs):
        raise HTTPException(status_code=400, detail="New filename already exists")

    os.makedirs(os.path.dirname(new_abs), exist_ok=True)
    os.replace(old_abs, new_abs)

    updated = rename_file_record(db, record.filename, new_rel)
    if not updated:
        raise HTTPException(status_code=500, detail="Error renaming in DB")
    return updated  # сериализуется в FileInfo


@router.delete(
    "/{file_path:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    dependencies=[Depends(get_current_user)],
)
async def delete_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить файл по относительному пути (e.g. "user_3/docs/a.txt"):
      • Удаляем физически из папки uploads/…
      • Удаляем запись из БД
    """
    record = crud_get_file(db, file_path)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    path_on_disk = os.path.join(UPLOAD_ROOT, record.filename)
    if os.path.exists(path_on_disk):
        os.remove(path_on_disk)

    delete_file_record(db, record.filename)
    return None  # 204 No Content


@router.post(
    "/{file_path:path}/public-link",
    response_model=PublicLinkResponse,
    summary="Generate a public link for a file",
    response_description="Filename, token and full public URL",
    dependencies=[Depends(get_current_user)],
)
async def make_public_link(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Генерирует или перезаписывает UUID‑токен для существующего файла.
    Возвращает:
      {
        "filename": "...",
        "public_token": "...",
        "public_url": "http://localhost:8002/files/public/..."
      }
    """
    record = crud_get_file(db, file_path)
    get_error_404(record)
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated = create_public_link(db, file_path)
    if not updated:
        raise HTTPException(status_code=404, detail="File not found")

    public_url = f"http://localhost:8002/files/public/{updated.public_token}"
    return PublicLinkResponse(
        filename=updated.filename,
        public_token=updated.public_token,
        public_url=public_url,
    )


@router.get(
    "/public/{token}",
    response_class=FileResponse,
    summary="Download file by public token",
    response_description="Binary content of the file",
    dependencies=[],  # без авторизации
)
async def download_by_public_token(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Позволяет скачать файл любому пользователю по public UUID‑token.
    """
    record = get_file_by_token(db, token)
    if not record:
        raise HTTPException(status_code=404, detail="Invalid or expired public token")

    path_on_disk = os.path.join(UPLOAD_ROOT, record.filename)
    if not os.path.exists(path_on_disk):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=path_on_disk,
        filename=os.path.basename(record.filename),
        media_type="application/octet-stream",
    )
