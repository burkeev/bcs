"""
Сервис обработки обратной связи от пользователей.

Отделён от роутера, чтобы при необходимости (например, при добавлении
антиспам-логики или агрегации статистики) логику можно было расширить
без изменения API-слоя.
"""

from sqlalchemy.orm import Session

from ..models import Feedback


def save_feedback(
    db: Session,
    message_id: int,
    is_positive: bool,
    comment: str | None = None,
) -> Feedback:
    """Сохраняет оценку ответа бота в БД.

    Args:
        db: Сессия БД.
        message_id: ID сообщения бота, к которому относится оценка.
        is_positive: True для лайка, False для дизлайка.
        comment: Опциональный текстовый комментарий пользователя.

    Returns:
        Feedback: Созданная запись.
    """
    fb = Feedback(
        message_id=message_id,
        is_positive=is_positive,
        comment=comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb