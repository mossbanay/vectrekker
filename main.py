import os
import re
import sqlite3
import time
import toml
from pathlib import Path

CONTENT_REGEX_DEFAULT = r".*\.md$"

def default_content_regex():
    return CONTENT_REGEX_DEFAULT

def stat_modified_time(path):
    modified_time = os.path.getmtime(path)
    return int(modified_time)

class Config:
    def __init__(self, content_folder, content_regex=default_content_regex()):
        self.content_folder = content_folder
        self.content_regex = content_regex

class FileCache:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        if not os.path.exists(path):
            self.conn.execute(
                """
                CREATE TABLE files (
                    path TEXT PRIMARY KEY,
                    last_edit_time INTEGER,
                    hash TEXT
                )
                """
            )

    def get_edit_time(self, path):
        query = "SELECT last_edit_time FROM files WHERE path = ?"
        cursor = self.conn.cursor()
        cursor.execute(query, (path,))

        result = cursor.fetchone()
        return result[0] if result else 0

    def reset_edit_time(self, path):
        query = """
        INSERT OR REPLACE INTO files (path, last_edit_time, hash)
        VALUES (?, ?, ?)
        """
        cursor = self.conn.cursor()
        last_edit_time = stat_modified_time(path)
        hash = "TODO"
        cursor.execute(query, (path, last_edit_time, hash))

        self.conn.commit()

def load_config():
    config_folder_path = "/Users/moss/.vectrekker"
    os.makedirs(config_folder_path, exist_ok=True)

    config_file = os.path.join(config_folder_path, "config.toml")
    if not os.path.exists(config_file):
        with open(config_file, 'w') as f:
            pass

    with open(config_file, 'r') as f:
        config_file_contents = f.read()

    config = toml.loads(config_file_contents)
    return Config(config['content_folder'], config.get('content_regex', default_content_regex()))

def main():
    config = load_config()
    content_regex = re.compile(config.content_regex)

    candidate_files = []

    for dirpath, dirnames, filenames in os.walk(config.content_folder):
        for filename in filenames:
            if content_regex.match(filename):
                candidate_files.append(os.path.join(dirpath, filename))

    conn = FileCache("/Users/moss/.vectrekker/cache.db")
    for entry in candidate_files:
        print(entry)
        last_edit_time = conn.get_edit_time(entry)
        current_edit_time = stat_modified_time(entry)

        print(last_edit_time, current_edit_time)

        if current_edit_time > last_edit_time:
            print("File has changed:", entry)

            # TODO: Tokenize the file and submit embedding to vector store

            conn.reset_edit_time(entry)

if __name__ == "__main__":
    main()
