# CHANGELOG

Проект «Онлайн-кинотеатр» (python-admin-panel). Три части в трёх ветках,
у каждой свой PR и автотесты GitHub Actions. Решение выверено под тесты
шаблона (conftest, test_ddl, test_models_*, test_admin, test_s2p).

---

## feature/schema-design — Часть 1: архитектура БД

Папка: `schema_design/` — файл `movies_database.ddl`.

- Схема `content`; таблицы `film_work`, `genre`, `person`,
  `genre_film_work`, `person_film_work`. PK — `uuid`.
- Типы под `test_columns_info`: `rating real` (не float!), остальные `text`,
  `creation_date date`, `created/modified timestamp with time zone`.
- FK с `ON DELETE CASCADE` (под `test_foreign_keys`).
- Уникальные индексы под `test_unique_indexes_exist`:
  `genre_film_work (film_work_id, genre_id)`,
  `person_film_work (film_work_id, person_id, role)`.
- Обычный индекс `film_work_creation_date_idx`.
- Расширение `uuid-ossp` НЕ используется (тест это проверяет).
- conftest сам выполняет `DROP SCHEMA content CASCADE` и накатывает DDL.

Линтер и тесты:
```bash
cd schema_design
sqlfluff lint --dialect postgres movies_database.ddl   # при ошибках: sqlfluff fix ...
pytest
```

---

## feature/movies-admin — Часть 2: панель администратора

Папка: `movies_admin/`.

- `django-admin startproject config .` + `startapp movies`.
- `config/settings.py` разбит: подключение БД в
  `config/components/database.py` (django-split-settings).
- Подключение через `.env` (python-dotenv), переменные `POSTGRES_DB`,
  `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SQL_HOST`, `SQL_PORT` (как в
  автотестах). `search_path=public,content`: служебные таблицы Django — в
  `public`, модели — в `content`.
- Миксины `UUIDMixin`, `TimeStampedMixin` — в `movies/mixins.py`
  (test_mixins импортирует их оттуда).
- `movies/models.py`: 5 моделей. `db_table = 'content"."<table>'` (без
  внешних кавычек — так ждёт `test_db_table`). `verbose_name` русскими
  строками. M2M `genres`/`persons` через `through`.
- `created`/`modified` — `auto_now_add`/`auto_now`.
- `movies/admin.py`: `FilmworkAdmin.list_filter = ('type', 'genres')`,
  inline `GenreFilmworkInline`/`PersonFilmworkInline`, search_fields под
  тесты.
- initial-миграция: `makemigrations movies --name initial`, затем В НАЧАЛО
  operations добавлен `migrations.RunSQL('CREATE SCHEMA IF NOT EXISTS
  content;')` (иначе `manage.py test` и `migrate` упадут — нет схемы).
- Применение: `migrate --fake-initial` (БД уже создана DDL из части 1).
- Локализация: `makemessages -l en -l ru` → перевод в `.po` →
  `compilemessages`.

Линтер и тесты:
```bash
cd movies_admin
flake8 .
python manage.py test
```

---

## feature/sqlite-to-postgres — Часть 3: перенос данных

Папка: `sqlite_to_postgres/` — файл `load_data.py` (имя обязательно: его
запускает `test_s2p.py` как `python load_data.py`).

- Полный перенос 5 таблиц из `db.sqlite` в PostgreSQL.
- dataclass на каждую сущность; чтение пачками (`fetchmany`, `BATCH_SIZE`)
  через генераторы.
- `executemany` + `ON CONFLICT (id) DO NOTHING` (идемпотентность — повторный
  запуск не дублирует, проверяет `test_load_data`).
- `file_path` из SQLite не переносится (в PG поля нет); `created_at`/
  `updated_at` → `created`/`modified` через алиасы в SELECT.
- Обработка ошибок чтения/записи + `logging`; соединения открываются один
  раз, закрываются через `contextlib.closing`.
- dsl из переменных окружения (`SQL_HOST` и т.д.) — чтобы в CI подключиться
  к сервису `postgres`.
- `requirements.txt` (CI ставит его): `psycopg[binary]`, `python-dotenv`.

В CI часть 3 поднимает БД через `python manage.py migrate` (из movies_admin),
поэтому миграция с `RunSQL CREATE SCHEMA` обязательна и здесь.

Тест целостности (локально, НЕ в Actions):
`user_tests/check_consistency/test_consistency.py` — count + содержимое всех
5 таблиц (рядом нужен `db.sqlite`).

Линтер и тесты:
```bash
cd sqlite_to_postgres
flake8 .
python load_data.py
pytest
```
