import os
import re
import sqlite3
import time
import toml
from pathlib import Path
from typing import Any

CONTENT_REGEX_DEFAULT = r".*\.md$"

def stat_modified_time(path: Path):
    """Returns the last modified time of the given path."""
    modified_time = os.path.getmtime(path)
    return int(modified_time)

class FileCache:
    """A class for interacting with the SQLite cache."""
    def __init__(self, path: Path):
        self.path = path
        self.conn = self.create_db(self.path)

    @staticmethod
    def create_db(path: Path):
        """Create a new database or connect to an existing one."""

        if not path.exists():
            conn = sqlite3.connect(path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    last_edit_time INTEGER
                )
                """
            )
            conn.commit()
            conn.close()

        conn = sqlite3.connect(path)
        return conn

    def get_edit_time(self, path: Path):
        """Get the last edit time of a file from the database."""
        query = "SELECT last_edit_time FROM files WHERE path = ?"
        cursor = self.conn.cursor()
        cursor.execute(query, (path,))

        result = cursor.fetchone()
        return result[0] if result else 0

    def reset_edit_time(self, path: Path):
        """Reset the last edit time and hash of a file in the database."""
        query = """
        INSERT OR REPLACE INTO files (path, last_edit_time)
        VALUES (?, ?)
        """
        last_edit_time = stat_modified_time(path)

        cursor = self.conn.cursor()
        cursor.execute(query, (path, last_edit_time))
        self.conn.commit()

    def close(self):
        """Close the connection to the database."""
        self.conn.close()

def load_config() -> dict[str, Any]:
    """Load the configuration from a TOML file."""
    config_folder_path = Path.home() / ".vectrekker"
    config_folder_path.mkdir(exist_ok=True)

    config_file = config_folder_path / "config.toml"
    config_file.touch(exist_ok=True)

    with open(config_file, 'r') as f:
        config_file_contents = f.read()

    config = toml.loads(config_file_contents)
    return config

def main():
    config = load_config()
    content_regex = re.compile(config.get('content_regex', CONTENT_REGEX_DEFAULT))

    candidate_files = []

    for root, _, files in os.walk(config['content_folder']):
        for f in files:
            if content_regex.match(f):
                candidate_files.append(os.path.join(root, f))

    conn = FileCache(Path.home() / ".vectrekker" / "cache.db")
    for entry in candidate_files:
        print(entry)
        last_edit_time = conn.get_edit_time(entry)
        current_edit_time = stat_modified_time(entry)

        print(last_edit_time, current_edit_time)

        if current_edit_time > last_edit_time:
            print(f"File has changed: {entry}")

            # TODO: Tokenize the file and submit embedding to vector store

            conn.reset_edit_time(entry)

if __name__ == "__main__":
    main()
