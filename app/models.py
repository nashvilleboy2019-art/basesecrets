from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="auditeur")
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def display_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.username


class Secret(Base):
    __tablename__ = "secrets"
    id = Column(Integer, primary_key=True, index=True)
    id_secret = Column(String(100), unique=True, nullable=False, index=True)
    libelle = Column(String(255), nullable=False)
    nom_technique = Column(String(255), nullable=False)
    domaine = Column(String(100), nullable=False, index=True)
    coffre = Column(String(100), nullable=False, index=True)
    num_envelope = Column(String(100), unique=True, nullable=False, index=True)
    scan_path = Column(String(500), nullable=True)
    archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    history = relationship(
        "SecretHistory",
        back_populates="secret",
        order_by="SecretHistory.changed_at.desc()"
    )
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])


class SecretHistory(Base):
    __tablename__ = "secrets_history"
    id = Column(Integer, primary_key=True, index=True)
    secret_id = Column(Integer, ForeignKey("secrets.id"), nullable=False)
    action = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    note = Column(String(500), nullable=True)

    secret = relationship("Secret", back_populates="history")
    user = relationship("User", foreign_keys=[changed_by])


class AuditSession(Base):
    __tablename__ = "audit_sessions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    year = Column(Integer, nullable=False)
    coffre = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="open")

    checks = relationship("AuditCheck", back_populates="session")
    creator = relationship("User", foreign_keys=[created_by])


class AuditCheck(Base):
    __tablename__ = "audit_checks"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("audit_sessions.id"), nullable=False)
    num_envelope_scanned = Column(String(100), nullable=False)
    secret_id = Column(Integer, ForeignKey("secrets.id"), nullable=True)
    status = Column(String(20), nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow)
    checked_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    session = relationship("AuditSession", back_populates="checks")
    secret = relationship("Secret")
    checker = relationship("User", foreign_keys=[checked_by])


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    resource = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
