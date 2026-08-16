from dotenv import load_dotenv

load_dotenv()

import repository
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
repository.init_db()


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


def row_to_task(row: dict) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.get("/", summary="API info")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks")
def get_tasks():
    return [row_to_task(r) for r in repository.list_tasks()]


@app.get("/tasks/{task_id}", summary="Get one task by id")
def get_task(task_id: int):
    row = repository.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    row = repository.create_task(task.title)
    return row_to_task(row)


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, update: TaskUpdate):
    existing = repository.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    new_title = existing["title"]
    new_done = existing["done"]

    if update.title is not None:
        if not update.title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        new_title = update.title

    if update.done is not None:
        new_done = update.done

    row = repository.update_task(task_id, new_title, new_done)
    return row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    existing = repository.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    repository.delete_task(task_id)