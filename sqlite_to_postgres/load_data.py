import logging
import os
import sqlite3
from contextlib import closing
from dataclasses import astuple, dataclass, fields
from typing import Generator

import psycopg
from dotenv import load_dotenv
from psycopg import ClientCursor
from psycopg.rows import dict_row

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500

DSL = {
    "dbname": os.environ.get("POSTGRES_DB", "movies_database"),
    "user": os.environ.get("POSTGRES_USER", "app"),
    "password": os.environ.get("POSTGRES_PASSWORD", "123qwe"),
    "host": os.environ.get("SQL_HOST", "127.0.0.1"),
    "port": os.environ.get("SQL_PORT", 5432),
}


@dataclass
class Genre:
    id: str
    name: str
    description: str
    created: str
    modified: str


@dataclass
class Person:
    id: str
    full_name: str
    created: str
    modified: str


@dataclass
class Filmwork:
    id: str
    title: str
    description: str
    creation_date: str
    rating: float
    type: str
    created: str
    modified: str


@dataclass
class GenreFilmwork:
    id: str
    genre_id: str
    film_work_id: str
    created: str


@dataclass
class PersonFilmwork:
    id: str
    person_id: str
    film_work_id: str
    role: str
    created: str


@dataclass
class TableConfig:
    pg_table: str
    model: type
    sqlite_query: str


# Порядок важен из-за внешних ключей: справочники -> фильмы -> связи.
# file_path из SQLite не переносим (в PostgreSQL такого поля нет);
# created_at/updated_at приводим к created/modified алиасами.
TABLES = [
    TableConfig(
        "content.genre",
        Genre,
        "SELECT id, name, description, "
        "created_at AS created, updated_at AS modified FROM genre",
    ),
    TableConfig(
        "content.person",
        Person,
        "SELECT id, full_name, "
        "created_at AS created, updated_at AS modified FROM person",
    ),
    TableConfig(
        "content.film_work",
        Filmwork,
        "SELECT id, title, description, creation_date, rating, type, "
        "created_at AS created, updated_at AS modified FROM film_work",
    ),
    TableConfig(
        "content.genre_film_work",
        GenreFilmwork,
        "SELECT id, genre_id, film_work_id, "
        "created_at AS created FROM genre_film_work",
    ),
    TableConfig(
        "content.person_film_work",
        PersonFilmwork,
        "SELECT id, person_id, film_work_id, role, "
        "created_at AS created FROM person_film_work",
    ),
]


class SQLiteLoader:
    """Читает таблицы SQLite пачками и отдаёт dataclass-модели."""

    def __init__(self, connection: sqlite3.Connection):
        connection.row_factory = sqlite3.Row
        self.connection = connection

    def load(self, config: TableConfig) -> Generator[list, None, None]:
        cursor = self.connection.cursor()
        cursor.execute(config.sqlite_query)
        while True:
            rows = cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break
            yield [config.model(**dict(row)) for row in rows]


class PostgresSaver:
    """Сохраняет пачки в PostgreSQL; повторные id игнорируются."""

    def __init__(self, pg_conn):
        self.pg_conn = pg_conn

    def save(self, config: TableConfig, batch: list) -> None:
        column_names = [field.name for field in fields(config.model)]
        columns = ", ".join(column_names)
        placeholders = ", ".join(["%s"] * len(column_names))
        query = (
            "INSERT INTO {table} ({cols}) VALUES ({vals}) "
            "ON CONFLICT (id) DO NOTHING"
        ).format(table=config.pg_table, cols=columns, vals=placeholders)
        rows = [astuple(item) for item in batch]
        with self.pg_conn.cursor() as cursor:
            cursor.executemany(query, rows)


def load_from_sqlite(connection: sqlite3.Connection, pg_conn) -> None:
    """Основной метод загрузки данных из SQLite в Postgres."""
    loader = SQLiteLoader(connection)
    saver = PostgresSaver(pg_conn)
    for config in TABLES:
        total = 0
        for batch in loader.load(config):
            saver.save(config, batch)
            total += len(batch)
        logger.info("%s: загружено %s записей", config.pg_table, total)
    pg_conn.commit()


def main() -> None:
    try:
        with closing(sqlite3.connect("db.sqlite")) as sqlite_conn:
            with closing(
                psycopg.connect(
                    **DSL,
                    row_factory=dict_row,
                    cursor_factory=ClientCursor,
                ),
            ) as pg_conn:
                load_from_sqlite(sqlite_conn, pg_conn)
    except sqlite3.Error:
        logger.exception("Ошибка чтения из SQLite")
        raise
    except psycopg.Error:
        logger.exception("Ошибка записи в PostgreSQL")
        raise


if __name__ == "__main__":
    main()
