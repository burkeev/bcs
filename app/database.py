"""
Конфигурация подключения к базе данных и фабрика сессий SQLAlchemy.

Поддерживает две СУБД через переменную окружения ``DATABASE_URL``:

* PostgreSQL (рекомендуется для production):
  ``postgresql+psycopg2://user:pass@localhost:5432/legal_bot``
* SQLite (по умолчанию, удобно для разработки):
  ``sqlite:///./legal_bot_db.sqlite``

Если ``DATABASE_URL`` не задан — используется SQLite в корне проекта.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Строка подключения берётся из .env. Fallback на SQLite, чтобы проект
# можно было запустить "из коробки" без поднятия Postgres.
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///./legal_bot_db.sqlite"
)

# Для SQLite требуется connect_args={"check_same_thread": False},
# для Postgres — нет. Подмешиваем аргумент только для SQLite.
engine_kwargs = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI-зависимость: выдаёт сессию БД и гарантированно её закрывает.

    Yields:
        Session: Активная сессия SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()