from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Generator

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tasks.db"
SEED_VERSION = 1


class TaskCreate(BaseModel):
    title: str
    done: bool = False


class TaskUpdate(BaseModel):
    title: str
    done: bool


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool


def connect_db() -> sqlite3.Connection:
    """Hər əməliyyat üçün ayrıca SQLite bağlantısı qaytarır."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Cədvəli yaradır və nümunə task-ları yalnız ilk başlanğıcda əlavə edir."""
    with connect_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
            )
            """
        )

        # PRAGMA user_version verilənlər bazası faylında qalıcıdır.
        # Buna görə task-lar sonradan silinsə belə seed yenidən əlavə olunmur.
        initialized = connection.execute("PRAGMA user_version").fetchone()[0]
        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

        if initialized < SEED_VERSION:
            if task_count == 0:
                connection.executemany(
                    "INSERT INTO tasks (title, done) VALUES (?, ?)",
                    [
                        ("FastAPI layihəsini yarat", 1),
                        ("SQLite inteqrasiyasını tamamla", 0),
                        ("CRUD endpoint-lərini yoxla", 0),
                    ],
                )
            connection.execute(f"PRAGMA user_version = {SEED_VERSION}")


def get_db() -> Generator[sqlite3.Connection, None, None]:
    connection = connect_db()
    try:
        yield connection
    finally:
        connection.close()


def row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
    }


def require_title(title: str) -> str:
    normalized_title = title.strip()
    if not normalized_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title boş ola bilməz",
        )
    return normalized_title


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Tasks API", lifespan=lifespan)


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    row = db.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task tapılmadı",
        )
    return row_to_task(row)


@app.post("/tasks", response_model=TaskOut)
def create_task(
    payload: TaskCreate, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    title = require_title(payload.title)

    cursor = db.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (title, int(payload.done)),
    )
    db.commit()

    row = db.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return row_to_task(row)


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, payload: TaskUpdate, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    title = require_title(payload.title)

    cursor = db.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (title, int(payload.done), task_id),
    )
    db.commit()

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task tapılmadı",
        )

    row = db.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    return row_to_task(row)


@app.delete("/tasks/{task_id}", response_model=TaskOut)
def delete_task(task_id: int, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    row = db.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task tapılmadı",
        )

    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return row_to_task(row)


# İşə salmaq üçün:
# uvicorn main:app --reload