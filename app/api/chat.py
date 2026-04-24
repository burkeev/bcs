"""
Роутер чата: отправка сообщений, история диалогов, чтение конкретного диалога.

При обработке запроса параметры генерации LLM (системный промпт,
температура, max_tokens) читаются из таблицы ``bot_config`` через
:func:`app.services.admin_service.get_or_create_bot_config`. Это
позволяет администратору менять поведение бота через админ-панель
без перезапуска приложения.
"""

import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Message
from ..schemas import (
    ChatRequest,
    ChatResponse,
    ConversationOut,
    MessageOut,
)
from ..services import admin_service
from ..services.chat_service import chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    """Обрабатывает сообщение пользователя и возвращает ответ LLM.

    Алгоритм:

    1. Находит или создаёт :class:`Conversation`.
    2. Сохраняет реплику пользователя.
    3. Читает актуальную :class:`BotConfig` из БД.
    4. Вызывает :meth:`ChatService.process_query` (RAG + LLM) с параметрами
       из конфигурации.
    5. Сохраняет ответ бота, обновляет ``last_updated`` диалога.

    Args:
        req: ``user_id``, опциональный ``conversation_id``, текст вопроса.
        db: Сессия БД.

    Returns:
        ChatResponse: Идентификаторы созданных сущностей и ответ бота.

    Raises:
        HTTPException: 404, если ``conversation_id`` указан, но не найден.
    """
    if req.conversation_id:
        conv = (
            db.query(Conversation)
            .filter(Conversation.conversation_id == req.conversation_id)
            .first()
        )
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Диалог не найден",
            )
    else:
        conv = Conversation(user_id=req.user_id, title=req.text[:50])
        db.add(conv)
        db.commit()
        db.refresh(conv)

    user_msg = Message(
        conversation_id=conv.conversation_id,
        sender="user",
        text=req.text,
    )
    db.add(user_msg)
    db.commit()

    # Читаем актуальную конфигурацию из БД. Если её нет —
    # admin_service сам создаст запись со значениями по умолчанию.
    cfg = admin_service.get_or_create_bot_config(db)

    ai_result = chat_service.process_query(
        user_query=req.text,
        system_prompt=cfg.system_prompt,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )

    bot_msg = Message(
        conversation_id=conv.conversation_id,
        sender="bot",
        text=ai_result["reply"],
        has_legal_references=ai_result["has_references"],
    )
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)

    conv.last_updated = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    return ChatResponse(
        conversation_id=conv.conversation_id,
        message_id=bot_msg.message_id,
        reply=bot_msg.text,
        has_references=bot_msg.has_legal_references,
    )


@router.get("/history/{user_id}", response_model=List[ConversationOut])
def get_history(user_id: int, db: Session = Depends(get_db)):
    """Возвращает список диалогов пользователя, отсортированный по свежести.

    Args:
        user_id: Идентификатор пользователя.
        db: Сессия БД.

    Returns:
        list[ConversationOut]: Диалоги от самых свежих к старым.
    """
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.last_updated.desc())
        .all()
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageOut],
)
def get_conversation_messages(
    conversation_id: int, db: Session = Depends(get_db)
):
    """Возвращает все сообщения конкретного диалога в хронологическом порядке.

    Используется фронтендом при клике на элемент истории — чтобы
    отрисовать ранее состоявшийся диалог.

    Args:
        conversation_id: Идентификатор диалога.
        db: Сессия БД.

    Returns:
        list[MessageOut]: Сообщения от старых к новым.

    Raises:
        HTTPException: 404, если диалога не существует.
    """
    conv = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диалог не найден",
        )

    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.asc())
        .all()
    )