import bcrypt
import re
from sqlalchemy.orm import Session
from app import models


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def authenticate_user(db: Session, username: str, password: str):
    from app import settings_manager
    cfg = settings_manager.load()

    if cfg.get("ldap_enabled") and cfg.get("ldap_server"):
        ldap_user = _authenticate_ldap(db, username, password, cfg)
        if ldap_user:
            return ldap_user

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def _authenticate_ldap(db: Session, username: str, password: str, cfg: dict):
    # Reject usernames with LDAP special characters to prevent injection
    if not re.match(r"^[\w.\-@]+$", username) or not password:
        return None

    try:
        from ldap3 import Server, Connection
    except ImportError:
        return None

    template = cfg.get("ldap_user_template", "{username}@domain.local")
    user_dn = template.replace("{username}", username)

    try:
        server = Server(cfg["ldap_server"], port=int(cfg.get("ldap_port", 389)), connect_timeout=5)
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        if not conn.bound:
            return None
    except Exception:
        return None

    # Auth succeeded — get or create local user record
    role = cfg.get("ldap_default_role", "auditeur")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        user = models.User(
            username=username,
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.flush()
    return user


def create_default_users(db: Session):
    if db.query(models.User).count() == 0:
        db.add_all([
            models.User(
                username="admin",
                password_hash=hash_password("noukie2017"),
                role="responsable"
            ),
            models.User(
                username="auditeur",
                password_hash=hash_password("audit123"),
                role="auditeur"
            ),
        ])
        db.commit()
        print("Utilisateurs par défaut créés : admin / noukie2017  |  auditeur / audit123")
        print("IMPORTANT : changez ces mots de passe après la première connexion.")
