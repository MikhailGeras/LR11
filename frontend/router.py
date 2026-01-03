import os
from urllib.parse import unquote
from wsgiref.simple_server import make_server
import jinja2

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)

def render_template(name: str, **context) -> bytes:
    template = env.get_template(name)
    return template.render(**context).encode("utf-8")

def not_found(start_response):
    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]

def app(environ, start_response):
    path = unquote(environ.get("PATH_INFO", "/")) or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # Простейший роутер по пути и методу
    if method == "GET" and path in ("/", "/index"):
        body = render_template("index.html", title="Главная")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    if method == "GET" and path == "/about":
        body = render_template("about.html", title="О нас")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    # Можно добавить динамический сегмент: /hello/<name>
    if method == "GET" and path.startswith("/hello/"):
        name = path.removeprefix("/hello/") or "Гость"
        body = render_template("hello.html", name=name, title="Привет")
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    return not_found(start_response)

if __name__ == "__main__":
    port = 8000
    with make_server("0.0.0.0", port, app) as server:
        print(f"Serving on http://0.0.0.0:{port}")
        server.serve_forever()