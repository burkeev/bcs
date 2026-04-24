"""
Pydantic-схемы для валидации запросов и формирования ответов API.

Сгруппированы по доменным областям:

* Аутентификация: :class:`LoginRequest`, :class:`LoginResponse`.
* Чат: :class:`ChatRequest`, :class:`ChatResponse`, :class:`MessageOut`,
  :class:`ConversationOut`.
* Обратная связь: :class:`FeedbackRequest`.
* Админ-CRUD по НПА: :class:`LegalMaterialCreate`,
  :class:`LegalMaterialUpdate`, :class:`LegalMaterialOut`.
* Админ-CRUD по типовым сценариям: :class:`TypicalSituationCreate`,
  :class:`TypicalSituationUpdate`, :class:`TypicalSituationOut`.
* Админ-управление пользователями: :class:`UserOut`,
  :class:`UserRoleUpdate`.
* Админ-конфигурация бота: :class:`BotConfigOut`,
  :class:`BotConfigUpdate`.
* Админ-статистика: :class:`StatsOut`.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ==========================================
# Аутентификация
# ==========================================
class LoginRequest(BaseModel):
    """Тело запроса на вход в систему."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Ответ на успешный вход.

    Поле ``role`` нужно фронтенду, чтобы решить, показывать ли
    административные элементы интерфейса.
    """

    user_id: int
    username: str
    role: str


# ==========================================
# Чат
# ==========================================
class ChatRequest(BaseModel):
    """Запрос пользователя к чат-боту."""

    user_id: int
    conversation_id: Optional[int] = None
    text: str


class ChatResponse(BaseModel):
    """Ответ чат-бота на сообщение пользователя."""

    conversation_id: int
    message_id: int
    reply: str
    has_references: bool


class MessageOut(BaseModel):
    """Сообщение в формате, удобном для рендеринга на фронте."""

    model_config = ConfigDict(from_attributes=True)

    message_id: int
    sender: str
    text: str
    has_legal_references: bool
    timestamp: datetime


class ConversationOut(BaseModel):
    """Краткое описание диалога для списка истории."""

    model_config = ConfigDict(from_attributes=True)

    conversation_id: int
    title: Optional[str]
    last_updated: datetime


# ==========================================
# Обратная связь
# ==========================================
class FeedbackRequest(BaseModel):
    """Оценка пользователя на конкретный ответ бота."""

    message_id: int
    is_positive: bool
    comment: Optional[str] = None


# ==========================================
# Админ: НПА (LegalMaterial)
# ==========================================
class LegalMaterialCreate(BaseModel):
    """Создание новой записи НПА."""

    title: str
    article_number: Optional[str] = None
    content: str
    source_url: Optional[str] = None


class LegalMaterialUpdate(BaseModel):
    """Обновление НПА. Все поля опциональны (частичное обновление)."""

    title: Optional[str] = None
    article_number: Optional[str] = None
    content: Optional[str] = None
    source_url: Optional[str] = None


class LegalMaterialOut(BaseModel):
    """Запись НПА в формате ответа API."""

    model_config = ConfigDict(from_attributes=True)

    material_id: int
    title: str
    article_number: Optional[str]
    content: str
    source_url: Optional[str]
    last_updated: datetime


# ==========================================
# Админ: Типовые сценарии (TypicalSituation)
# ==========================================
class TypicalSituationCreate(BaseModel):
    """Создание типового сценария."""

    category: str
    title: str
    step_by_step_instruction: str


class TypicalSituationUpdate(BaseModel):
    """Обновление сценария. Все поля опциональны."""

    category: Optional[str] = None
    title: Optional[str] = None
    step_by_step_instruction: Optional[str] = None


class TypicalSituationOut(BaseModel):
    """Сценарий в формате ответа API."""

    model_config = ConfigDict(from_attributes=True)

    situation_id: int
    category: str
    title: str
    step_by_step_instruction: str
    last_updated: datetime


# ==========================================
# Админ: Управление пользователями
# ==========================================
class UserOut(BaseModel):
    """Краткая информация о пользователе для админ-списка."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    role: str
    created_at: datetime


class UserRoleUpdate(BaseModel):
    """Запрос на смену роли пользователя.

    Допустимые значения: ``"user"`` или ``"admin"``. Валидация
    выполняется на уровне сервиса.
    """

    role: str


# ==========================================
# Админ: Конфигурация бота (BotConfig)
# ==========================================
class BotConfigOut(BaseModel):
    """Текущая конфигурация бота."""

    model_config = ConfigDict(from_attributes=True)

    config_id: int
    system_prompt: str
    temperature: float
    max_tokens: int
    restricted_topics: Optional[str]
    updated_at: datetime


class BotConfigUpdate(BaseModel):
    """Обновление конфигурации бота. Все поля опциональны."""

    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    restricted_topics: Optional[str] = None


# ==========================================
# Админ: Статистика
# ==========================================
class StatsOut(BaseModel):
    """Агрегированная статистика по работе бота."""

    total_users: int
    total_admins: int
    total_conversations: int
    total_messages: int
    user_messages: int
    bot_messages: int
    total_feedbacks: int
    positive_feedbacks: int
    negative_feedbacks: int
    total_legal_materials: int
    total_situations: int