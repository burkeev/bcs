"""
Точка входа FastAPI-приложения "ЮрКонсультант ИИ".

Согласно архитектурной документации приложение реализовано как
*модульный монолит*: единый процесс FastAPI, внутри которого
бизнес-логика разнесена по слоям ``api/`` (роутеры),
``services/`` (бизнес-сервисы), ``core/`` (безопасность и
зависимости), ``models``, ``schemas`` и ``database``.

Этот модуль выполняет только три задачи:

1. Создаёт экземпляр :class:`FastAPI`.
2. Регистрирует CORS-мидлвару, статический фронтенд и две
   входные страницы — пользовательскую (``/``) и админскую (``/admin``).
3. Подключает роутеры (auth, chat, feedback, admin).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import admin, auth, chat, feedback
from .database import Base, engine

# При старте приложения создаём недостающие таблицы. Для production
# миграции лучше делать через Alembic, но для MVP этого достаточно.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ЮрКонсультант ИИ")

# CORS — разрешаем все источники на этапе разработки.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Раздача статических ассетов (если появятся CSS/JS-файлы отдельно).
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=FileResponse, include_in_schema=False)
def read_root():
    """Главная страница пользовательского чата."""
    return "static/index.html"


@app.get("/admin", response_class=FileResponse, include_in_schema=False)
def read_admin():
    """Страница административной панели.

    Доступ к данным внутри страницы дополнительно проверяется
    серверными эндпоинтами через :func:`app.core.deps.require_admin`,
    так что просто открыть HTML недостаточно для получения прав.
    """
    return "static/admin.html"


# Подключение роутеров API.
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(admin.router)