import bcrypt
from sqlalchemy.orm import Session
from app import models


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return None
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
