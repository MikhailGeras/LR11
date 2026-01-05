import sqlite3
from models.user import User

class DatabaseController:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self.create_tables()

    def connect(self):
        """Создает и возвращает соединение с базой данных SQLite."""
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        is_admin BOOLEAN NOT NULL
                    );
                    """)

        cur.execute("""
                        CREATE TABLE IF NOT EXISTS notes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            content TEXT,
                            user_id INTEGER NOT NULL,
                            date_created TEXT DEFAULT CURRENT_TIMESTAMP,
                            date_modified TEXT DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            tags TEXT                                
                        );
                        """)

        cur.execute("""
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE
                    );
                    """)

        cur.execute("""
                    CREATE TABLE IF NOT EXISTS tag_for_note (
                        tag_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        note_id INTEGER NOT NULL,
                        PRIMARY KEY (tag_id, user_id, note_id),
                        FOREIGN KEY (tag_id) REFERENCES tags(id)
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (note_id) REFERENCES notes(id)
                    );
                    """)


        conn.commit()
        conn.close()
        print("✔ Таблицы созданы")

    def insert_users(self, users_data):
        """
        Добавляет пользователей в базу данных
        на вход:
        [тип User]
        """
        conn = self.connect()
        cur = conn.cursor()

        for u in users_data:
            cur.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                (u.username, u.email, u.password, u.is_admin)
            )

        conn.commit()
        conn.close()
        print("✔ Пользователи добавлены")

    def insert_note(self, note):
        """
        Добавляет заметку в базу данных

        на вход:
        объект типа Note
        """
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("INSERT INTO notes (title, content, user_id, date_created, date_modified, tags)VALUES (?, ?, ?, ?, ?, ?)", (
            note.title,
            note.content,
            note.user_id,
            note.date_created,
            note.date_modified,
            note.tags
        ))

        conn.commit()
        conn.close()
        print("✔ Заметка добавлена")

    def insert_tag(self, tag):
        """
        Добавляет тэги в базу данных
        на вход:
        [тип str]
        """
        conn = self.connect()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO tags (name) VALUES (?)",
            (tag,)
        )

        conn.commit()
        conn.close()
        print("✔ Тэг добавлен")

    def insert_tags_id_for_note_by_user(self, tags_id, user_id, note_id):
        conn = self.connect()
        cur = conn.cursor()

        for tag in tags_id:
            cur.execute(
                "INSERT INTO tag_for_note (tag_id, user_id, note_id) VALUES (?, ?, ?)",
                (tag, user_id, note_id)
            )

        conn.commit()
        conn.close()
        print("Свясь тега, пользователя и подписки создана")

    def read_all_users(self):
        """Возвращает список всех пользователей в базе в виде словаря."""
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("SELECT id, username, email, password, is_admin FROM users")
        rows = cur.fetchall()
        conn.close()

        return rows


    def read_notes_by_user(self, user_id):
        """
        Находит все заметки по user_id
        :param user_id:
        :return [..., (id, title, content, user_id, date_created, date_modified, tags), ...]:
        """
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("SELECT id, title, content, date_created, date_modified, tags FROM notes WHERE user_id=?",
                    (user_id,))
        rows = cur.fetchall()
        conn.close()
        return rows


    def read_note_by_id(self,id):

        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, date_created, date_modified, tags FROM notes WHERE id=?",
                    (id,))
        row = cur.fetchone()
        conn.close()
        return row


    def read_all_tags_user(self, user_id):
        """Возвращает список всех тегов пользователя в базе в виде словаря."""
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("SELECT tag_id FROM tag_for_note WHERE user_id=?",
                    (user_id,))
        rows = cur.fetchall()
        conn.close()

        return rows


    def login_user(self, email, password):
        """ Возвращает 0 если пользователя нет / если есть - row """
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=?, password=?", (email,password))
        row = cur.fetchone()
        if row is None:
            return 0
        else:
            return row


    def update_note(self, id, title, new_content, tags):
        """Обновляет note и возвращает 1"""
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("UPDATE notes SET title=?, content=?, tags=? WHERE id=?",
                    (title, new_content, tags, id))

        conn.commit()
        conn.close()

        return 1


    def delete_note(self, id):
        """Удаляет note по его id и возвращает 1"""
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return 1

    def search_notes(self, user_id, query="", tag=""):
        """
        Ищет заметки по user_id с фильтрацией по query (в заголовке или содержимом)
        и по тегу
        :param user_id: ID пользователя
        :param query: строка поиска в заголовке или содержимом
        :param tag: тег для фильтрации
        :return: список кортежей (id, title, content, date_created, date_modified, tags)
        """
        conn = self.connect()
        cur = conn.cursor()
        
        sql = "SELECT id, title, content, date_created, date_modified, tags FROM notes WHERE user_id=?"
        params = [user_id]
        
        if query:
            sql += " AND (title LIKE ? OR content LIKE ?)"
            query_param = f"%{query}%"
            params.extend([query_param, query_param])
        
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f"%{tag}%")
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return rows

