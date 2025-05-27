# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from src.config import DB_URL

def get_conn():
    print("Connecting with URL:", DB_URL)  # Добавьте эту строку
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def init_db():
    """Создаёт таблицы, если их ещё нет."""
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS sleep_data (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            sleep_time TIMESTAMP NOT NULL,
            wake_time TIMESTAMP NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            date TIMESTAMP NOT NULL,
            level TEXT NOT NULL,
            exercises TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            reminder_time TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            for sql in ddl:
                cur.execute(sql)
    conn.close()

def save_workout(user_id: int, level: str, exercises: str):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workouts (user_id, date, level, exercises)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, datetime.now(), level, exercises)
            )
    conn.close()

def get_user_workouts(user_id: int, limit: int = 3):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date, level, exercises
            FROM workouts
            WHERE user_id = %s
            ORDER BY date DESC
            LIMIT %s
            """,
            (user_id, limit)
        )
        rows = cur.fetchall()  # вот здесь rows — list of dicts
    conn.close()
    # Приводим в привычный формат [(date, level, exercises), …]
    return [
        (row['date'], row['level'], row['exercises'])
        for row in rows
    ]


def save_sleep_data(user_id: int, sleep_time: str, wake_time: str):
    now = datetime.now()
    sleep_dt = datetime.strptime(sleep_time, '%H:%M')
    wake_dt = datetime.strptime(wake_time, '%H:%M')

    # Привязываем дату к sleep_time — сегодня или вчера
    sleep_datetime = now.replace(
        hour=sleep_dt.hour, minute=sleep_dt.minute, second=0, microsecond=0
    )
    if sleep_datetime > now:
        sleep_datetime -= timedelta(days=1)

    # wake_time считается на следующий день, если раньше sleep_time
    wake_datetime = now.replace(
        hour=wake_dt.hour, minute=wake_dt.minute, second=0, microsecond=0
    )
    if wake_datetime <= sleep_datetime:
        wake_datetime += timedelta(days=1)

    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sleep_data (user_id, sleep_time, wake_time)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    sleep_datetime,
                    wake_datetime
                )
            )
    conn.close()

def get_sleep_data(user_id: int, days: int = 7):
    since = datetime.now() - timedelta(days=days)
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sleep_time::date AS date,
                   sleep_time,
                   wake_time
            FROM sleep_data
            WHERE user_id = %s
              AND sleep_time >= %s
            ORDER BY sleep_time ASC
            """,
            (user_id, since)
        )
        rows = cur.fetchall()
    conn.close()
    return rows
