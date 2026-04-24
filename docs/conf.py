"""
Конфигурация Sphinx для проекта "ЮрКонсультант ИИ".

Расположение: ``docs/conf.py``. После выполнения ``sphinx-quickstart``
этот файл следует заменить на данный.
"""

import os
import sys

# Корень проекта (на уровень выше docs/) добавляется в sys.path,
# чтобы autodoc мог импортировать пакет ``app``.
sys.path.insert(0, os.path.abspath(".."))


# -- Информация о проекте ----------------------------------------------------
project = "ЮрКонсультант ИИ"
author = "Burkeev R."
release = "0.1.0"
copyright = f"2026, {author}"


# -- Расширения --------------------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",       # автоматический сбор docstrings
    "sphinx.ext.napoleon",      # поддержка Google/NumPy style docstrings
    "sphinx.ext.viewcode",      # ссылки на исходники рядом с описанием
    "sphinx.ext.autosummary",   # сводные таблицы по модулям
    "sphinx.ext.intersphinx",   # ссылки на внешнюю документацию (Python, FastAPI)
]


# -- Настройки autodoc / napoleon -------------------------------------------
autosummary_generate = True
autodoc_member_order = "bysource"  # порядок как в исходнике
autodoc_typehints = "description"  # типы из аннотаций - в описание параметров
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True


# -- Внешние ссылки ----------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "fastapi": ("https://fastapi.tiangolo.com/", None),
}


# -- Локализация и общие настройки -------------------------------------------
language = "ru"
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- HTML-вывод --------------------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = f"{project} — Документация разработчика"
