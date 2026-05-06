"""
Remet la base de donnees a zero : supprime toutes les donnees et recrée
les deux comptes par defaut (admin / auditeur).

Usage : python demo_reset.py
"""
import os

os.makedirs("data", exist_ok=True)
os.makedirs(os.path.join("uploads", "scans"), exist_ok=True)

from app.database import engine, SessionLocal
from app import models
from app.auth import hash_password

# Supprime et recrée toutes les tables
models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()
db.add_all([
    models.User(username="admin",    password_hash=hash_password("noukie2017"), role="responsable"),
    models.User(username="auditeur", password_hash=hash_password("audit123"),   role="auditeur"),
])
db.commit()
db.close()

print("Base remise a zero.")
print("Comptes : admin / noukie2017  |  auditeur / audit123")
