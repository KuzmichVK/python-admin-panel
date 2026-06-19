"""Проверка целостности переноса SQLite -> PostgreSQL.

Локальный тест (НЕ добавлять в GitHub Actions). Запуск из этой папки,
рядом должен быть db.sqlite (скопировать из sqlite_to_postgres):
    cd user_tests/check_consistency
    pytest
"""
import os
import sqlite3
from contextlib import closing

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

DSL = {
    'dbname': os.environ.get('POSTGRES_DB', 'movies_database'),
    'user': os.environ.get('POSTGRES_USER', 'app'),
    'password': os.environ.get('POSTGRES_PASSWORD', '123qwe'),
    'host': os.environ.get('SQL_HOST', '127.0.0.1'),
    'port': os.environ.get('SQL_PORT', 5432),
}

# таблица SQLite -> (таблица PostgreSQL, колонки SQLite с алиасами под PG)
TABLES = {
    'genre': (
        'content.genre',
        'id, name, description, '
        'created_at AS created, updated_at AS modified',
    ),
    'person': (
        'content.person',
        'id, full_name, created_at AS created, updated_at AS modified',
    ),
    'film_work': (
        'content.film_work',
        'id, title, description, creation_date, rating, type, '
        'created_at AS created, updated_at AS modified',
    ),
    'genre_film_work': (
        'content.genre_film_work',
        'id, genre_id, film_work_id, created_at AS created',
    ),
    'person_film_work': (
        'content.person_film_work',
        'id, person_id, film_work_id, role, created_at AS created',
    ),
}


@pytest.fixture(scope='module')
def connections():
    with closing(sqlite3.connect('db.sqlite')) as sqlite_conn:
        sqlite_conn.row_factory = sqlite3.Row
        with closing(
            psycopg.connect(**DSL, row_factory=dict_row),
        ) as pg_conn:
            yield sqlite_conn, pg_conn


@pytest.mark.parametrize('sqlite_table', list(TABLES))
def test_row_count(connections, sqlite_table):
    sqlite_conn, pg_conn = connections
    pg_table = TABLES[sqlite_table][0]

    sqlite_count = sqlite_conn.execute(
        'SELECT count(*) FROM {0}'.format(sqlite_table),
    ).fetchone()[0]
    with pg_conn.cursor() as cur:
        cur.execute('SELECT count(*) AS c FROM {0}'.format(pg_table))
        pg_count = cur.fetchone()['c']

    assert sqlite_count == pg_count


@pytest.mark.parametrize('sqlite_table', list(TABLES))
def test_row_content(connections, sqlite_table):
    sqlite_conn, pg_conn = connections
    pg_table, columns = TABLES[sqlite_table]

    sqlite_rows = {
        row['id']: dict(row)
        for row in sqlite_conn.execute(
            'SELECT {0} FROM {1}'.format(columns, sqlite_table),
        ).fetchall()
    }
    with pg_conn.cursor() as cur:
        cur.execute('SELECT * FROM {0}'.format(pg_table))
        pg_rows = {str(row['id']): row for row in cur.fetchall()}

    assert set(sqlite_rows) == set(pg_rows)
    for row_id, sqlite_row in sqlite_rows.items():
        pg_row = pg_rows[row_id]
        for key, value in sqlite_row.items():
            assert str(value) == str(pg_row[key])
