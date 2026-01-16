from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from models.user import User, UserLogin
from models.note import Note
from controllers.db_controller import DatabaseController


db_controller = DatabaseController()

app = FastAPI()

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {"status": "Вход прошел успешно!", "user": {"id": row[0], "username": row[1], "email": row[2]}}


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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)