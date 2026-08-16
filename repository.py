import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        count = conn.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
        if count == 0:
            conn.execute(
                """
                INSERT INTO tasks (title, done) VALUES
                    (%s, %s), (%s, %s), (%s, %s)
                """,
                ("Buy milk", False, "Learn FastAPI", False, "Push to GitHub", True),
            )


def list_tasks():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()


def get_task(task_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM tasks WHERE id = %s", (task_id,)
        ).fetchone()


def create_task(title: str):
    with get_connection() as conn:
        return conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
            (title, False),
        ).fetchone()


def update_task(task_id: int, title: str, done: bool):
    with get_connection() as conn:
        return conn.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
            (title, done, task_id),
        ).fetchone()


def delete_task(task_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return cursor.rowcount > 0