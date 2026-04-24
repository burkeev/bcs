"""
Скрипт инициализации базы данных: создаёт первого администратора.

Запускается один раз после первого старта приложения, когда таблицы
уже созданы. Идемпотентен: при повторном запуске не дублирует
запись, а только убеждается, что у указанного email установлена
роль ``admin``.

Использование::

    python seed.py
"""

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import User

# ==========================================
# Параметры первого администратора
# ==========================================
ADMIN_EMAIL = "burkeev2018@yandex.ru"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def seed_admin() -> None:
    """Создаёт или обновляет учётную запись администратора.

    Сценарии:

    * Пользователя с ``ADMIN_EMAIL`` нет — создаётся новый с ролью
      ``admin``.
    * Пользователь есть, но он не admin — роль повышается до ``admin``
      (пароль не трогается).
    * Пользователь есть и уже admin — ничего не меняется.
    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()

        if existing is None:
            admin = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print(f"[OK] Создан администратор: {ADMIN_EMAIL}")
            print(f"     Пароль: {ADMIN_PASSWORD}")
            return

        if existing.role != "admin":
            existing.role = "admin"
            db.commit()
            print(f"[OK] Роль пользователя {ADMIN_EMAIL} повышена до admin.")
            print("     Пароль не изменён.")
            return

        print(f"[SKIP] Администратор {ADMIN_EMAIL} уже существует.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()