from fastapi import (
    APIRouter,
    UploadFile,
    File as FileParam,
    HTTPException,
    Depends,
    status,
    Query,
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
from models.directory import Directory
from models.file import File as FileModel
from schemas.file import (
    FileInfo,
    FileDetail,
    FileStats,
    PublicLinkResponse,
    ListDirResponse,
)
from crud.file import (
    create_file,
    get_file as crud_get_file,
    delete_file_record,
    get_user_file_stats,
    create_public_link,
    get_file_by_token,
    unpack_and_register_directory,
)
from crud.directory import (
    create_directory,
    get_directories_for_user,
)

router = APIRouter(
    prefix="/files",
    tags=["Files"],
)

UPLOAD_ROOT = "uploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)


@router.get(
    "/",
    response_model=ListDirResponse,
    summary="List files and directories",
    dependencies=[Depends(get_current_user)],
)
def list_dir(
    path: str = Query("", description="Relative path under user_{id}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Возвращает:
      - directories: список имён вложенных папок
      - files: список имён файлов
    по конкретной директории.
    """
    user_prefix = f"user_{current_user.id}"
    # полный префикс в таблицах
    full_prefix = user_prefix + (f"/{path}" if path else "")

    # получаем все папки пользователя
    all_dirs = get_directories_for_user(db, current_user.id)
    # фильтруем дочерние: у которых путь начинается с full_prefix + '/'
    # и не содержит дополнительного '/'
    children_dirs = []
    for d in all_dirs:
        p = d.path
        if full_prefix:
            if not p.startswith(full_prefix + "/"):
                continue
            rest = p[len(full_prefix) + 1 :]
        else:
            if not p.startswith(user_prefix + "/"):
                continue
            rest = p[len(user_prefix) + 1 :]
        if "/" not in rest:
            children_dirs.append(rest)

    # файлы аналогично
    files = db.query(FileModel).filter(FileModel.owner_id == current_user.id).all()
    children_files = []
    for f in files:
        fn = f.filename
        if full_prefix:
            if not fn.startswith(full_prefix + "/"):
                continue
            rest = fn[len(full_prefix) + 1 :]
        else:
            if not fn.startswith(user_prefix + "/"):
                continue
            rest = fn[len(user_prefix) + 1 :]
        if "/" not in rest:
            children_files.append(rest)

    return ListDirResponse(directories=children_dirs, files=children_files)


@router.post(
    "/{file_path:path}/mkdir",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new directory",
    dependencies=[Depends(get_current_user)],
)
def make_dir(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создаёт новую запись Directory по полному относительному пути file_path.
    """
    full = file_path
    # проверяем, что ни в files, ни в directories нет такого пути
    exists_file = crud_get_file(db, full)
    exists_dir = db.query(Directory).filter(Directory.path == full).first()
    if exists_file or exists_dir:
        raise HTTPException(status_code=400, detail="Already exists")

    new_dir = create_directory(db, full, current_user.id)
    return {"path": new_dir.path}


@router.post(
    "/upload",
    response_model=FileInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a single file",
    dependencies=[Depends(get_current_user)],
)
async def upload_file(
    file: UploadFile = FileParam(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_prefix = f"user_{current_user.id}/"
    rel_path = user_prefix + file.filename
    abs_path = os.path.join(UPLOAD_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        file_record = create_file(db, rel_path, current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail="File already exists")
    return file_record


@router.get(
    "/stats",
    response_model=FileStats,
    summary="Get user file statistics",
    dependencies=[Depends(get_current_user)],
)
def stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_files, total_size = get_user_file_stats(db, current_user.id)
    return FileStats(total_files=total_files, total_size=total_size)


@router.get(
    "/download/{file_path:path}",
    response_class=FileResponse,
    summary="Download file",
    dependencies=[Depends(get_current_user)],
)
def download_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = crud_get_file(db, file_path)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(404, detail="Not found")
    abs_path = os.path.join(UPLOAD_ROOT, record.filename)
    return FileResponse(path=abs_path, filename=os.path.basename(record.filename))


@router.delete(
    "/{file_path:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete file",
    dependencies=[Depends(get_current_user)],
)
def delete_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = crud_get_file(db, file_path)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(404, detail="Not found")
    abs_path = os.path.join(UPLOAD_ROOT, record.filename)
    if os.path.exists(abs_path):
        os.remove(abs_path)
    delete_file_record(db, record.filename)


@router.post(
    "/{file_path:path}/public-link",
    response_model=PublicLinkResponse,
    summary="Generate public link",
    dependencies=[Depends(get_current_user)],
)
def make_public_link(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = crud_get_file(db, file_path)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(404, detail="Not found")
    updated = create_public_link(db, file_path)
    public_url = f"http://localhost:8002/files/public/{updated.public_token}"
    return PublicLinkResponse(
        filename=updated.filename,
        public_token=updated.public_token,
        public_url=public_url,
    )


@router.get(
    "/public/{token}",
    response_class=FileResponse,
    summary="Download by public token",
)
def download_by_token(token: str, db: Session = Depends(get_db)):
    record = get_file_by_token(db, token)
    if not record:
        raise HTTPException(404, detail="Invalid token")
    abs_path = os.path.join(UPLOAD_ROOT, record.filename)
    return FileResponse(path=abs_path, filename=os.path.basename(record.filename))
