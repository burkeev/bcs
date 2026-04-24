"""
FastAPI-зависимости для аутентификации и авторизации.

В рамках упрощённой модели MVP клиент передаёт ``user_id`` через HTTP-заголовок
``X-User-Id``. По нему сервер находит запись в таблице :class:`User` и
проверяет роль. В production-варианте этот механизм заменяется на JWT-токены
с подписью, но для целей курсового проекта приведённой схемы достаточно.

Две основные зависимости:

* :func:`get_current_user` — достаёт пользователя по ``X-User-Id``.
  Используется во всех "защищённых" эндпоинтах.
* :func:`require_admin` — то же, плюс проверка ``role == "admin"``.
  Используется во всех админских эндпоинтах.
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def get_current_user(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    """Возвращает пользователя, идентифицированного заголовком ``X-User-Id``.

    Args:
        x_user_id: Значение HTTP-заголовка ``X-User-Id``.
            FastAPI автоматически конвертирует имя в kebab-case.
        db: Сессия БД.

    Returns:
        User: ORM-объект пользователя.

    Raises:
        HTTPException: 401, если заголовок отсутствует.
        HTTPException: 404, если пользователь с таким ID не найден.
    """
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не передан заголовок X-User-Id",
        )

    user = db.query(User).filter(User.user_id == x_user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Пропускает запрос только если текущий пользователь — администратор.

    Используется как зависимость во всех ``/api/admin/*`` эндпоинтах.

    Args:
        current_user: Пользователь, инжектируется через
            :func:`get_current_user`.

    Returns:
        User: Тот же пользователь, если у него роль ``admin``.

    Raises:
        HTTPException: 403, если у пользователя роль ``user``.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ разрешён только администраторам",
        )
    return current_user