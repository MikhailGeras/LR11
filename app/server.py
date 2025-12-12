from fastapi import FastAPI
import uvicorn


app = FastAPI()

app.mount("static")

@app.get("/register")
def register_handler():
    pass

@app.get("/login")
def login_handler():
    pass

@app.post("/add_note")
def add_note_handler():
    pass

@app.get("/get_all_notes")
def get_notes_handler():
    pass

@app.get("/get_note")
def get_note_handler():
    pass

@app.update("/update_note")
def update_note_handler():
    pass

@app.delete("/delete_note")
def delete_note_handler():
    pass

@app.search("/search_notes")
def search_notes_handler():
    pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)