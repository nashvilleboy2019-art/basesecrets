"""
Script de peuplement avec données fictives réalistes pour screenshots.
Lance : python populate_demo.py
"""
import os, json
from datetime import datetime, timedelta

os.makedirs("data", exist_ok=True)
os.makedirs(os.path.join("uploads", "scans"), exist_ok=True)

from app.database import engine, SessionLocal
from app import models
from app.auth import hash_password

models.Base.metadata.create_all(bind=engine)

# Migrations
from sqlalchemy import text, inspect as sa_inspect
inspector = sa_inspect(engine)
with engine.connect() as conn:
    audit_cols = [c["name"] for c in inspector.get_columns("audit_sessions")]
    if "coffre" not in audit_cols:
        conn.execute(text("ALTER TABLE audit_sessions ADD COLUMN coffre VARCHAR(100)"))
    secret_cols = [c["name"] for c in inspector.get_columns("secrets")]
    if "archived" not in secret_cols:
        conn.execute(text("ALTER TABLE secrets ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0"))
    conn.commit()

db = SessionLocal()

# ── Comptes utilisateurs ─────────────────────────────────────────────────────
admin = db.query(models.User).filter_by(username="admin").first()
if not admin:
    admin = models.User(username="admin", password_hash=hash_password("noukie2017"), role="responsable")
    db.add(admin)

auditeur = db.query(models.User).filter_by(username="auditeur").first()
if not auditeur:
    auditeur = models.User(username="auditeur", password_hash=hash_password("audit123"), role="auditeur")
    db.add(auditeur)

jmartin = db.query(models.User).filter_by(username="j.martin").first()
if not jmartin:
    jmartin = models.User(username="j.martin", password_hash=hash_password("Martin2024!"), role="responsable")
    db.add(jmartin)

db.flush()

# ── Secrets ───────────────────────────────────────────────────────────────────
SECRETS = [
    # (id_secret, libelle, nom_technique, domaine, coffre, num_envelope, archived)
    ("AD_ADMIN_DA",   "Compte DA de break-glass",       "DC01.acme.local",     "Active Directory",  "Coffre 1 — Salle serveurs", "ENV-2024-001", False),
    ("AD_KRBTGT",     "Compte KRBTGT (réinitialisation)","DC01.acme.local",     "Active Directory",  "Coffre 1 — Salle serveurs", "ENV-2024-002", False),
    ("AD_DSRM",       "Mot de passe DSRM",               "DC01.acme.local",     "Active Directory",  "Coffre 1 — Salle serveurs", "ENV-2024-003", False),
    ("SQL_SA_PROD",   "SA SQL Server production",        "SRV-SQL01.acme.local","Bases de données",  "Coffre 1 — Salle serveurs", "ENV-2024-004", False),
    ("SQL_SA_BACKUP", "SA SQL Server backup",            "SRV-SQL02.acme.local","Bases de données",  "Coffre 1 — Salle serveurs", "ENV-2024-005", False),
    ("ORACLE_SYS",    "SYS Oracle ERP",                  "SRV-ORA01.acme.local","Bases de données",  "Coffre 1 — Salle serveurs", "ENV-2024-006", False),
    ("VMWARE_ROOT",   "Root vCenter",                    "vcenter01.acme.local","Infrastructure",    "Coffre 1 — Salle serveurs", "ENV-2024-007", False),
    ("ILO_ADMIN",     "Admin iLO HP ProLiant",           "SRV-HP-01",           "Infrastructure",    "Coffre 1 — Salle serveurs", "ENV-2024-008", False),
    ("BACKUP_VEEAM",  "Compte service Veeam Backup",     "SRV-BACKUP01",        "Infrastructure",    "Coffre 1 — Salle serveurs", "ENV-2024-009", False),
    ("FW_DATACENTER", "Admin Firewall datacenter",       "FW-DC-01.acme.local", "Réseau",            "Coffre 1 — Salle serveurs", "ENV-2024-010", False),
    ("SW_CORE_ENABLE","Enable switch cœur de réseau",    "SW-CORE-01",          "Réseau",            "Coffre 1 — Salle serveurs", "ENV-2024-011", False),
    ("WIFI_PSK_CORP", "Clé WPA2 réseau Corp",            "AP-UNIFI-CTRL",       "Réseau",            "Coffre 1 — Salle serveurs", "ENV-2024-012", False),
    ("ERP_ADMIN",     "Administrateur SAP ERP",          "SAP-PROD.acme.local", "Applications",      "Coffre 2 — Direction",      "ENV-2024-013", False),
    ("CRM_ADMIN",     "Admin Salesforce CRM",            "acme.salesforce.com", "Applications",      "Coffre 2 — Direction",      "ENV-2024-014", False),
    ("AZURE_GA",      "Compte Global Admin Azure",       "portail.azure.com",   "Cloud",             "Coffre 2 — Direction",      "ENV-2024-015", False),
    ("AWS_ROOT",      "Compte root AWS",                 "console.aws.amazon.com","Cloud",           "Coffre 2 — Direction",      "ENV-2024-016", False),
    ("EXCHANGE_ADMIN","Admin Exchange on-premise",       "SRV-EXCH01.acme.local","Messagerie",       "Coffre 2 — Direction",      "ENV-2024-017", False),
    ("SMTP_RELAY",    "Compte relais SMTP sortant",      "smtp.acme.local",     "Messagerie",        "Coffre 2 — Direction",      "ENV-2024-018", False),
    # Secret archivé (ancien système)
    ("OLD_PROXY_ADMIN","Admin proxy Squid (décommissionné)","SRV-PROXY-OLD",    "Réseau",            "Coffre 1 — Salle serveurs", "ENV-2022-088", True),
]

created_secrets = {}
t_base = datetime(2024, 1, 15, 9, 0, 0)

for i, (id_s, libelle, nom_tech, domaine, coffre, num_env, archived) in enumerate(SECRETS):
    existing = db.query(models.Secret).filter_by(id_secret=id_s).first()
    if existing:
        created_secrets[id_s] = existing
        continue

    t = t_base + timedelta(days=i * 3, hours=i % 8)
    s = models.Secret(
        id_secret=id_s, libelle=libelle, nom_technique=nom_tech,
        domaine=domaine, coffre=coffre, num_envelope=num_env,
        archived=archived,
        created_by=admin.id, updated_by=admin.id,
        created_at=t, updated_at=t,
    )
    db.add(s)
    db.flush()
    created_secrets[id_s] = s

    db.add(models.SecretHistory(
        secret_id=s.id, action="Création", changed_by=admin.id,
        changed_at=t,
        new_values=json.dumps({"id_secret": id_s, "libelle": libelle,
                               "nom_technique": nom_tech, "domaine": domaine,
                               "coffre": coffre, "num_envelope": num_env}),
    ))
    db.add(models.ActivityLog(
        user_id=admin.id, username="admin",
        action="Création secret", resource="secret",
        resource_id=str(s.id), details=libelle,
        timestamp=t,
    ))

# Changement d'enveloppe sur AD_ADMIN_DA (simulation d'une ouverture d'enveloppe)
s_da = created_secrets.get("AD_ADMIN_DA")
if s_da and s_da.num_envelope == "ENV-2024-001":
    t_change = datetime(2024, 6, 12, 14, 30, 0)
    old_env = "ENV-2024-001"
    new_env = "ENV-2024-001B"
    existing_change = db.query(models.SecretHistory).filter_by(
        secret_id=s_da.id, action="Changement enveloppe"
    ).first()
    if not existing_change:
        s_da.num_envelope = new_env
        s_da.updated_at = t_change
        db.add(models.SecretHistory(
            secret_id=s_da.id, action="Changement enveloppe",
            changed_by=jmartin.id, changed_at=t_change,
            old_values=json.dumps({"num_envelope": old_env}),
            new_values=json.dumps({"num_envelope": new_env}),
            note="Rotation planifiée post-départ salarié — Jean Dupont (DSI)",
        ))
        db.add(models.ActivityLog(
            user_id=jmartin.id, username="j.martin",
            action="Changement enveloppe", resource="secret",
            resource_id=str(s_da.id),
            details=f"{old_env} → {new_env}",
            timestamp=t_change,
        ))

db.flush()

# ── Sessions d'audit ──────────────────────────────────────────────────────────
# Audit 2023 clôturé — Coffre 1
if not db.query(models.AuditSession).filter_by(name="Audit annuel 2023").first():
    t_audit_2023 = datetime(2023, 11, 14, 8, 30, 0)
    sess_2023 = models.AuditSession(
        name="Audit annuel 2023", year=2023,
        coffre=None,
        created_by=auditeur.id, status="closed",
        created_at=t_audit_2023,
        closed_at=datetime(2023, 11, 14, 11, 45, 0),
    )
    db.add(sess_2023)
    db.flush()

    # Scans : tous les ENV-2022-* et ENV-2024-* qui existaient à l'époque
    envelopes_2023 = [
        ("ENV-2022-088", True),   # proxy archivé — existait encore
        ("ENV-2024-001", True),   # AD_ADMIN_DA
        ("ENV-2024-002", True),
        ("ENV-2024-003", True),
        ("ENV-2024-004", True),
        ("ENV-2024-005", True),
        ("ENV-2024-099", False),  # enveloppe inconnue
    ]
    for env_num, known in envelopes_2023:
        secret = db.query(models.Secret).filter(
            models.Secret.num_envelope == env_num
        ).first() if known else None
        # Pour les archivés, utiliser l'ancien num
        if env_num == "ENV-2022-088":
            secret = db.query(models.Secret).filter_by(id_secret="OLD_PROXY_ADMIN").first()
        t_scan = t_audit_2023 + timedelta(minutes=envelopes_2023.index((env_num, known)) * 4)
        db.add(models.AuditCheck(
            session_id=sess_2023.id,
            num_envelope_scanned=env_num,
            secret_id=secret.id if secret else None,
            status="match" if secret else "unknown",
            checked_by=auditeur.id,
            checked_at=t_scan,
        ))
    db.add(models.ActivityLog(
        user_id=auditeur.id, username="auditeur",
        action="Création session audit", resource="audit",
        resource_id=str(sess_2023.id), details="Audit annuel 2023",
        timestamp=t_audit_2023,
    ))
    db.add(models.ActivityLog(
        user_id=auditeur.id, username="auditeur",
        action="Clôture session audit", resource="audit",
        resource_id=str(sess_2023.id), details="Audit annuel 2023",
        timestamp=datetime(2023, 11, 14, 11, 45, 0),
    ))

# Audit 2024 clôturé — Coffre 1
if not db.query(models.AuditSession).filter_by(name="Audit annuel 2024 — Coffre 1").first():
    t_audit_c1 = datetime(2024, 10, 8, 9, 0, 0)
    sess_c1 = models.AuditSession(
        name="Audit annuel 2024 — Coffre 1", year=2024,
        coffre="Coffre 1 — Salle serveurs",
        created_by=auditeur.id, status="closed",
        created_at=t_audit_c1,
        closed_at=datetime(2024, 10, 8, 10, 20, 0),
    )
    db.add(sess_c1)
    db.flush()

    coffre1_ids = ["AD_ADMIN_DA","AD_KRBTGT","AD_DSRM","SQL_SA_PROD","SQL_SA_BACKUP",
                   "ORACLE_SYS","VMWARE_ROOT","ILO_ADMIN","BACKUP_VEEAM",
                   "FW_DATACENTER","SW_CORE_ENABLE","WIFI_PSK_CORP"]
    for idx, sid in enumerate(coffre1_ids):
        s = created_secrets.get(sid)
        if not s:
            continue
        t_sc = t_audit_c1 + timedelta(minutes=idx * 3 + 1)
        db.add(models.AuditCheck(
            session_id=sess_c1.id,
            num_envelope_scanned=s.num_envelope,
            secret_id=s.id,
            status="match",
            checked_by=auditeur.id,
            checked_at=t_sc,
        ))
    # 1 inconnu simulé
    db.add(models.AuditCheck(
        session_id=sess_c1.id,
        num_envelope_scanned="ENV-2024-099",
        secret_id=None,
        status="unknown",
        checked_by=auditeur.id,
        checked_at=t_audit_c1 + timedelta(minutes=40),
    ))
    db.add(models.ActivityLog(
        user_id=auditeur.id, username="auditeur",
        action="Création session audit", resource="audit",
        resource_id=str(sess_c1.id), details="Audit annuel 2024 — Coffre 1",
        timestamp=t_audit_c1,
    ))
    db.add(models.ActivityLog(
        user_id=auditeur.id, username="auditeur",
        action="Clôture session audit", resource="audit",
        resource_id=str(sess_c1.id), details="Audit annuel 2024 — Coffre 1",
        timestamp=datetime(2024, 10, 8, 10, 20, 0),
    ))

# Audit 2024 en cours — Coffre 2
if not db.query(models.AuditSession).filter_by(name="Audit annuel 2024 — Coffre 2").first():
    t_audit_c2 = datetime(2024, 10, 9, 14, 0, 0)
    sess_c2 = models.AuditSession(
        name="Audit annuel 2024 — Coffre 2", year=2024,
        coffre="Coffre 2 — Direction",
        created_by=auditeur.id, status="open",
        created_at=t_audit_c2,
    )
    db.add(sess_c2)
    db.flush()

    # Partiellement scanné (4 sur 6)
    partial_ids = ["ERP_ADMIN","CRM_ADMIN","AZURE_GA","EXCHANGE_ADMIN"]
    for idx, sid in enumerate(partial_ids):
        s = created_secrets.get(sid)
        if not s:
            continue
        t_sc = t_audit_c2 + timedelta(minutes=idx * 2 + 1)
        db.add(models.AuditCheck(
            session_id=sess_c2.id,
            num_envelope_scanned=s.num_envelope,
            secret_id=s.id,
            status="match",
            checked_by=auditeur.id,
            checked_at=t_sc,
        ))
    db.add(models.ActivityLog(
        user_id=auditeur.id, username="auditeur",
        action="Création session audit", resource="audit",
        resource_id=str(sess_c2.id), details="Audit annuel 2024 — Coffre 2",
        timestamp=t_audit_c2,
    ))

db.commit()
db.close()

print("\n  OK - Donnees de demonstration chargees avec succes !")
print("  Secrets      :", len(SECRETS), "(dont 1 archive)")
print("  Sessions      : Audit 2023 (cloture), Audit 2024 Coffre 1 (cloture), Audit 2024 Coffre 2 (en cours)")
print("  Comptes       : admin / noukie2017  |  j.martin / Martin2024!  |  auditeur / audit123\n")
