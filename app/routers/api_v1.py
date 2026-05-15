from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime, date
from hashlib import sha256

from app.database import get_db
from app import models

router = APIRouter()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _check_key(api_key: str = Security(_api_key_header), db: Session = Depends(get_db)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Clé API absente.")
    key_hash = sha256(api_key.encode()).hexdigest()
    k = db.query(models.ApiKey).filter(
        models.ApiKey.key_hash == key_hash,
        models.ApiKey.is_active == True,
    ).first()
    if not k:
        raise HTTPException(status_code=401, detail="Clé API invalide ou absente.")
    k.last_used_at = datetime.utcnow()
    db.commit()
    return api_key


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: str = Depends(_check_key)):
    users = db.query(models.User).order_by(models.User.last_name, models.User.first_name).all()
    return [
        {
            "id":         u.id,
            "username":   u.username,
            "first_name": u.first_name or "",
            "last_name":  u.last_name or "",
            "nom_prenom": f"{(u.last_name or '').upper()} {(u.first_name or '').capitalize()}".strip(),
            "role":       u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/connections")
def list_connections(
    from_date: str = Query(None, description="YYYY-MM-DD"),
    to_date:   str = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: str = Depends(_check_key),
):
    """Retourne les événements de connexion (action='Connexion') sur la période."""
    q = db.query(models.ActivityLog).filter(models.ActivityLog.action == "Connexion")
    if from_date:
        q = q.filter(models.ActivityLog.timestamp >= datetime.fromisoformat(from_date))
    if to_date:
        # inclusif : jusqu'à la fin du jour to_date
        to_dt = datetime.fromisoformat(to_date).replace(hour=23, minute=59, second=59)
        q = q.filter(models.ActivityLog.timestamp <= to_dt)
    entries = q.order_by(models.ActivityLog.timestamp.desc()).all()
    return [
        {
            "username":  e.username,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in entries
    ]
