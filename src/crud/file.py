# src/crud/file.py

import os
import uuid
import zipfile
from sqlalchemy.orm import Session
from models.file import File

# Корневая папка для всех загрузок
UPLOAD_ROOT = "uploads"


def get_file_details(db: Session, filename: str) -> File | None:
    """
    Возвращает ORM‐объект File по его полному относительному пути (filename),
    например: "user_3/documents/report.pdf". Если не найдено — None.
    """
    return db.query(File).filter(File.filename == filename).first()


def get_user_file_stats(db: Session, owner_id: int) -> tuple[int, int]:
    """
    Возвращает (количество_файлов, суммарный_размер) по всем файлам
    пользователя owner_id. Размер считается, глядя на реальные файлы в папке uploads.
    """
    files = db.query(File).filter(File.owner_id == owner_id).all()
    total_files = len(files)
    total_size = 0
    for f in files:
        path_on_disk = os.path.join(UPLOAD_ROOT, f.filename)
        if os.path.exists(path_on_disk):
            total_size += os.path.getsize(path_on_disk)
    return total_files, total_size


def get_files_by_owner(db: Session, owner_id: int):
    """
    Возвращает список ORM‐объектов File для данного пользователя.
    """
    return db.query(File).filter(File.owner_id == owner_id).all()


def rename_file_record(db: Session, old_name: str, new_name: str) -> File | None:
    """
    Переименовывает запись в БД: old_name → new_name.
    Если записи old_name нет, возвращает None.
    """
    file = get_file_details(db, old_name)
    if file:
        file.filename = new_name
        db.commit()
        db.refresh(file)
        return file
    return None


def create_file(db: Session, filename: str, owner_id: int) -> File:
    """
    Создаёт новую запись File с указанным filename (полный относительный путь, например "user_3/a.txt")
    и owner_id. Возвращает созданный ORM‐объект.
    """
    file = File(filename=filename, owner_id=owner_id)
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


def get_file(db: Session, filename: str) -> File | None:
    """
    Ищет в БД запись File по точному filename. Если не находит — возвращает None.
    """
    return db.query(File).filter(File.filename == filename).first()


def delete_file_record(db: Session, filename: str):
    """
    Удаляет из БД запись File с этим filename (если она есть) и коммитит.
    """
    file = get_file(db, filename)
    if file:
        db.delete(file)
        db.commit()


# --- Новая функция: распаковка ZIP и регистрация директории ---
def unpack_and_register_directory(db: Session, zip_path: str, owner_id: int) -> list[File]:
    """
    1) Распаковывает zip-файл, лежащий по абсолютному пути zip_path, во временную папку.
    2) Проходит по каждому файлу внутри распакованной структуры,
       перемещает его в uploads/user_{owner_id}/… сохраняя вложенную структуру.
    3) Создаёт запись в БД через create_file(...) для каждого перемещённого файла.
    4) Возвращает список созданных ORM‐объектов File.
    """
    base_tmp = zip_path + "_tmp"
    os.makedirs(base_tmp, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(base_tmp)
    except zipfile.BadZipFile:
        # если не zip или повреждённый архив
        return []

    created_files: list[File] = []
    user_prefix = f"user_{owner_id}/"

    for root, _, files in os.walk(base_tmp):
        for fname in files:
            abs_src_path = os.path.join(root, fname)
            rel_inside = os.path.relpath(abs_src_path, base_tmp)  # e.g. "docs/a.txt"
            rel_full_path = os.path.normpath(user_prefix + rel_inside.replace("\\", "/"))
            abs_target_path = os.path.join(UPLOAD_ROOT, rel_full_path)

            os.makedirs(os.path.dirname(abs_target_path), exist_ok=True)
            os.replace(abs_src_path, abs_target_path)

            try:
                new_rec = create_file(db, rel_full_path, owner_id)
                created_files.append(new_rec)
            except Exception:
                db.rollback()
                continue

    # Удаляем временную папку
    try:
        import shutil
        shutil.rmtree(base_tmp)
    except Exception:
        pass

    return created_files


# --- Публичные ссылки (без изменений) ---
def create_public_link(db: Session, filename: str) -> File | None:
    """
    Генерирует новый UUID4‑токен для данной записи File (по filename),
    сохраняет его в public_token, возвращает обновлённый ORM‑объект.
    """
    file = get_file(db, filename)
    if not file:
        return None

    token = str(uuid.uuid4())
    file.public_token = token
    db.commit()
    db.refresh(file)
    return file


def get_file_by_token(db: Session, token: str) -> File | None:
    """
    Возвращает объект File, у которого public_token == token, или None.
    """
    return db.query(File).filter(File.public_token == token).first()
