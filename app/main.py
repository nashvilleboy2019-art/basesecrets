from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import json
import os

from app.database import get_db, engine
from app import models, auth
from app.routers import secrets, audit, activity, users, settings as settings_router, api_v1
from app.templates_config import templates
from app.utils import get_flash, log_activity, require_login

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BaseSecrets")
app.add_middleware(SessionMiddleware, secret_key="basesecrets-change-this-key-in-prod")

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

static_dir = os.path.join(PARENT_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

uploads_dir = os.path.join(PARENT_DIR, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

screenshots_dir = os.path.join(PARENT_DIR, "screenshots")
os.makedirs(screenshots_dir, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=screenshots_dir), name="screenshots")

app.include_router(secrets.router, prefix="/secrets")
app.include_router(audit.router, prefix="/audit")
app.include_router(activity.router, prefix="/activity")
app.include_router(users.router, prefix="/users")
app.include_router(settings_router.router, prefix="/settings")
app.include_router(api_v1.router, prefix="/api/v1", tags=["API"])


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
    active_count = db.query(func.count(models.Secret.id)).filter(models.Secret.archived == False).scalar() or 0
    archived_count = db.query(func.count(models.Secret.id)).filter(models.Secret.archived == True).scalar() or 0
    total_users = db.query(func.count(models.User.id)).scalar() or 0

    by_domaine = (db.query(models.Secret.domaine, func.count(models.Secret.id))
                  .group_by(models.Secret.domaine)
                  .order_by(func.count(models.Secret.id).desc()).all())
    by_coffre = (db.query(models.Secret.coffre, func.count(models.Secret.id))
                 .group_by(models.Secret.coffre)
                 .order_by(func.count(models.Secret.id).desc()).limit(10).all())

    recent_activity = (db.query(models.ActivityLog)
                       .order_by(models.ActivityLog.timestamp.desc()).limit(15).all())
    last_activity_log = (db.query(models.ActivityLog)
                         .order_by(models.ActivityLog.timestamp.desc()).first())

    open_audits = db.query(models.AuditSession).filter(models.AuditSession.status == "open").count()

    # Top 5 actions dans les logs
    top_actions = (db.query(models.ActivityLog.action, func.count(models.ActivityLog.id))
                   .group_by(models.ActivityLog.action)
                   .order_by(func.count(models.ActivityLog.id).desc())
                   .limit(5).all())
    max_action_count = top_actions[0][1] if top_actions else 1

    # Données mensuelles complètes (depuis le début) pour calcul du cumul
    now = datetime.utcnow()
    fr_months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

    added_all = (db.query(
        func.strftime('%Y-%m', models.Secret.created_at).label('month'),
        func.count(models.Secret.id)
    ).group_by('month').order_by('month').all())

    archived_all = (db.query(
        func.strftime('%Y-%m', models.SecretHistory.changed_at).label('month'),
        func.count(models.SecretHistory.id)
    ).filter(models.SecretHistory.action == "Archivage")
    .group_by('month').order_by('month').all())

    unarchived_all = (db.query(
        func.strftime('%Y-%m', models.SecretHistory.changed_at).label('month'),
        func.count(models.SecretHistory.id)
    ).filter(models.SecretHistory.action == "Désarchivage")
    .group_by('month').order_by('month').all())

    added_dict = {row[0]: row[1] for row in added_all}
    archived_dict = {row[0]: row[1] for row in archived_all}
    unarchived_dict = {row[0]: row[1] for row in unarchived_all}
    all_keys = sorted(set(
        list(added_dict) + list(archived_dict) + list(unarchived_dict)
    ))

    # 6 derniers mois (labels + clés)
    months_labels = []
    month_keys = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y:04d}-{m:02d}"
        month_keys.append(key)
        months_labels.append(f"{fr_months[m - 1]} {y}")

    months_data_added = [added_dict.get(k, 0) for k in month_keys]
    months_data_archived = [archived_dict.get(k, 0) for k in month_keys]

    # Cumul actifs = Σ(créés) - Σ(archivés) + Σ(désarchivés) jusqu'à chaque mois
    months_data_cumul = []
    for key in month_keys:
        total = (
            sum(added_dict.get(k, 0) for k in all_keys if k <= key)
            - sum(archived_dict.get(k, 0) for k in all_keys if k <= key)
            + sum(unarchived_dict.get(k, 0) for k in all_keys if k <= key)
        )
        months_data_cumul.append(total)

    # Audits ouverts avec taux de complétion
    open_audit_sessions = (db.query(models.AuditSession)
                           .filter(models.AuditSession.status == "open")
                           .order_by(models.AuditSession.created_at.desc()).all())
    audit_progress = []
    for session in open_audit_sessions:
        total_in_coffre = (db.query(func.count(models.Secret.id))
                           .filter(models.Secret.coffre == session.coffre,
                                   models.Secret.archived == False)
                           .scalar() or 0)
        checked = (db.query(func.count(models.AuditCheck.id))
                   .filter(models.AuditCheck.session_id == session.id)
                   .scalar() or 0)
        pct = round(checked / total_in_coffre * 100) if total_in_coffre > 0 else 0
        audit_progress.append({
            "session": session,
            "total": total_in_coffre,
            "checked": checked,
            "pct": pct,
        })

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "active": "dashboard",
        "flash": get_flash(request),
        "total_secrets": total_secrets,
        "active_count": active_count,
        "archived_count": archived_count,
        "total_users": total_users,
        "by_domaine": by_domaine,
        "by_coffre": by_coffre,
        "recent_activity": recent_activity,
        "last_activity_log": last_activity_log,
        "open_audits": open_audits,
        "top_actions": top_actions,
        "max_action_count": max_action_count,
        "months_labels": json.dumps(months_labels),
        "months_data_added": json.dumps(months_data_added),
        "months_data_archived": json.dumps(months_data_archived),
        "months_data_cumul": json.dumps(months_data_cumul),
        "audit_progress": audit_progress,
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
