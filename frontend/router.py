import os
from urllib.parse import unquote, parse_qs
from wsgiref.simple_server import make_server
import jinja2
import httpx


API_URL = "http://localhost:8001"

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)

# Простейшее хранилище для текущего пользователя (в реальном приложении использовать cookies/sessions)
current_user = {"id": None, "username": None, "email": None}

def render_template(name: str, **context) -> bytes:
    # Всегда добавляем current_user в контекст
    context['user'] = current_user if current_user["id"] else None
    template = env.get_template(name)
    return template.render(**context).encode("utf-8")

def not_found(start_response):
    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]

def redirect(start_response, location):
    start_response("302 Found", [("Location", location)])
    return [b""]

def get_post_data(environ):
    """Читает POST данные из WSGI environ"""
    try:
        content_length = int(environ.get("CONTENT_LENGTH", 0))
    except ValueError:
        content_length = 0
    
    if content_length > 0:
        body = environ["wsgi.input"].read(content_length).decode("utf-8")
        return parse_qs(body)
    return {}

def application(environ, start_response):
    path = unquote(environ.get("PATH_INFO", "/")) or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # === Главная страница ===
    if method == "GET" and path in ("/", "/index"):
        if current_user["id"]:
            # Получаем заметки пользователя через httpx
            try:
                with httpx.Client() as client:
                    response = client.get(f"{API_URL}/get_all_notes/{current_user['id']}")
                    notes = response.json() if response.status_code == 200 else []
                    
                body = render_template("index.html", title="Главная", users=[{
                    "name": current_user["username"],
                    "email": current_user["email"],
                    "notes_count": len(notes)
                }])
            except Exception as e:
                body = render_template("index.html", title="Главная", users=[])
        else:
            body = render_template("index.html", title="Главная", users=[])
        
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    # === Регистрация ===
    if method == "GET" and path == "/auth/register":
        body = render_template("auth/register.html")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    
    if method == "POST" and path == "/auth/register":
        data = get_post_data(environ)
        try:
            with httpx.Client() as client:
                response = client.post(f"{API_URL}/register", json={
                    "username": data.get("name", [""])[0],
                    "email": data.get("email", [""])[0],
                    "password": data.get("password", [""])[0],
                    "is_admin": False
                })
                if response.status_code == 200:
                    return redirect(start_response, "/auth/login")
        except Exception as e:
            pass
        
        body = render_template("auth/register.html")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    # === Вход ===
    if method == "GET" and path == "/auth/login":
        body = render_template("auth/login.html")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    
    if method == "POST" and path == "/auth/login":
        data = get_post_data(environ)
        try:
            with httpx.Client() as client:
                response = client.post(f"{API_URL}/login", json={
                    "email": data.get("email", [""])[0],
                    "password": data.get("password", [""])[0]
                })
                if response.status_code == 200:
                    result = response.json()
                    user_data = result.get("user", {})
                    current_user["id"] = user_data.get("id")
                    current_user["username"] = user_data.get("username")
                    current_user["email"] = user_data.get("email")
                    return redirect(start_response, "/notes")
        except Exception as e:
            pass
        
        body = render_template("auth/login.html")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    # === Выход ===
    if method == "GET" and path == "/auth/logout":
        current_user["id"] = None
        current_user["username"] = None
        current_user["email"] = None
        return redirect(start_response, "/")

    # === Список заметок ===
    if method == "GET" and path == "/notes":
        if not current_user["id"]:
            return redirect(start_response, "/auth/login")
        
        # Получаем параметры поиска из query string
        query_string = environ.get("QUERY_STRING", "")
        params = parse_qs(query_string)
        search_query = params.get("query", [""])[0]
        search_tag = params.get("tag", [""])[0]
        
        try:
            with httpx.Client() as client:
                # Используем новый эндпоинт для поиска с параметрами
                response = client.get(
                    f"{API_URL}/search_notes/{current_user['id']}",
                    params={"query": search_query, "tag": search_tag}
                )
                notes_data = response.json() if response.status_code == 200 else []
                
                notes = []
                for note in notes_data:
                    notes.append({
                        "id": note["id"],
                        "title": note["title"],
                        "updated_at": note["date_modified"] or note["date_created"],
                        "tags": note["tags"]
                    })
                
            body = render_template("notes/list.html", notes=notes, query=search_query, tag=search_tag)
        except Exception as e:
            body = render_template("notes/list.html", notes=[], query=search_query, tag=search_tag)
        
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    # === Создание заметки ===
    if method == "GET" and path == "/notes/new":
        if not current_user["id"]:
            return redirect(start_response, "/auth/login")
        
        body = render_template("notes/form.html", note=None, action="/notes/new")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    
    if method == "POST" and path == "/notes/new":
        if not current_user["id"]:
            return redirect(start_response, "/auth/login")
        
        data = get_post_data(environ)
        try:
            with httpx.Client() as client:
                response = client.post(f"{API_URL}/add_note", json={
                    "title": data.get("title", [""])[0],
                    "content": data.get("content", [""])[0],
                    "user_id": current_user["id"],
                    "tags": data.get("tags", [""])[0]
                })
                if response.status_code == 200:
                    return redirect(start_response, "/notes")
        except Exception as e:
            pass
        
        return redirect(start_response, "/notes")

    # === Просмотр заметки ===
    if method == "GET" and path.startswith("/notes/") and path.count("/") == 2:
        if not current_user["id"]:
            return redirect(start_response, "/auth/login")
        
        note_id = path.split("/")[-1]
        if note_id == "new":
            return not_found(start_response)
        
        try:
            with httpx.Client() as client:
                response = client.get(f"{API_URL}/get_note/{note_id}")
                if response.status_code == 200:
                    note_data = response.json()
                    note = {
                        "id": note_data["id"],
                        "title": note_data["title"],
                        "content": note_data["content"],
                        "created_at": note_data["date_created"],
                        "updated_at": note_data["date_modified"] or note_data["date_created"],
                        "tags": note_data["tags"]
                    }
                    body = render_template("notes/detail.html", note=note)
                    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                    return [body]
        except Exception as e:
            pass
        
        return not_found(start_response)

    # === Редактирование заметки ===
    if method == "GET" and path.endswith("/edit"):
        if not current_user["id"]:
            return redirect(start_response, "/auth/login")
        
        note_id = path.split("/")[-2]
        try:
            with httpx.Client() as client:
                response = client.get(f"{API_URL}/get_note/{note_id}")
                if response.status_code == 200:
                    note_data = response.json()
                    note = {
                        "id": note_data["id"],
                        "title": note_data["title"],
                        "content": note_data["content"],
                        "tags": note_data["tags"]
                    }
                    body = render_template("notes/form.html", note=note, action=f"/notes/{note_id}/edit")
                    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                    return [body]
        except Exception as e:
            pass
        
        return not_found(start_response)
    
    if method == "POST" and path.endswith("/edit"):
        if not current_user["id"]:
            return redirect(start_response, "/auth/login")
        
        note_id = path.split("/")[-2]
        data = get_post_data(environ)
        try:
            with httpx.Client() as client:
                response = client.put(f"{API_URL}/update_note", json={
                    "id": int(note_id),
                    "title": data.get("title", [""])[0],
                    "content": data.get("content", [""])[0],
                    "user_id": current_user["id"],
                    "tags": data.get("tags", [""])[0]
                })
                if response.status_code == 200:
                    return redirect(start_response, f"/notes/{note_id}")
        except Exception as e:
            pass
        
        return redirect(start_response, "/notes")

    # === Удаление заметки ===
    if method == "POST" and path.endswith("/delete"):
        if not current_user["id"]:
            return redirect(start_response, "/auth/login")
        
        note_id = path.split("/")[-2]
        try:
            with httpx.Client() as client:
                response = client.delete(f"{API_URL}/delete_note/{note_id}")
                if response.status_code == 200:
                    return redirect(start_response, "/notes")
        except Exception as e:
            pass
        
        return redirect(start_response, "/notes")

    return not_found(start_response)

if __name__ == "__main__":
    port = 8000
    with make_server("0.0.0.0", port, application) as server:
        print(f"Frontend serving on http://0.0.0.0:{port}")
        print(f"API server should be running on {API_URL}")
        server.serve_forever()