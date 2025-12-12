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
                        password TEXT NOT NULL
                        is_admin BOOLEAN NOT NULL
                    );
                    """)

        cur.execute("""
                            CREATE TABLE IF NOT EXISTS notes (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                title TEXT NOT NULL,
                                content TEXT,
                                owner_id INTEGER NOT NULL,
                                date_created TEXT NOT NULL,
                                date_modified TEXT NOT NULL,
                                tags TEXT                                
                            );
                            """)
        conn.commit()
        conn.close()
        print("✔ Таблицы созданы")

    def insert_users(self, users_data):
        """Добавляет пользователей в базу данных."""
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

        cur.execute("""
                                    INSERT INTO notes (title, content, owner_id, date_created, date_modified, tags)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (
            note.title,
            note.content,
            note.owner_id,
            note.date_created,
            note.date_modified,
            note.tags
        ))

        conn.commit()
        conn.close()
        print("✔ Заметка добавлена")