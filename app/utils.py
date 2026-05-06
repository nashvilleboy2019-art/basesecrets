import json
from datetime import datetime
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy.orm import Session
from app import models


def require_login(request: Request, db: Session) -> models.User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401)
    return user


def require_responsable(request: Request, db: Session) -> models.User:
    user = require_login(request, db)
    if user.role != "responsable":
        raise HTTPException(status_code=403, detail="Accès réservé au responsable de sécurité.")
    return user


def log_activity(db: Session, user: models.User, action: str,
                 resource: str = None, resource_id=None, details: str = None):
    db.add(models.ActivityLog(
        user_id=user.id,
        username=user.username,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details,
        timestamp=datetime.utcnow(),
    ))


def log_history(db: Session, secret_id: int, action: str, user_id: int,
                old_values: dict = None, new_values: dict = None, note: str = None):
    db.add(models.SecretHistory(
        secret_id=secret_id,
        action=action,
        changed_by=user_id,
        old_values=json.dumps(old_values, ensure_ascii=False) if old_values else None,
        new_values=json.dumps(new_values, ensure_ascii=False) if new_values else None,
        note=note,
        changed_at=datetime.utcnow(),
    ))


def set_flash(request: Request, message: str, category: str = "success"):
    request.session["flash"] = {"message": message, "category": category}


def get_flash(request: Request):
    if "flash" in request.session:
        flash = request.session["flash"]
        del request.session["flash"]
        return flash
    return None


def paginate(query, page: int, per_page: int = 50) -> dict:
    total = query.count()
    page = max(1, page)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "results": items,
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
        "start": (page - 1) * per_page + 1 if total > 0 else 0,
        "end": min(page * per_page, total),
    }
