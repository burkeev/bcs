"""
Роутер обратной связи: лайки/дизлайки и комментарии к ответам бота.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import FeedbackRequest
from ..services import feedback_service

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback")
def leave_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    """Сохраняет оценку конкретного ответа бота.

    Args:
        req: ``message_id``, флаг положительной оценки и опциональный
            комментарий.
        db: Сессия БД.

    Returns:
        dict: Подтверждение со статусом.
    """
    feedback_service.save_feedback(
        db,
        message_id=req.message_id,
        is_positive=req.is_positive,
        comment=req.comment,
    )
    return {"status": "success", "message": "Спасибо за отзыв!"}