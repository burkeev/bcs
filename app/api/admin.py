"""
Административные эндпоинты.

Все маршруты этого роутера защищены зависимостью
:func:`app.core.deps.require_admin`: пользователь должен быть
аутентифицирован (заголовок ``X-User-Id``) и иметь роль ``admin``.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import require_admin
from ..database import get_db
from ..models import User
from ..schemas import (
    BotConfigOut,
    BotConfigUpdate,
    LegalMaterialCreate,
    LegalMaterialOut,
    LegalMaterialUpdate,
    StatsOut,
    TypicalSituationCreate,
    TypicalSituationOut,
    TypicalSituationUpdate,
    UserOut,
    UserRoleUpdate,
)
from ..services import admin_service

# prefix=/api/admin: все маршруты внутри начинаются с /api/admin/...
# dependencies=[require_admin]: каждый маршрут требует роли admin.
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# ==========================================
# НПА
# ==========================================
@router.get("/legal-materials", response_model=List[LegalMaterialOut])
def list_legal_materials(db: Session = Depends(get_db)):
    """Возвращает полный список НПА."""
    return admin_service.list_legal_materials(db)


@router.get(
    "/legal-materials/{material_id}",
    response_model=LegalMaterialOut,
)
def get_legal_material(material_id: int, db: Session = Depends(get_db)):
    """Возвращает один НПА по идентификатору."""
    try:
        return admin_service.get_legal_material(db, material_id)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


@router.post(
    "/legal-materials",
    response_model=LegalMaterialOut,
    status_code=status.HTTP_201_CREATED,
)
def create_legal_material(
    data: LegalMaterialCreate, db: Session = Depends(get_db)
):
    """Создаёт новый НПА в БД и индексирует в ChromaDB."""
    return admin_service.create_legal_material(db, **data.model_dump())


@router.put(
    "/legal-materials/{material_id}",
    response_model=LegalMaterialOut,
)
def update_legal_material(
    material_id: int,
    data: LegalMaterialUpdate,
    db: Session = Depends(get_db),
):
    """Обновляет НПА (частичное обновление)."""
    try:
        return admin_service.update_legal_material(
            db, material_id, **data.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


@router.delete(
    "/legal-materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_legal_material(
    material_id: int, db: Session = Depends(get_db)
):
    """Удаляет НПА из БД и из ChromaDB."""
    try:
        admin_service.delete_legal_material(db, material_id)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


# ==========================================
# Типовые сценарии
# ==========================================
@router.get("/situations", response_model=List[TypicalSituationOut])
def list_situations(db: Session = Depends(get_db)):
    """Возвращает все типовые сценарии."""
    return admin_service.list_situations(db)


@router.get(
    "/situations/{situation_id}",
    response_model=TypicalSituationOut,
)
def get_situation(situation_id: int, db: Session = Depends(get_db)):
    """Возвращает один сценарий по идентификатору."""
    try:
        return admin_service.get_situation(db, situation_id)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


@router.post(
    "/situations",
    response_model=TypicalSituationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_situation(
    data: TypicalSituationCreate, db: Session = Depends(get_db)
):
    """Создаёт новый типовой сценарий."""
    return admin_service.create_situation(db, **data.model_dump())


@router.put(
    "/situations/{situation_id}",
    response_model=TypicalSituationOut,
)
def update_situation(
    situation_id: int,
    data: TypicalSituationUpdate,
    db: Session = Depends(get_db),
):
    """Обновляет типовой сценарий (частичное обновление)."""
    try:
        return admin_service.update_situation(
            db, situation_id, **data.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


@router.delete(
    "/situations/{situation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_situation(situation_id: int, db: Session = Depends(get_db)):
    """Удаляет типовой сценарий."""
    try:
        admin_service.delete_situation(db, situation_id)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


# ==========================================
# Пользователи
# ==========================================
@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    """Возвращает всех пользователей системы."""
    return admin_service.list_users(db)


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Меняет роль пользователя.

    Запрещено понижать собственную роль — иначе администратор может
    случайно лишить себя доступа и оставить систему без админов.
    """
    if user_id == current_admin.user_id and data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя понизить собственную роль",
        )
    try:
        return admin_service.update_user_role(db, user_id, data.role)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Удаляет пользователя.

    Запрещено удалять самого себя.
    """
    if user_id == current_admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственную учётную запись",
        )
    try:
        admin_service.delete_user(db, user_id)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


# ==========================================
# Конфигурация бота
# ==========================================
@router.get("/config", response_model=BotConfigOut)
def get_bot_config(db: Session = Depends(get_db)):
    """Возвращает текущую конфигурацию бота (создаёт при отсутствии)."""
    return admin_service.get_or_create_bot_config(db)


@router.put("/config", response_model=BotConfigOut)
def update_bot_config(
    data: BotConfigUpdate, db: Session = Depends(get_db)
):
    """Обновляет конфигурацию бота (частичное обновление)."""
    return admin_service.update_bot_config(
        db, **data.model_dump(exclude_unset=True)
    )


# ==========================================
# Статистика
# ==========================================
@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    """Возвращает агрегированную статистику работы системы."""
    return admin_service.collect_stats(db)