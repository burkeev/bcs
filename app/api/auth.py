"""
Роутер аутентификации: вход и авторегистрация.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import LoginRequest, LoginResponse
from ..services import auth_service

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Аутентифицирует пользователя или регистрирует нового.

    При первом входе с новым email пользователь создаётся автоматически
    с ролью ``user``. Существующие пользователи проверяются через bcrypt.

    Args:
        req: Email и пароль.
        db: Сессия БД.

    Returns:
        LoginResponse: ``user_id``, ``username`` и ``role``. Поле ``role``
        используется фронтом для решения, показывать ли админ-панель.

    Raises:
        HTTPException: 401 при неверном пароле.
    """
    try:
        user = auth_service.login_or_register(db, req.email, req.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return LoginResponse(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )