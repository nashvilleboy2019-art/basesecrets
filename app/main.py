from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import os

from app.database import get_db
from app import models, auth
from app.routers import secrets, audit, activity, users
from app.templates_config import templates
from app.utils import get_flash, log_activity, require_login

app = FastAPI(title="BaseSecrets")
app.add_middleware(SessionMiddleware, secret_key="basesecrets-change-this-key-in-prod")

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

static_dir = os.path.join(PARENT_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

uploads_dir = os.path.join(PARENT_DIR, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(secrets.router, prefix="/secrets")
app.include_router(audit.router, prefix="/audit")
app.include_router(activity.router, prefix="/activity")
app.include_router(users.router, prefix="/users")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=302)
    if exc.status_code == 403:
        return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Accès refusé</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 flex items-center justify-center h-screen">
<div class="text-center">
  <div class="text-6xl font-bold text-red-400 mb-4">403</div>
  <h1 class="text-2xl font-semibold text-gray-700 mb-2">Accès refusé</h1>
  <p class="text-gray-500 mb-6">{exc.detail or "Vous n'avez pas les droits nécessaires."}</p>
  <a href="/" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Retour</a>
</div></body></html>""", status_code=403)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)

    total_secrets = db.query(func.count(models.Secret.id)).scalar() or 0
    by_domaine = (db.query(models.Secret.domaine, func.count(models.Secret.id))
                  .group_by(models.Secret.domaine)
                  .order_by(func.count(models.Secret.id).desc()).all())
    by_coffre = (db.query(models.Secret.coffre, func.count(models.Secret.id))
                 .group_by(models.Secret.coffre)
                 .order_by(func.count(models.Secret.id).desc()).limit(10).all())
    recent_activity = (db.query(models.ActivityLog)
                       .order_by(models.ActivityLog.timestamp.desc()).limit(15).all())
    open_audits = db.query(models.AuditSession).filter(models.AuditSession.status == "open").count()

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "active": "dashboard",
        "flash": get_flash(request),
        "total_secrets": total_secrets,
        "by_domaine": by_domaine,
        "by_coffre": by_coffre,
        "recent_activity": recent_activity,
        "open_audits": open_audits,
    })


@app.get("/guide", response_class=HTMLResponse)
async def guide(request: Request):
    return templates.TemplateResponse(request, "guide.html", {})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(request, "login.html", {"error": "Identifiants incorrects"})

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role

    log_activity(db, user, "Connexion")
    db.commit()
    return RedirectResponse("/", status_code=302)


@app.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if db_user:
            log_activity(db, db_user, "Déconnexion")
            db.commit()
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
