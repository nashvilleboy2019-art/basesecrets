from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app import models
from app.auth import hash_password
from app.utils import require_responsable, log_activity, set_flash, get_flash
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def list_users(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    users = db.query(models.User).order_by(models.User.role, models.User.username).all()
    return templates.TemplateResponse(request, "users/list.html", {
        "user": user, "active": "users",
        "flash": get_flash(request),
        "users": users,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_user_form(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    return templates.TemplateResponse(request, "users/form.html", {
        "user": user, "active": "users",
        "target": None, "errors": {},
    })


@router.post("/", response_class=HTMLResponse)
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    user = require_responsable(request, db)
    username = username.strip()
    errors = {}

    if role not in ("responsable", "auditeur"):
        errors["role"] = "Rôle invalide."
    if len(username) < 3:
        errors["username"] = "Minimum 3 caractères."
    elif db.query(models.User).filter(models.User.username == username).first():
        errors["username"] = "Ce nom d'utilisateur existe déjà."
    if len(password) < 6:
        errors["password"] = "Minimum 6 caractères."

    if errors:
        return templates.TemplateResponse(request, "users/form.html", {
            "user": user, "active": "users",
            "target": {"username": username, "role": role},
            "errors": errors,
        })

    new_user = models.User(
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(new_user)
    db.flush()
    log_activity(db, user, "Création compte", "user", new_user.id, f"{username} ({role})")
    db.commit()

    set_flash(request, f"Compte « {username} » créé.")
    return RedirectResponse("/users/", status_code=302)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "users/form.html", {
        "user": user, "active": "users",
        "target": target, "errors": {},
    })


@router.post("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user(
    user_id: int,
    request: Request,
    username: str = Form(...),
    password: str = Form(""),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    user = require_responsable(request, db)
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404)

    username = username.strip()
    errors = {}

    if role not in ("responsable", "auditeur"):
        errors["role"] = "Rôle invalide."
    if len(username) < 3:
        errors["username"] = "Minimum 3 caractères."
    elif (db.query(models.User)
          .filter(models.User.username == username, models.User.id != user_id).first()):
        errors["username"] = "Ce nom d'utilisateur existe déjà."
    if password and len(password) < 6:
        errors["password"] = "Minimum 6 caractères."

    # Prevent removing the last responsable
    if role != "responsable" and target.role == "responsable":
        remaining = (db.query(models.User)
                     .filter(models.User.role == "responsable", models.User.id != user_id)
                     .count())
        if remaining == 0:
            errors["role"] = "Impossible : il doit rester au moins un responsable."

    if errors:
        return templates.TemplateResponse(request, "users/form.html", {
            "user": user, "active": "users",
            "target": {"id": user_id, "username": username, "role": role},
            "errors": errors,
        })

    old_role = target.role
    target.username = username
    target.role = role
    if password:
        target.password_hash = hash_password(password)

    details = f"{username} role={old_role}→{role}" + (" + mdp changé" if password else "")
    log_activity(db, user, "Modification compte", "user", user_id, details)
    db.commit()

    set_flash(request, f"Compte « {username} » mis à jour.")
    return RedirectResponse("/users/", status_code=302)


@router.post("/{user_id}/delete", response_class=HTMLResponse)
async def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)

    if user_id == user.id:
        set_flash(request, "Vous ne pouvez pas supprimer votre propre compte.", "error")
        return RedirectResponse("/users/", status_code=302)

    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404)

    if target.role == "responsable":
        remaining = (db.query(models.User)
                     .filter(models.User.role == "responsable", models.User.id != user_id)
                     .count())
        if remaining == 0:
            set_flash(request, "Impossible : il doit rester au moins un responsable.", "error")
            return RedirectResponse("/users/", status_code=302)

    name = target.username
    db.delete(target)
    log_activity(db, user, "Suppression compte", "user", user_id, name)
    db.commit()

    set_flash(request, f"Compte « {name} » supprimé.")
    return RedirectResponse("/users/", status_code=302)
