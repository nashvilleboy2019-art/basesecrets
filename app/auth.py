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
    if not re.match(r"^[\w.\-@\\]+$", username) or not password:
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

    # Vérification OU / groupe si configuré
    allowed_ou = cfg.get("ldap_allowed_ou", "").strip()
    required_group = cfg.get("ldap_required_group", "").strip()

    if allowed_ou or required_group:
        # Extraire le sAMAccountName (partie avant @ ou après \)
        short = username.split("@")[0] if "@" in username else username
        if "\\" in short:
            short = short.split("\\")[-1]
        # Neutraliser les caractères LDAP spéciaux dans le filtre
        short = re.sub(r'[\\*\(\)\x00/]', '', short)

        # Utiliser le compte de service si disponible, sinon la connexion de l'utilisateur
        search_conn = conn
        bind_dn = cfg.get("ldap_bind_dn", "").strip()
        bind_pw = cfg.get("ldap_bind_password", "").strip()
        if bind_dn and bind_pw:
            try:
                svc = Connection(server, user=bind_dn, password=bind_pw, auto_bind=True)
                if svc.bound:
                    search_conn = svc
            except Exception:
                pass

        search_base = allowed_ou or cfg.get("ldap_base_dn", "")
        search_conn.search(
            search_base=search_base,
            search_filter=f"(sAMAccountName={short})",
            attributes=["memberOf", "distinguishedName"],
        )

        if not search_conn.entries:
            # Utilisateur introuvable dans l'OU autorisé
            return None

        if required_group:
            member_of = [str(g).strip() for g in search_conn.entries[0].memberOf]
            if not any(g.lower() == required_group.lower() for g in member_of):
                # Utilisateur non membre du groupe requis
                return None

    # Authentification réussie — créer ou récupérer le compte local
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
