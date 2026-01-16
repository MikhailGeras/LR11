from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional
import uvicorn
from models.user import User, UserLogin
from models.note import Note
from models.admin_user import AdminUser
from controllers.db_controller import DatabaseController


db_controller = DatabaseController()

def ensure_admin_exists():
    admin = AdminUser()
    if not db_controller.user_exists_by_email(admin.email):
        db_controller.admin_create_user(admin.username, admin.email, admin.password, 1)
ensure_admin_exists()

app = FastAPI()

def require_admin(x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")

    try:
        user_id = int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-User-Id must be int")

    user = db_controller.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if int(user["is_admin"]) != 1:
        raise HTTPException(status_code=403, detail="Admin only")

    return user
def require_user(x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    try:
        user_id = int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-User-Id must be int")

    user = db_controller.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

class AdminUserIn(BaseModel):
    username: str
    email: str
    password: str
    is_admin: int = 0

class AdminUserUpdate(BaseModel):
    username: str
    email: str
    password: str
    is_admin: int

class AdminNoteUpdate(BaseModel):
    title: str
    content: str
    tags: str = ""

class MeUpdate(BaseModel):
    username: str
    email: str
    password: str


@app.get("/me")
def me_get(user=Depends(require_user)):
    # пароль не отдаём
    return {"id": user["id"], "username": user["username"], "email": user["email"]}


@app.put("/me")
def me_update(payload: MeUpdate, user=Depends(require_user)):
    db_controller.update_user_self(user["id"], payload.username, payload.email, payload.password)
    updated = db_controller.get_user_by_id(user["id"])
    return {"status": "ok", "user": {"id": updated["id"], "username": updated["username"], "email": updated["email"]}}


@app.delete("/me")
def me_delete(user=Depends(require_user)):
    db_controller.delete_user_cascade(user["id"])
    return {"status": "ok"}


@app.post("/register")
def register_handler(user_data: User):
    db_controller.insert_users([user_data])
    return {"status": "Регистрация прошла успешно!"}

@app.post("/login")
def login_handler(user_credentials: UserLogin):
    row = db_controller.login_user(user_credentials.email, user_credentials.password)
    if not row:
        raise HTTPException(status_code=401, detail="Ошибка входа")
    
    # Неверный пароль!
    if row[3] != user_credentials.password:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    return {"status": "Вход прошел успешно!", "user": {"id": row[0], "username": row[1], "email": row[2], "is_admin": row[4]}}


@app.post("/add_note")
def add_note_handler(note_data: Note):
    res = db_controller.insert_note(note_data)
    return {"status": "Заметка успешно добавлена!"}

@app.get("/users/summary")
def get_users_summary_handler():
    return db_controller.get_users_summary()

@app.get("/get_all_notes/{user_id}")
def get_notes_handler(user_id: int):
    notes = db_controller.read_notes_by_user(user_id)
    result = []
    for note in notes:
        result.append({
            "id": note[0],
            "title": note[1],
            "content": note[2],
            "date_created": note[3],
            "date_modified": note[4],
            "tags": note[5]
        })
    return result

@app.get("/search_notes/{user_id}")
def search_notes_handler(user_id: int, query: str = "", tag: str = ""):
    notes = db_controller.search_notes(user_id, query, tag)
    result = []
    for note in notes:
        result.append({
            "id": note[0],
            "title": note[1],
            "content": note[2],
            "date_created": note[3],
            "date_modified": note[4],
            "tags": note[5]
        })
    return result

@app.get("/get_note/{note_id}")
def get_note_handler(note_id: int):
    note = db_controller.read_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    return {
        "id": note[0],
        "title": note[1],
        "content": note[2],
        "date_created": note[3],
        "date_modified": note[4],
        "tags": note[5]
    }

@app.put("/update_note")
def update_note_handler(note_data: Note):
    is_success = db_controller.update_note(note_data.id, note_data.title, note_data.content, note_data.tags)
    if is_success:
        return {"status": "Заметка успешно обновлена!"}
    raise HTTPException(status_code=400, detail="Ошибка обновления заметки")


@app.delete("/delete_note/{note_id}")
def delete_note_handler(note_id: int):
    is_success = db_controller.delete_note(note_id)
    if is_success:
        return {"status": "Заметка успешно удалена!"}
    raise HTTPException(status_code=400, detail="Ошибка удаления заметки")

@app.get("/admin/users")
def admin_users_list(admin=Depends(require_admin)):
    return db_controller.admin_list_users()


@app.post("/admin/users")
def admin_users_create(payload: AdminUserIn, admin=Depends(require_admin)):
    new_id = db_controller.admin_create_user(payload.username, payload.email, payload.password, payload.is_admin)
    return {"id": new_id}


@app.put("/admin/users/{user_id}")
def admin_users_update(user_id: int, payload: AdminUserUpdate, admin=Depends(require_admin)):
    db_controller.admin_update_user(user_id, payload.username, payload.email, payload.password, payload.is_admin)
    return {"status": "ok"}


@app.delete("/admin/users/{user_id}")
def admin_users_delete(user_id: int, admin=Depends(require_admin)):
    # Минимальная защита: не удалять самого себя
    if admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db_controller.admin_delete_user(user_id)
    return {"status": "ok"}


@app.get("/admin/notes")
def admin_notes_list(admin=Depends(require_admin)):
    return db_controller.admin_list_notes()


@app.put("/admin/notes/{note_id}")
def admin_notes_update(note_id: int, payload: AdminNoteUpdate, admin=Depends(require_admin)):
    db_controller.admin_update_note(note_id, payload.title, payload.content, payload.tags)
    return {"status": "ok"}


@app.delete("/admin/notes/{note_id}")
def admin_notes_delete(note_id: int, admin=Depends(require_admin)):
    db_controller.admin_delete_note(note_id)
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)