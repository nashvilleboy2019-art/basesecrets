import os
import uvicorn

os.makedirs("data", exist_ok=True)
os.makedirs(os.path.join("uploads", "scans"), exist_ok=True)
os.makedirs("static", exist_ok=True)

from app.database import engine
from app import models
from app.database import SessionLocal
from app.auth import create_default_users

if __name__ == "__main__":
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    create_default_users(db)
    db.close()
    print("\n  BaseSecrets démarré sur http://127.0.0.1:8000\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
