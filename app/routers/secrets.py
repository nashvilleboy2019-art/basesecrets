from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import os, uuid, json

from app.database import get_db
from app import models
from app.utils import (require_login, require_responsable, log_activity,
                       log_history, set_flash, get_flash, paginate)
from app.templates_config import templates

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "scans")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_filters(db):
    domaines = [r[0] for r in db.query(models.Secret.domaine).distinct()
                .order_by(models.Secret.domaine).all()]
    coffres = [r[0] for r in db.query(models.Secret.coffre).distinct()
               .order_by(models.Secret.coffre).all()]
    return domaines, coffres


@router.get("/", response_class=HTMLResponse)
async def list_secrets(
    request: Request,
    q: str = "",
    domaine: str = "",
    coffre: str = "",
    page: int = 1,
    db: Session = Depends(get_db)
):
    user = require_login(request, db)

    query = db.query(models.Secret)
    if q:
        # Sous-requête : secrets dont un ancien num_envelope correspond
        old_env_subq = (
            db.query(models.SecretHistory.secret_id)
            .filter(
                models.SecretHistory.action == "Changement enveloppe",
                models.SecretHistory.old_values.ilike(f'%{q}%')
            ).subquery()
        )
        query = query.filter(or_(
            models.Secret.libelle.ilike(f"%{q}%"),
            models.Secret.id_secret.ilike(f"%{q}%"),
            models.Secret.nom_technique.ilike(f"%{q}%"),
            models.Secret.num_envelope.ilike(f"%{q}%"),
            models.Secret.id.in_(old_env_subq),
        ))
    if domaine:
        query = query.filter(models.Secret.domaine == domaine)
    if coffre:
        query = query.filter(models.Secret.coffre == coffre)

    query = query.order_by(models.Secret.domaine, models.Secret.libelle)
    pagination = paginate(query, page)
    domaines, coffres = _get_filters(db)

    return templates.TemplateResponse(request, "secrets/list.html", {
        "user": user, "active": "secrets",
        "flash": get_flash(request),
        "pagination": pagination,
        "q": q, "sel_domaine": domaine, "sel_coffre": coffre,
        "domaines": domaines, "coffres": coffres,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_secret_form(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    domaines, coffres = _get_filters(db)
    return templates.TemplateResponse(request, "secrets/form.html", {
        "user": user, "active": "secrets",
        "secret": None, "domaines": domaines, "coffres": coffres, "errors": {},
    })


@router.post("/", response_class=HTMLResponse)
async def create_secret(
    request: Request,
    id_secret: str = Form(...),
    libelle: str = Form(...),
    nom_technique: str = Form(...),
    domaine: str = Form(...),
    coffre: str = Form(...),
    num_envelope: str = Form(...),
    scan_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = require_responsable(request, db)
    id_secret = id_secret.strip()
    num_envelope = num_envelope.strip()

    errors = {}
    if db.query(models.Secret).filter(models.Secret.id_secret == id_secret).first():
        errors["id_secret"] = "Cet identifiant existe déjà."
    if db.query(models.Secret).filter(models.Secret.num_envelope == num_envelope).first():
        errors["num_envelope"] = "Ce numéro d'enveloppe existe déjà."

    if errors:
        domaines, coffres = _get_filters(db)
        return templates.TemplateResponse(request, "secrets/form.html", {
            "user": user, "active": "secrets",
            "secret": {"id_secret": id_secret, "libelle": libelle,
                       "nom_technique": nom_technique, "domaine": domaine,
                       "coffre": coffre, "num_envelope": num_envelope},
            "domaines": domaines, "coffres": coffres, "errors": errors,
        })

    scan_path = await _save_upload(scan_file)

    secret = models.Secret(
        id_secret=id_secret, libelle=libelle.strip(),
        nom_technique=nom_technique.strip(), domaine=domaine.strip(),
        coffre=coffre.strip(), num_envelope=num_envelope,
        scan_path=scan_path, created_by=user.id, updated_by=user.id,
    )
    db.add(secret)
    db.flush()

    log_history(db, secret.id, "Création", user.id, new_values={
        "id_secret": id_secret, "libelle": libelle, "nom_technique": nom_technique,
        "domaine": domaine, "coffre": coffre, "num_envelope": num_envelope,
    })
    log_activity(db, user, "Création secret", "secret", secret.id, libelle)
    db.commit()

    set_flash(request, f"Secret « {libelle} » créé avec succès.")
    return RedirectResponse(f"/secrets/{secret.id}", status_code=302)


@router.get("/{secret_id}", response_class=HTMLResponse)
async def view_secret(secret_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    secret = db.query(models.Secret).filter(models.Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret introuvable")

    history = (db.query(models.SecretHistory)
               .filter(models.SecretHistory.secret_id == secret_id)
               .order_by(models.SecretHistory.changed_at.desc()).all())

    log_activity(db, user, "Consultation", "secret", secret_id, secret.libelle)
    db.commit()

    return templates.TemplateResponse(request, "secrets/detail.html", {
        "user": user, "active": "secrets",
        "flash": get_flash(request),
        "secret": secret, "history": history, "json": json,
    })


@router.get("/{secret_id}/edit", response_class=HTMLResponse)
async def edit_secret_form(secret_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    secret = db.query(models.Secret).filter(models.Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret introuvable")
    domaines, coffres = _get_filters(db)
    return templates.TemplateResponse(request, "secrets/form.html", {
        "user": user, "active": "secrets",
        "secret": secret, "domaines": domaines, "coffres": coffres, "errors": {},
    })


@router.post("/{secret_id}/edit", response_class=HTMLResponse)
async def edit_secret(
    secret_id: int,
    request: Request,
    libelle: str = Form(...),
    nom_technique: str = Form(...),
    domaine: str = Form(...),
    coffre: str = Form(...),
    scan_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = require_responsable(request, db)
    secret = db.query(models.Secret).filter(models.Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404)

    old_values = {
        "libelle": secret.libelle, "nom_technique": secret.nom_technique,
        "domaine": secret.domaine, "coffre": secret.coffre,
    }

    new_scan = await _save_upload(scan_file)
    secret.libelle = libelle.strip()
    secret.nom_technique = nom_technique.strip()
    secret.domaine = domaine.strip()
    secret.coffre = coffre.strip()
    if new_scan:
        secret.scan_path = new_scan
    secret.updated_by = user.id
    secret.updated_at = datetime.utcnow()

    log_history(db, secret_id, "Modification", user.id, old_values=old_values, new_values={
        "libelle": secret.libelle, "nom_technique": secret.nom_technique,
        "domaine": secret.domaine, "coffre": secret.coffre,
    })
    log_activity(db, user, "Modification secret", "secret", secret_id, secret.libelle)
    db.commit()

    set_flash(request, f"Secret « {secret.libelle} » mis à jour.")
    return RedirectResponse(f"/secrets/{secret_id}", status_code=302)


@router.get("/{secret_id}/envelope", response_class=HTMLResponse)
async def envelope_form(secret_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    secret = db.query(models.Secret).filter(models.Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "secrets/envelope.html", {
        "user": user, "active": "secrets",
        "secret": secret, "error": None,
    })


@router.post("/{secret_id}/envelope", response_class=HTMLResponse)
async def change_envelope(
    secret_id: int,
    request: Request,
    num_envelope: str = Form(...),
    note: str = Form(""),
    scan_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = require_responsable(request, db)
    secret = db.query(models.Secret).filter(models.Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404)

    num_envelope = num_envelope.strip()
    conflict = (db.query(models.Secret)
                .filter(models.Secret.num_envelope == num_envelope,
                        models.Secret.id != secret_id).first())
    if conflict:
        return templates.TemplateResponse(request, "secrets/envelope.html", {
            "user": user, "active": "secrets",
            "secret": secret,
            "error": f"Ce numéro est déjà utilisé par « {conflict.libelle} ».",
        })

    old_num = secret.num_envelope
    new_scan = await _save_upload(scan_file)

    secret.num_envelope = num_envelope
    if new_scan:
        secret.scan_path = new_scan
    secret.updated_by = user.id
    secret.updated_at = datetime.utcnow()

    log_history(db, secret_id, "Changement enveloppe", user.id,
                old_values={"num_envelope": old_num},
                new_values={"num_envelope": num_envelope},
                note=note.strip() or None)
    log_activity(db, user, "Changement enveloppe", "secret", secret_id,
                 f"{old_num} → {num_envelope}")
    db.commit()

    set_flash(request, f"Enveloppe mise à jour : {old_num} → {num_envelope}")
    return RedirectResponse(f"/secrets/{secret_id}", status_code=302)


async def _save_upload(upload: UploadFile) -> str | None:
    if not upload or not upload.filename:
        return None
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}:
        return None
    filename = f"{uuid.uuid4()}{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(await upload.read())
    return f"scans/{filename}"
