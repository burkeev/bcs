"""
Сервисный слой административных операций.

Содержит чистую бизнес-логику CRUD по сущностям, доступным
администратору. Роутер :mod:`app.api.admin` тонкий и просто
делегирует вызовы сюда.

Сервис делает синхронизацию двух хранилищ:

* для НПА — основная БД (PostgreSQL/SQLite) и векторное хранилище
  ChromaDB. При создании/удалении НПА запись в ChromaDB создаётся или
  удаляется автоматически, чтобы они не разъезжались.

При невозможности выполнить операцию сервис выбрасывает
:class:`LookupError` (запись не найдена) или :class:`ValueError`
(некорректные данные). Роутер ловит эти исключения и превращает в
HTTP 404 / 400.
"""

from typing import List

from sqlalchemy.orm import Session

from ..models import (
    BotConfig,
    Conversation,
    Feedback,
    LegalMaterial,
    Message,
    TypicalSituation,
    User,
)
from .chat_service import chat_service


# ==========================================
# CRUD: НПА (LegalMaterial)
# ==========================================
def list_legal_materials(db: Session) -> List[LegalMaterial]:
    """Возвращает все НПА, отсортированные по ID."""
    return (
        db.query(LegalMaterial)
        .order_by(LegalMaterial.material_id.asc())
        .all()
    )


def get_legal_material(db: Session, material_id: int) -> LegalMaterial:
    """Возвращает одну запись НПА по идентификатору.

    Raises:
        LookupError: Если запись не найдена.
    """
    item = (
        db.query(LegalMaterial)
        .filter(LegalMaterial.material_id == material_id)
        .first()
    )
    if item is None:
        raise LookupError("НПА не найден")
    return item


def create_legal_material(
    db: Session,
    title: str,
    content: str,
    article_number: str | None = None,
    source_url: str | None = None,
) -> LegalMaterial:
    """Создаёт запись НПА и индексирует её в ChromaDB.

    Запись попадает в две системы хранения одновременно: реляционная
    БД (для админских операций) и векторное хранилище (для
    семантического поиска RAG-сервисом).

    Args:
        db: Сессия БД.
        title: Заголовок (например, ``"ГК РФ Статья 1064"``).
        content: Полный текст статьи.
        article_number: Номер статьи (``"1064"``).
        source_url: Ссылка на оригинал (опционально).

    Returns:
        LegalMaterial: Созданная запись.
    """
    item = LegalMaterial(
        title=title,
        content=content,
        article_number=article_number,
        source_url=source_url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Индексируем в ChromaDB. Используем material_id как идентификатор
    # документа, чтобы потом можно было удалить тот же ключ.
    chat_service.rag_service.add_material(
        doc_id=str(item.material_id),
        text=content,
        source=title,
    )

    return item


def update_legal_material(
    db: Session,
    material_id: int,
    **fields,
) -> LegalMaterial:
    """Обновляет НПА. Применяет только не-None поля.

    При изменении ``content`` или ``title`` запись переиндексируется
    в ChromaDB (удаление + повторная вставка с тем же ID).

    Args:
        db: Сессия БД.
        material_id: ID НПА.
        **fields: Поля для обновления (см. :class:`LegalMaterialUpdate`).

    Returns:
        LegalMaterial: Обновлённая запись.

    Raises:
        LookupError: Если НПА не найден.
    """
    item = get_legal_material(db, material_id)

    # Применяем только переданные (не None) поля.
    text_changed = False
    for key, value in fields.items():
        if value is not None and hasattr(item, key):
            if key in ("content", "title"):
                text_changed = True
            setattr(item, key, value)

    db.commit()
    db.refresh(item)

    # Если изменился текст или заголовок — переиндексируем в ChromaDB.
    if text_changed:
        chat_service.rag_service.delete_material(str(item.material_id))
        chat_service.rag_service.add_material(
            doc_id=str(item.material_id),
            text=item.content,
            source=item.title,
        )

    return item


def delete_legal_material(db: Session, material_id: int) -> None:
    """Удаляет НПА из основной БД и из ChromaDB.

    Raises:
        LookupError: Если НПА не найден.
    """
    item = get_legal_material(db, material_id)
    chat_service.rag_service.delete_material(str(item.material_id))
    db.delete(item)
    db.commit()


# ==========================================
# CRUD: Типовые сценарии (TypicalSituation)
# ==========================================
def list_situations(db: Session) -> List[TypicalSituation]:
    """Возвращает все типовые сценарии."""
    return (
        db.query(TypicalSituation)
        .order_by(TypicalSituation.situation_id.asc())
        .all()
    )


def get_situation(db: Session, situation_id: int) -> TypicalSituation:
    """Возвращает один сценарий по ID.

    Raises:
        LookupError: Если сценарий не найден.
    """
    item = (
        db.query(TypicalSituation)
        .filter(TypicalSituation.situation_id == situation_id)
        .first()
    )
    if item is None:
        raise LookupError("Типовой сценарий не найден")
    return item


def create_situation(
    db: Session,
    category: str,
    title: str,
    step_by_step_instruction: str,
) -> TypicalSituation:
    """Создаёт новый типовой сценарий."""
    item = TypicalSituation(
        category=category,
        title=title,
        step_by_step_instruction=step_by_step_instruction,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_situation(
    db: Session,
    situation_id: int,
    **fields,
) -> TypicalSituation:
    """Обновляет сценарий. Применяет только не-None поля.

    Raises:
        LookupError: Если сценарий не найден.
    """
    item = get_situation(db, situation_id)
    for key, value in fields.items():
        if value is not None and hasattr(item, key):
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_situation(db: Session, situation_id: int) -> None:
    """Удаляет сценарий.

    Raises:
        LookupError: Если сценарий не найден.
    """
    item = get_situation(db, situation_id)
    db.delete(item)
    db.commit()


# ==========================================
# Управление пользователями
# ==========================================
def list_users(db: Session) -> List[User]:
    """Возвращает всех пользователей системы."""
    return db.query(User).order_by(User.user_id.asc()).all()


def update_user_role(
    db: Session,
    user_id: int,
    new_role: str,
) -> User:
    """Меняет роль пользователя.

    Args:
        db: Сессия БД.
        user_id: ID пользователя.
        new_role: ``"user"`` или ``"admin"``.

    Returns:
        User: Обновлённая запись.

    Raises:
        LookupError: Если пользователь не найден.
        ValueError: Если передана невалидная роль.
    """
    if new_role not in ("user", "admin"):
        raise ValueError("Роль должна быть 'user' или 'admin'")

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise LookupError("Пользователь не найден")

    user.role = new_role
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """Удаляет пользователя.

    Note:
        Удаление пользователя приводит к "висячим" внешним ключам в
        ``conversations``, если в БД не настроен ON DELETE CASCADE.
        Для production-варианта стоит либо настроить каскад, либо
        реализовать "мягкое удаление" (флаг ``is_deleted``). Для MVP
        достаточно текущего поведения.

    Raises:
        LookupError: Если пользователь не найден.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise LookupError("Пользователь не найден")
    db.delete(user)
    db.commit()


# ==========================================
# Конфигурация бота (BotConfig)
# ==========================================
# Строка-плейсхолдер по умолчанию для system_prompt.
_DEFAULT_SYSTEM_PROMPT = (
    "Ты — опытный российский юрист. Отвечай вежливо, структурированно, "
    "ссылайся на законы РФ. Объясняй сложные термины простым языком."
)


def get_or_create_bot_config(db: Session) -> BotConfig:
    """Возвращает единственную запись конфигурации, создавая её при
    отсутствии.

    Конфигурация моделируется как singleton — в системе всегда
    одна активная запись с ``config_id == 1``. При первом обращении
    она создаётся со значениями по умолчанию.
    """
    cfg = db.query(BotConfig).first()
    if cfg is None:
        cfg = BotConfig(
            system_prompt=_DEFAULT_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048,
            restricted_topics=None,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_bot_config(db: Session, **fields) -> BotConfig:
    """Обновляет конфигурацию бота (singleton).

    Применяются только не-None поля.
    """
    cfg = get_or_create_bot_config(db)
    for key, value in fields.items():
        if value is not None and hasattr(cfg, key):
            setattr(cfg, key, value)
    db.commit()
    db.refresh(cfg)
    return cfg


# ==========================================
# Статистика
# ==========================================
def collect_stats(db: Session) -> dict:
    """Собирает агрегированную статистику по системе.

    Returns:
        dict: Готов к десериализации в :class:`StatsOut`.
    """
    total_users = db.query(User).count()
    total_admins = db.query(User).filter(User.role == "admin").count()

    total_conversations = db.query(Conversation).count()
    total_messages = db.query(Message).count()
    user_messages = (
        db.query(Message).filter(Message.sender == "user").count()
    )
    bot_messages = (
        db.query(Message).filter(Message.sender == "bot").count()
    )

    total_feedbacks = db.query(Feedback).count()
    positive_feedbacks = (
        db.query(Feedback).filter(Feedback.is_positive.is_(True)).count()
    )
    negative_feedbacks = (
        db.query(Feedback).filter(Feedback.is_positive.is_(False)).count()
    )

    total_legal_materials = db.query(LegalMaterial).count()
    total_situations = db.query(TypicalSituation).count()

    return {
        "total_users": total_users,
        "total_admins": total_admins,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "user_messages": user_messages,
        "bot_messages": bot_messages,
        "total_feedbacks": total_feedbacks,
        "positive_feedbacks": positive_feedbacks,
        "negative_feedbacks": negative_feedbacks,
        "total_legal_materials": total_legal_materials,
        "total_situations": total_situations,
    }