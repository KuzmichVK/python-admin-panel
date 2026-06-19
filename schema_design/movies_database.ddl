CREATE SCHEMA IF NOT EXISTS content;

CREATE TABLE IF NOT EXISTS content.film_work (
    id uuid PRIMARY KEY,
    title text NOT NULL,
    description text,
    creation_date date,
    rating real,
    type text NOT NULL,
    created timestamp with time zone,
    modified timestamp with time zone
);

CREATE TABLE IF NOT EXISTS content.genre (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    description text,
    created timestamp with time zone,
    modified timestamp with time zone
);

CREATE TABLE IF NOT EXISTS content.person (
    id uuid PRIMARY KEY,
    full_name text NOT NULL,
    created timestamp with time zone,
    modified timestamp with time zone
);

CREATE TABLE IF NOT EXISTS content.genre_film_work (
    id uuid PRIMARY KEY,
    genre_id uuid NOT NULL REFERENCES content.genre (id) ON DELETE CASCADE,
    film_work_id uuid NOT NULL REFERENCES content.film_work (id) ON DELETE CASCADE,
    created timestamp with time zone
);

CREATE TABLE IF NOT EXISTS content.person_film_work (
    id uuid PRIMARY KEY,
    person_id uuid NOT NULL REFERENCES content.person (id) ON DELETE CASCADE,
    film_work_id uuid NOT NULL REFERENCES content.film_work (id) ON DELETE CASCADE,
    role text,
    created timestamp with time zone
);

CREATE INDEX IF NOT EXISTS film_work_creation_date_idx
    ON content.film_work (creation_date);

CREATE UNIQUE INDEX IF NOT EXISTS genre_film_work_idx
    ON content.genre_film_work (film_work_id, genre_id);

CREATE UNIQUE INDEX IF NOT EXISTS person_film_work_idx
    ON content.person_film_work (film_work_id, person_id, role);
