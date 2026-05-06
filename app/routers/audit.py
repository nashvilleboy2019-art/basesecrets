from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app import models
from app.utils import require_login, log_activity, set_flash, get_flash
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def list_sessions(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    sessions = (db.query(models.AuditSession)
                .order_by(models.AuditSession.created_at.desc()).all())

    for s in sessions:
        total = len(s.checks)
        s._total = total
        s._match = sum(1 for c in s.checks if c.status == "match")
        s._unknown = total - s._match

    return templates.TemplateResponse(request, "audit/list.html", {
        "user": user, "active": "audit",
        "flash": get_flash(request), "sessions": sessions,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_session_form(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    coffres = [r[0] for r in db.query(models.Secret.coffre).distinct().order_by(models.Secret.coffre).all()]
    return templates.TemplateResponse(request, "audit/new.html", {
        "user": user, "active": "audit",
        "current_year": datetime.utcnow().year,
        "coffres": coffres,
    })


@router.post("/", response_class=HTMLResponse)
async def create_session(
    request: Request,
    name: str = Form(...),
    year: int = Form(...),
    coffre: str = Form(""),
    db: Session = Depends(get_db)
):
    user = require_login(request, db)
    coffre_val = coffre.strip() or None
    session = models.AuditSession(
        name=name.strip(), year=year,
        coffre=coffre_val,
        created_by=user.id, status="open"
    )
    db.add(session)
    db.flush()
    scope = f" (coffre : {coffre_val})" if coffre_val else ""
    log_activity(db, user, f"Création session audit{scope}", "audit", session.id, name)
    db.commit()
    set_flash(request, f"Session « {name} » créée.")
    return RedirectResponse(f"/audit/{session.id}", status_code=302)


@router.get("/{session_id}", response_class=HTMLResponse)
async def scan_session(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    session = db.query(models.AuditSession).filter(models.AuditSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    checks = (db.query(models.AuditCheck)
              .filter(models.AuditCheck.session_id == session_id)
              .order_by(models.AuditCheck.checked_at.desc()).all())
    stats = {
        "match": sum(1 for c in checks if c.status == "match"),
        "unknown": sum(1 for c in checks if c.status == "unknown"),
        "total": len(checks),
    }

    return templates.TemplateResponse(request, "audit/session.html", {
        "user": user, "active": "audit",
        "session": session, "checks": checks, "stats": stats,
    })


@router.post("/{session_id}/scan")
async def scan_envelope(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    session = (db.query(models.AuditSession)
               .filter(models.AuditSession.id == session_id).first())
    if not session or session.status != "open":
        return JSONResponse({"error": "Session invalide ou déjà clôturée."}, status_code=400)

    body = await request.json()
    num = (body.get("num_envelope") or "").strip()
    if not num:
        return JSONResponse({"error": "Numéro vide."}, status_code=400)

    already = (db.query(models.AuditCheck)
               .filter(models.AuditCheck.session_id == session_id,
                       models.AuditCheck.num_envelope_scanned == num).first())
    if already:
        return JSONResponse({"error": "duplicate",
                             "message": f"« {num} » déjà scanné dans cette session."},
                            status_code=409)

    secret = db.query(models.Secret).filter(models.Secret.num_envelope == num).first()
    status = "match" if secret else "unknown"

    db.add(models.AuditCheck(
        session_id=session_id,
        num_envelope_scanned=num,
        secret_id=secret.id if secret else None,
        status=status,
        checked_by=user.id,
    ))
    db.commit()

    return JSONResponse({
        "status": status,
        "num_envelope": num,
        "secret": {
            "id": secret.id,
            "libelle": secret.libelle,
            "nom_technique": secret.nom_technique,
            "domaine": secret.domaine,
            "coffre": secret.coffre,
        } if secret else None,
    })


@router.post("/{session_id}/close")
async def close_session(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    session = db.query(models.AuditSession).filter(models.AuditSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)
    session.status = "closed"
    session.closed_at = datetime.utcnow()
    log_activity(db, user, "Clôture session audit", "audit", session_id, session.name)
    db.commit()
    set_flash(request, f"Session « {session.name} » clôturée.")
    return RedirectResponse(f"/audit/{session_id}/report", status_code=302)


@router.get("/{session_id}/report", response_class=HTMLResponse)
async def session_report(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    session = db.query(models.AuditSession).filter(models.AuditSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404)

    checks = (db.query(models.AuditCheck)
              .filter(models.AuditCheck.session_id == session_id)
              .order_by(models.AuditCheck.checked_at).all())

    scanned_secret_ids = {c.secret_id for c in checks if c.secret_id}
    q = db.query(models.Secret).filter(models.Secret.archived == False)
    if session.coffre:
        q = q.filter(models.Secret.coffre == session.coffre)
    all_secrets = q.order_by(models.Secret.domaine, models.Secret.libelle).all()
    missing = [s for s in all_secrets if s.id not in scanned_secret_ids]

    match_checks = [c for c in checks if c.status == "match"]
    unknown_checks = [c for c in checks if c.status == "unknown"]

    return templates.TemplateResponse(request, "audit/report.html", {
        "user": user, "active": "audit",
        "flash": get_flash(request),
        "session": session,
        "match_checks": match_checks,
        "unknown_checks": unknown_checks,
        "missing": missing,
        "stats": {
            "total_scanned": len(checks),
            "match": len(match_checks),
            "unknown": len(unknown_checks),
            "missing": len(missing),
            "total_db": len(all_secrets),
        },
    })
