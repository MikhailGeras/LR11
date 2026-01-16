import sqlite3

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
                            date_modified TEXT DEFAULT CURRENT_TIMESTAMP,
                            tags TEXT                                
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
    def update_user_self(self, user_id: int, username: str, email: str, password: str):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET username=?, email=?, password=? WHERE id=?",
            (username, email, password, user_id)
        )
        conn.commit()
        conn.close()

    def delete_user_cascade(self, user_id: int):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id=?", (user_id,))
        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def insert_note(self, note):
        """
        Добавляет заметку в базу данных

        на вход:
        объект типа Note
        """
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("INSERT INTO notes (title, content, user_id, tags)VALUES (?, ?, ?, ?)", (
            note.title,
            note.content,
            note.user_id,
            note.tags
        ))

        conn.commit()
        conn.close()
        print("✔ Заметка добавлена")

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


    def login_user(self, email, password):
        """ Возвращает 0 если пользователя нет / если есть - row """
        conn = self.connect()
        cur = conn.cursor()
        sql = "SELECT * FROM users WHERE email=? AND password = ?"
        cur.execute(sql, (email,password))
        row = cur.fetchone()
        if row is None:
            return 0
        else:
            return row


    def update_note(self, id, title, new_content, tags):
        """Обновляет note и возвращает 1"""
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("UPDATE notes SET title=?, content=?, tags=?, date_modified=CURRENT_TIMESTAMP WHERE id=?",
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

    def get_users_summary(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                u.id,
                u.username,
                u.email,
                u.is_admin,
                COUNT(n.id) AS notes_count
            FROM users u
            LEFT JOIN notes n ON n.user_id = u.id
            GROUP BY u.id, u.username, u.email
            ORDER BY u.username
             """)
        rows = cur.fetchall()
        conn.close()

        return [
            {"id": r[0], "name": r[1], "email": r[2], "is_admin": r[3], "notes_count": r[4]}
            for r in rows
        ]
    def get_user_by_id(self, user_id: int):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, is_admin FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row[0], "username": row[1], "email": row[2], "password": row[3], "is_admin": row[4]}
    def admin_list_users(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, is_admin FROM users ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "username": r[1], "email": r[2], "is_admin": r[4]} for r in rows]

    def admin_create_user(self, username: str, email: str, password: str, is_admin: int=0):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, password, is_admin),
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return new_id
    def admin_exists(self)->bool:
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE is_admin=1 LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return row is not None

    def admin_update_user(self, user_id: int, username: str, email: str, password: str, is_admin: int):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET username=?, email=?, password=?, is_admin=? WHERE id=?",
            (username, email, password, is_admin, user_id),
        )
        conn.commit()
        conn.close()

    def admin_delete_user(self, user_id: int):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    def admin_list_notes(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT n.id, n.title, n.content, n.tags, n.date_created, n.date_modified, n.user_id, u.username
            FROM notes n
            JOIN users u ON u.id = n.user_id
            ORDER BY n.date_modified DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "id":r[0], "title": r[1], "content": r[2], "tags": r[3],
                "date_created": r[4], "date_modified": r[5],
                "user_id": r[6], "username": r[7]
            }
            for r in rows
        ]
    def admin_update_note(self, note_id: int, title: str, content: str, tags:str):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE notes
            SET title=?, content=?, tags=?, date_modified=CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title, content, tags, note_id))
        conn.commit()
        conn.close()

    def admin_delete_note(self, note_id: int):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        conn.close()
    def user_exists_by_email(self, email: str) -> bool:
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE email=? LIMIT 1", (email,))
        row = cur.fetchone()
        conn.close()
        return row is not None