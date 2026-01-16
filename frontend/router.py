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
        # Получаем заметки пользователей через httpx
        users = []
        try:
            with httpx.Client() as client:
                response = client.get(f"{API_URL}/users/summary")
                users = response.json() if response.status_code == 200 else []
        except Exception:
            users = []

        body = render_template("index.html", title="Главная", users=users, user=current_user)
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
                    current_user["is_admin"] = bool(user_data.get("is_admin", 0))
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
        current_user["is_admin"] = None
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
    if method == "GET" and path.startswith("/notes/") and path.endswith("/edit") and path.count("/") == 3:
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
    
    if method == "POST" and path.startswith("/notes/") and path.endswith("/edit") and path.count("/") == 3:
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
    if method == "POST" and path.startswith("/notes/") and path.endswith("/delete") and path.count("/") == 3:
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
    # ===Админ===
    if method == "GET" and path == "/admin/users":
        if not current_user["id"] or not current_user.get("is_admin"):
            start_response("302 Found", [("Location", "/auth/login")])
            return [b""]

        with httpx.Client() as client:
            r = client.get(f"{API_URL}/admin/users", headers={"X-User-Id": str(current_user["id"])})
            users = r.json() if r.status_code == 200 else []

        body = render_template("admin_users.html", title="Admin Users", users=users)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    if method == "POST" and path.startswith("/admin/users/") and path.endswith("/delete"):
        if not current_user["id"] or not current_user.get("is_admin"):
            start_response("302 Found", [("Location", "/auth/login")])
            return [b""]

        user_id = int(path.split("/")[3])
        with httpx.Client() as client:
            client.delete(f"{API_URL}/admin/users/{user_id}", headers={"X-User-Id": str(current_user["id"])})

        start_response("302 Found", [("Location", "/admin/users")])
        return [b""]
    if method == "GET" and path == "/admin/notes":
        if not current_user["id"] or not current_user.get("is_admin"):
            start_response("302 Found", [("Location", "/auth/login")])
            return [b""]

        with httpx.Client() as client:
            r = client.get(f"{API_URL}/admin/notes", headers={"X-User-Id": str(current_user["id"])})
            notes = r.json() if r.status_code == 200 else []

        body = render_template("admin_notes.html", title="Admin Notes", notes=notes)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    if method == "POST" and path.startswith("/admin/notes/") and path.endswith("/delete"):
        if not current_user["id"] or not current_user.get("is_admin"):
            start_response("302 Found", [("Location", "/auth/login")])
            return [b""]

        note_id = int(path.split("/")[3])
        with httpx.Client() as client:
            client.delete(f"{API_URL}/admin/notes/{note_id}", headers={"X-User-Id": str(current_user["id"])})

        start_response("302 Found", [("Location", "/admin/notes")])
        return [b""]
    if method == "GET" and path.startswith("/admin/notes/") and path.endswith("/edit"):
        if not current_user["id"] or not current_user.get("is_admin"):
            return redirect(start_response, "/auth/login")

        note_id = int(path.split("/")[3])

        with httpx.Client() as client:
            r = client.get(f"{API_URL}/get_note/{note_id}")
            if r.status_code != 200:
                return not_found(start_response)
            note_data = r.json()

        body = render_template(
            "admin_note_form.html",
            title="Admin Edit Note",
            note={"id": note_data["id"], "title": note_data["title"], "content": note_data["content"],
                  "tags": note_data["tags"]},
            action=f"/admin/notes/{note_id}/edit"
        )
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    if method == "POST" and path.startswith("/admin/notes/") and path.endswith("/edit"):
        if not current_user["id"] or not current_user.get("is_admin"):
            return redirect(start_response, "/auth/login")

        note_id = int(path.split("/")[3])
        data = get_post_data(environ)

        with httpx.Client() as client:
            client.put(
                f"{API_URL}/admin/notes/{note_id}",
                headers={"X-User-Id": str(current_user["id"])},
                json={
                    "title": data.get("title", [""])[0],
                    "content": data.get("content", [""])[0],
                    "tags": data.get("tags", [""])[0],
                },
            )

        return redirect(start_response, "/admin/notes")
    if method == "GET" and path.startswith("/admin/users/") and path.endswith("/notes"):
        if not current_user.get("id") or not current_user.get("is_admin"):
            return redirect(start_response, "/auth/login")

        user_id = int(path.split("/")[3])

        with httpx.Client() as client:
            # заметки выбранного пользователя
            r_notes = client.get(f"{API_URL}/get_all_notes/{user_id}")
            notes = r_notes.json() if r_notes.status_code == 200 else []

            # данные пользователя (берём из админ списка)
            r_users = client.get(
                f"{API_URL}/admin/users",
                headers={"X-User-Id": str(current_user["id"])}
            )
            users = r_users.json() if r_users.status_code == 200 else []

        selected = next((u for u in users if int(u.get("id", -1)) == user_id), None)
        if not selected:
            return not_found(start_response)

        body = render_template(
            "admin_user_notes.html",
            title="Admin User Notes",
            user=selected,
            notes=notes,
            user_nav=current_user
        )
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    if method == "GET" and path.startswith("/admin/users/") and path.endswith("/edit"):
        if not current_user.get("id") or not current_user.get("is_admin"):
            return redirect(start_response, "/auth/login")

        user_id = int(path.split("/")[3])

        with httpx.Client() as client:
            r = client.get(
                f"{API_URL}/admin/users",
                headers={"X-User-Id": str(current_user["id"])}
            )
            users = r.json() if r.status_code == 200 else []

        u = next((x for x in users if int(x.get("id", -1)) == user_id), None)
        if not u:
            return not_found(start_response)

        body = render_template(
            "admin_user_form.html",
            title="Admin Edit User",
            u=u,
            action=f"/admin/users/{user_id}/edit",
            user=current_user
        )
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    if method == "POST" and path.startswith("/admin/users/") and path.endswith("/edit"):
        if not current_user.get("id") or not current_user.get("is_admin"):
            return redirect(start_response, "/auth/login")

        user_id = int(path.split("/")[3])
        form = get_post_data(environ)

        payload = {
            "username": form.get("username", [""])[0],
            "email": form.get("email", [""])[0],
            "password": form.get("password", [""])[0],
            "is_admin": int(form.get("is_admin", ["0"])[0]),
        }

        with httpx.Client() as client:
            client.put(
                f"{API_URL}/admin/users/{user_id}",
                headers={"X-User-Id": str(current_user["id"])},
                json=payload
            )

        return redirect(start_response, "/")
    if method == "GET" and path == "/me/edit":
        if not current_user.get("id"):
            return redirect(start_response, "/auth/login")

        # берём актуальные данные с API
        with httpx.Client() as client:
            r = client.get(f"{API_URL}/me", headers={"X-User-Id": str(current_user["id"])})
            if r.status_code != 200:
                return not_found(start_response)
            me = r.json()

        body = render_template("me_form.html", title="Профиль", me=me, user=current_user)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    if method == "POST" and path == "/me/edit":
        if not current_user.get("id"):
            return redirect(start_response, "/auth/login")

        form = get_post_data(environ)
        payload = {
            "username": form.get("username", [""])[0],
            "email": form.get("email", [""])[0],
            "password": form.get("password", [""])[0],
        }

        with httpx.Client() as client:
            r = client.put(f"{API_URL}/me", headers={"X-User-Id": str(current_user["id"])}, json=payload)
            if r.status_code == 200:
                # обновим current_user
                u = r.json()["user"]
                current_user["username"] = u["username"]
                current_user["email"] = u["email"]
                current_user["is_admin"] = bool(u.get("is_admin", 0))

        return redirect(start_response, "/")
    if method == "POST" and path == "/me/delete":
        if not current_user.get("id"):
            return redirect(start_response, "/auth/login")

        with httpx.Client() as client:
            client.delete(f"{API_URL}/me", headers={"X-User-Id": str(current_user["id"])})

        # logout локально
        current_user["id"] = None
        current_user["username"] = None
        current_user["email"] = None
        current_user["is_admin"] = False

        return redirect(start_response, "/auth/login")
    return not_found(start_response)




if __name__ == "__main__":
    port = 8000
    with make_server("0.0.0.0", port, application) as server:
        print(f"Frontend serving on http://0.0.0.0:{port}")
        print(f"API server should be running on {API_URL}")
        server.serve_forever()