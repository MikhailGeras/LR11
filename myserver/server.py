from fastapi import FastAPI
import uvicorn
import json
from models import User, UserLogin, Note
from controllers.db_controller import DatabaseController


db_controller = DatabaseController()

app = FastAPI()


@app.get("/register")
def register_handler(user_data: User):
    db_controller.insert_users([user_data])
    return {"status": "Регистрация прошла успешно!"}

@app.get("/login")
def login_handler(user_credentials: UserLogin):
    row = db_controller.login_user(user_credentials.email, user_credentials.password)
    if not row:
        return {"status": "Ошибка входа"}, 401  # Unauthorized
    return {"status": "Вход прошел успешно!", "user": list(row)}


@app.post("/add_note")
def add_note_handler(note_data: Note):
    res = db_controller.insert_note(note_data)
    return {"status": "Заметка успешно добавлена!"}

@app.get("/get_all_notes")
def get_notes_handler():
    notes = db_controller.read_notes_by_user()
    return notes

@app.get("/get_note")
def get_note_handler(note_data: Note):
    note = db_controller.read_note_by_id(note_data.id)
    return list(note)

@app.put("/update_note")
def update_note_handler(note_data: Note):
    is_success = db_controller.update_note(note_data.id, note_data.title, note_data.content, note_data.tags)
    if is_success:
        return {"status": "Заметка успешно обновлена!"}
    return {"status": "Ошибка обновления заметки"}, 400

@app.get("/delete_note")
def delete_note_handler(note_data: Note):
    is_success = db_controller.delete_note(note_data.id)
    if is_success:
        return {"status": "Заметка успешно удалена!"}
    return {"status": "Ошибка удаления заметки"}, 400

@app.get("/search_notes")
def search_notes_handler():
    db_controller.search_notes_by_title()
    return {"status": "Поиск завершен" }

@app.get("/add_tags")
def add_tags_handler():
    db_controller.add_tags_to_note()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)