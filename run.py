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

    # Migrations pour les nouvelles colonnes
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(engine)
    with engine.connect() as conn:
        audit_cols = [c["name"] for c in inspector.get_columns("audit_sessions")]
        if "coffre" not in audit_cols:
            conn.execute(text("ALTER TABLE audit_sessions ADD COLUMN coffre VARCHAR(100)"))
            print("  Migration : colonne 'coffre' ajoutée à audit_sessions")
        secret_cols = [c["name"] for c in inspector.get_columns("secrets")]
        if "archived" not in secret_cols:
            conn.execute(text("ALTER TABLE secrets ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0"))
            print("  Migration : colonne 'archived' ajoutée à secrets")
        conn.commit()

    db = SessionLocal()
    create_default_users(db)
    db.close()

    host = os.environ.get("BASESECRETS_HOST", "127.0.0.1")
    port = int(os.environ.get("BASESECRETS_PORT", "8000"))
    reload = os.environ.get("BASESECRETS_RELOAD", "true").lower() != "false"

    print(f"\n  BaseSecrets démarré sur http://{host}:{port}\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
