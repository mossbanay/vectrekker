import os
import re
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Iterable, Optional, Type

import openai
import pinecone
import tiktoken
import toml
import typer
from pydantic import Field
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    content_folder: str
    content_regex: str = r".*\.md$"
    dimension_size: int = 1536
    metric: str = "cosine"


class PineconeConfig(BaseSettings):
    api_key: str = Field(..., env="PINECONE_API_KEY")
    environment: str = Field(..., env="PINECONE_ENVIRONMENT")
    index_name: str = Field(default="vectrekker", env="PINECONE_INDEX")


class OpenAIConfig(BaseSettings):
    api_key: str = Field(..., env="OPENAI_API_KEY")


class Config(BaseSettings):
    base: BaseConfig
    pinecone: PineconeConfig
    openai: OpenAIConfig


def load_config() -> Config:
    """Load the configuration from a TOML file."""
    config_folder_path = Path.home() / ".vectrekker"
    config_folder_path.mkdir(exist_ok=True)

    config_file = config_folder_path / "config.toml"
    config_file.touch(exist_ok=True)

    with config_file.open("r") as f:
        config_dict = toml.load(f)

    return Config(**config_dict)


def stat_modified_time(path: Path):
    """Returns the last modified time of the given path."""
    modified_time = os.path.getmtime(path)
    return int(modified_time)


def walk(path: Path) -> Iterable[Path]:
    """Recursively walk a path and yield all files."""
    for p in Path(path).iterdir():
        if p.is_dir():
            yield from walk(p)
            continue
        yield p.resolve()


class FileCache:
    """A simple file cache for storing the last edit time of a file."""

    def __init__(self, path: Path):
        self.path = path
        self.conn = None

    def __enter__(self):
        self.conn = self.create_db(self.path)
        return self

    def __exit__(
        self,
        _exc_type: Optional[Type[BaseException]],
        _exc: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ):
        self.conn.close()
        self.conn = None

    @staticmethod
    def create_db(path: Path):
        """Create a new database or connect to an existing one."""
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
        return conn

    def get_edit_time(self, path: Path):
        """Get the last modified time for a file or 0 if unknown."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_edit_time FROM files WHERE path = ?", (str(path),))
        result = cursor.fetchone()
        return result[0] or 0

    def reset_edit_time(self, path: Path):
        """Reset the last edit time and hash of a file in the database."""
        query = """
        INSERT OR REPLACE INTO files (path, last_edit_time)
        VALUES (?, ?)
        """
        last_edit_time = stat_modified_time(path)

        cursor = self.conn.cursor()
        cursor.execute(query, (str(path), last_edit_time))
        self.conn.commit()


def main(dry_run: bool = typer.Option(False)):
    """VecTrekker

    VecTrekker is a simple utility used to index text content on disk, embed it
    into vectors and upsert it to a vector store for usage with LLMs.
    """

    config = load_config()
    content_regex = re.compile(config.base.content_regex)
    files_to_reindex: list[Path] = []

    with FileCache(Path.home() / ".vectrekker" / "cache.db") as conn:
        for p in walk(Path(config.base.content_folder)):
            if not content_regex.match(str(p)):
                continue

            last_edit_time = conn.get_edit_time(p)
            current_edit_time = stat_modified_time(p)

            if current_edit_time > last_edit_time:
                files_to_reindex.append(p)

    print(f"{len(files_to_reindex)} file(s) have changed")

    if dry_run:
        print("Dry run complete, exiting")

    pinecone.init(
        api_key=config.pinecone.api_key, environment=config.pinecone.environment
    )

    if config.pinecone.index_name not in pinecone.list_indexes():
        pinecone.create_index(
            name=config.pinecone.index_name,
            dimension=config.base.dimension_size,
            metric=config.base.metric,
        )

    index = pinecone.Index(index_name=config.pinecone.index_name)
    encoder = tiktoken.get_encoding("cl100k_base")

    for entry in files_to_reindex:
        file_contents = entry.read_text()
        toks = encoder.encode(file_contents)

        # TODO: Currently we assume that all documents are less than 8191 tokens
        assert len(toks) < 8191, "Document is too long, splitting not yet supported"

        os.environ["OPENAI_API_KEY"] = config.openai.api_key
        embd = openai.Embedding.create(
            input=file_contents, model="text-embedding-ada-002"
        )["data"][0]["embedding"]

        index.upsert(vectors=[(str(entry), embd, {})])

        with FileCache(Path.home() / ".vectrekker" / "cache.db") as conn:
            conn.reset_edit_time(entry)


if __name__ == "__main__":
    typer.run(main)
