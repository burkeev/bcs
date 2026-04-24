"""
Сервисный слой аутентификации.

Содержит чистую бизнес-логику входа и авторегистрации, не зависящую
от FastAPI. Используется из роутера :mod:`app.api.auth`.
"""

from sqlalchemy.orm import Session

from ..core.security import hash_password, verify_password
from ..models import User


def login_or_register(db: Session, email: str, password: str) -> User:
    """Аутентифицирует пользователя или регистрирует нового.

    Поведение:

    * Если пользователя с таким email нет — создаёт нового с ролью
      ``user`` и хэшированным паролем.
    * Если пользователь существует — сверяет пароль через bcrypt.
      При несовпадении выбрасывает :class:`ValueError`.

    Роутер в :mod:`app.api.auth` ловит :class:`ValueError` и
    превращает в HTTP 401.

    Args:
        db: Сессия БД.
        email: Email пользователя.
        password: Пароль в открытом виде.

    Returns:
        User: Аутентифицированный (или только что созданный) пользователь.

    Raises:
        ValueError: Если пользователь существует, но пароль неверен.
    """
    user = db.query(User).filter(User.email == email).first()

    if user is None:
        # Авторегистрация: username = локальная часть email,
        # роль по умолчанию — обычный пользователь.
        user = User(
            username=email.split("@")[0],
            email=email,
            password_hash=hash_password(password),
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    if not verify_password(password, user.password_hash):
        raise ValueError("Неверный пароль")

    return user