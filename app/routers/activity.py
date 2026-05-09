from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.utils import require_responsable, get_flash, paginate
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def list_activity(
    request: Request,
    page: int = 1,
    username: str = "",
    action: str = "",
    db: Session = Depends(get_db)
):
    user = require_responsable(request, db)

    query = db.query(models.ActivityLog).order_by(models.ActivityLog.timestamp.desc())
    if username:
        query = query.filter(models.ActivityLog.username.ilike(f"%{username}%"))
    if action:
        query = query.filter(models.ActivityLog.action.ilike(f"%{action}%"))

    pagination = paginate(query, page, per_page=100)

    return templates.TemplateResponse(request, "activity/list.html", {
        "user": user,
        "active": "activity",
        "flash": get_flash(request),
        "pagination": pagination,
        "username": username,
        "action": action,
    })
