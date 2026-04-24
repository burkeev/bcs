"""
SQLAlchemy-модели приложения ЮрКонсультант ИИ.

Схема данных покрывает четыре обязательные функции:

* Ведение истории диалогов — :class:`User`, :class:`Conversation`,
  :class:`Message`.
* Обратная связь по ответам — :class:`Feedback`.
* Административный CRUD по НПА и типовым сценариям —
  :class:`LegalMaterial`, :class:`TypicalSituation`.
* Хранение конфигурации бота — :class:`BotConfig`.

Связь "сообщение ↔ использованные НПА" реализована через
вспомогательную таблицу :data:`message_materials` (many-to-many).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def utc_now() -> datetime:
    """Возвращает текущее время в UTC (timezone-aware).

    Используется как ``default`` для колонок ``DateTime(timezone=True)``,
    чтобы не зависеть от локального времени сервера.
    """
    return datetime.now(timezone.utc)


# Таблица связи многие-ко-многим: какое сообщение опиралось на какие НПА.
# Оформлена как чистый SQLAlchemy Core Table, так как содержательных полей
# (кроме двух FK) в ней нет.
message_materials = Table(
    "message_materials",
    Base.metadata,
    Column(
        "message_id",
        Integer,
        ForeignKey("messages.message_id"),
        primary_key=True,
    ),
    Column(
        "material_id",
        Integer,
        ForeignKey("legal_materials.material_id"),
        primary_key=True,
    ),
)


class User(Base):
    """Пользователь системы.

    Поддерживает две роли (``user`` / ``admin``), заданные строкой в
    ``role``. Пароль в MVP хранится как plain text в ``password_hash`` —
    для прод-версии нужно перейти на bcrypt/argon2.
    """

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), default="user", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    """Диалог пользователя с ботом.

    Один пользователь может иметь много диалогов; каждый диалог
    содержит упорядоченный набор сообщений.
    """

    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(200))
    started_at = Column(DateTime(timezone=True), default=utc_now)
    # onupdate отрабатывает при UPDATE через SQLAlchemy; при прямом
    # изменении значения в коде нужно проставлять время руками.
    last_updated = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """Отдельное сообщение внутри диалога (от пользователя или от бота).

    Для ответов бота может быть установлен флаг
    ``has_legal_references`` — использовались ли при генерации
    найденные через RAG фрагменты НПА.
    """

    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.conversation_id"),
        nullable=False,
    )
    sender = Column(String(10), nullable=False)  # 'user' или 'bot'
    text = Column(Text, nullable=False)
    has_legal_references = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now)

    conversation = relationship("Conversation", back_populates="messages")
    # uselist=False: на одно сообщение приходится не более одной оценки.
    feedbacks = relationship(
        "Feedback", back_populates="message", uselist=False
    )
    materials = relationship(
        "LegalMaterial",
        secondary=message_materials,
        back_populates="messages",
    )


class Feedback(Base):
    """Оценка пользователя на конкретный ответ бота.

    Минимально — лайк или дизлайк (``is_positive``); опционально —
    текстовый комментарий.
    """

    __tablename__ = "feedbacks"

    feedback_id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer, ForeignKey("messages.message_id"), nullable=False
    )
    is_positive = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    message = relationship("Message", back_populates="feedbacks")


class LegalMaterial(Base):
    """Фрагмент нормативно-правового акта (статья, пункт и т. п.).

    Хранится в PostgreSQL/SQLite как справочная сущность для админки.
    Параллельно этот же текст индексируется в ChromaDB (см.
    :class:`services.RAGService`) для семантического поиска.
    """

    __tablename__ = "legal_materials"

    material_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    article_number = Column(String(50))
    content = Column(Text, nullable=False)
    source_url = Column(String(500))
    last_updated = Column(DateTime(timezone=True), default=utc_now)

    messages = relationship(
        "Message",
        secondary=message_materials,
        back_populates="materials",
    )


class TypicalSituation(Base):
    """Типовой сценарий с готовой пошаговой инструкцией.

    Используется, когда вопрос пользователя попадает в распознаваемую
    категорию (например, "залив квартиры соседями") и можно выдать
    проверенный алгоритм действий вместо чистой LLM-генерации.
    """

    __tablename__ = "typical_situations"

    situation_id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)
    title = Column(String(300), nullable=False)
    step_by_step_instruction = Column(Text, nullable=False)
    last_updated = Column(DateTime(timezone=True), default=utc_now)


class BotConfig(Base):
    """Настройки работы LLM, редактируемые администратором.

    Хранит системный промпт, параметры генерации и список запрещённых
    тем. ``restricted_topics`` сериализуется как JSON-строка.
    """

    __tablename__ = "bot_config"

    config_id = Column(Integer, primary_key=True, index=True)
    system_prompt = Column(Text, nullable=False)
    temperature = Column(Float, nullable=False, default=0.3)
    max_tokens = Column(Integer, nullable=False, default=2048)
    restricted_topics = Column(Text)  # JSON-строка
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )