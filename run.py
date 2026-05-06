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

    host = os.environ.get("BASESECRETS_HOST", "127.0.0.1")
    port = int(os.environ.get("BASESECRETS_PORT", "8000"))
    reload = os.environ.get("BASESECRETS_RELOAD", "true").lower() != "false"

    print(f"\n  BaseSecrets démarré sur http://{host}:{port}\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
