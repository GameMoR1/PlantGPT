import sqlite3
import threading
import os
from pathlib import Path

DB_PATH = Path.home() / "PlantGPT" / "DB" / "plantuml_schemes.db"

class Database:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.create_table()

    def create_table(self):
        with self.lock:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS schemes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    code TEXT,
                    image_path TEXT,
                    image_data BLOB
                )
            ''')
            self.conn.commit()

    def add_scheme(self, filename, code, image_path):
        with self.lock:
            image_data = None
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()
            except Exception:
                pass
            self.cursor.execute('''
                INSERT OR REPLACE INTO schemes (filename, code, image_path, image_data)
                VALUES (?, ?, ?, ?)
            ''', (filename, code, image_path, image_data))
            self.conn.commit()

    def get_all_schemes(self):
        with self.lock:
            self.cursor.execute('SELECT id, filename FROM schemes ORDER BY id DESC')
            return self.cursor.fetchall()

    def get_scheme_by_id(self, scheme_id):
        with self.lock:
            self.cursor.execute('SELECT filename, code, image_path, image_data FROM schemes WHERE id=?', (scheme_id,))
            return self.cursor.fetchone()

    def delete_scheme_by_id(self, scheme_id):
        with self.lock:
            self.cursor.execute('SELECT image_path FROM schemes WHERE id=?', (scheme_id,))
            row = self.cursor.fetchone()
            if row:
                image_path = row[0]
                try:
                    if image_path and os.path.isfile(image_path):
                        os.remove(image_path)
                except Exception:
                    pass
            self.cursor.execute('DELETE FROM schemes WHERE id=?', (scheme_id,))
            self.conn.commit()

    def close(self):
        with self.lock:
            self.conn.close()
