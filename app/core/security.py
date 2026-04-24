"""
Утилиты безопасности: хэширование и проверка паролей.

Используется библиотека :mod:`passlib` со схемой ``bcrypt`` —
стандарт де-факто для хранения паролей в production.

Bcrypt:

* медленный по дизайну, что делает невыгодным брутфорс по словарю;
* автоматически добавляет соль к хэшу;
* инкапсулирует параметры (rounds) внутри самого хэша, что позволяет
  повышать сложность со временем без миграции данных.
"""

from passlib.context import CryptContext

# Конфигурация passlib: используется только bcrypt.
# При появлении более новой схемы старые хэши автоматически помечаются
# как deprecated и обновляются при следующей успешной проверке.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Хэширует пароль для безопасного хранения в БД.

    Args:
        plain_password: Пароль в открытом виде.

    Returns:
        str: Bcrypt-хэш длиной около 60 символов.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Сверяет открытый пароль с сохранённым хэшем.

    Args:
        plain_password: Пароль, введённый пользователем.
        hashed_password: Хэш из БД (поле ``User.password_hash``).

    Returns:
        bool: True, если пароли совпадают; иначе False.
    """
    return pwd_context.verify(plain_password, hashed_password)