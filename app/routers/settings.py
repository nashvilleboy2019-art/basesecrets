import os
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils import require_responsable, set_flash, get_flash
from app.templates_config import templates
from app import settings_manager

router = APIRouter()

_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
_MAX_LOGO = 2 * 1024 * 1024  # 2 Mo


@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = require_responsable(request, db)
    cfg = settings_manager.load()
    return templates.TemplateResponse(request, "settings/index.html", {
        "user": user, "active": "settings",
        "flash": get_flash(request),
        "cfg": cfg,
        "logo_url": _current_logo_url(),
    })


@router.post("/general")
async def save_general(
    request: Request,
    company_name: str = Form(""),
    db: Session = Depends(get_db)
):
    require_responsable(request, db)
    settings_manager.save({"company_name": company_name.strip()})
    set_flash(request, "Paramètres généraux enregistrés.")
    return RedirectResponse("/settings/", status_code=302)


@router.post("/logo")
async def upload_logo(
    request: Request,
    logo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    require_responsable(request, db)
    ext = os.path.splitext(logo.filename or "")[1].lower()
    if ext not in _LOGO_EXTS:
        set_flash(request, "Format non supporté. Utilisez PNG, JPG, GIF, SVG ou WEBP.", "error")
        return RedirectResponse("/settings/", status_code=302)

    content = await logo.read()
    if len(content) > _MAX_LOGO:
        set_flash(request, "Fichier trop volumineux (max 2 Mo).", "error")
        return RedirectResponse("/settings/", status_code=302)

    _delete_logo_files()
    dest = os.path.join("uploads", f"logo_custom{ext}")
    with open(dest, "wb") as f:
        f.write(content)

    settings_manager.save({"logo_ext": ext})
    set_flash(request, "Logo mis à jour.")
    return RedirectResponse("/settings/", status_code=302)


@router.post("/logo/delete")
async def delete_logo(request: Request, db: Session = Depends(get_db)):
    require_responsable(request, db)
    _delete_logo_files()
    settings_manager.save({"logo_ext": ""})
    set_flash(request, "Logo supprimé.")
    return RedirectResponse("/settings/", status_code=302)


@router.post("/ldap")
async def save_ldap(
    request: Request,
    ldap_enabled: str = Form(""),
    ldap_server: str = Form(""),
    ldap_port: int = Form(389),
    ldap_user_template: str = Form(""),
    ldap_default_role: str = Form("auditeur"),
    ldap_bind_dn: str = Form(""),
    ldap_bind_password: str = Form(""),
    db: Session = Depends(get_db)
):
    require_responsable(request, db)
    update = {
        "ldap_enabled": ldap_enabled == "on",
        "ldap_server": ldap_server.strip(),
        "ldap_port": max(1, min(65535, ldap_port)),
        "ldap_user_template": ldap_user_template.strip() or "{username}@domain.local",
        "ldap_default_role": ldap_default_role if ldap_default_role in ("auditeur", "responsable") else "auditeur",
        "ldap_bind_dn": ldap_bind_dn.strip(),
    }
    if ldap_bind_password:
        update["ldap_bind_password"] = ldap_bind_password
    settings_manager.save(update)
    set_flash(request, "Configuration Active Directory enregistrée.")
    return RedirectResponse("/settings/", status_code=302)


@router.get("/ldap/test")
async def test_ldap(request: Request, db: Session = Depends(get_db)):
    require_responsable(request, db)
    try:
        from ldap3 import Server, Connection
    except ImportError:
        return JSONResponse({"ok": False, "message": "Module ldap3 non installé — exécutez : pip install ldap3"})

    cfg = settings_manager.load()
    if not cfg.get("ldap_server"):
        return JSONResponse({"ok": False, "message": "Adresse du serveur non renseignée."})

    try:
        server = Server(cfg["ldap_server"], port=int(cfg.get("ldap_port", 389)), connect_timeout=5)
        conn = Connection(server, auto_bind=False)
        conn.open()
        return JSONResponse({"ok": True, "message": f"Serveur {cfg['ldap_server']}:{cfg.get('ldap_port', 389)} joignable."})
    except Exception as e:
        return JSONResponse({"ok": False, "message": f"Échec : {e}"})


def _current_logo_url() -> str | None:
    for ext in _LOGO_EXTS:
        path = os.path.join("uploads", f"logo_custom{ext}")
        if os.path.exists(path):
            return f"/uploads/logo_custom{ext}"
    return None


def _delete_logo_files():
    for ext in _LOGO_EXTS:
        path = os.path.join("uploads", f"logo_custom{ext}")
        if os.path.exists(path):
            os.remove(path)
