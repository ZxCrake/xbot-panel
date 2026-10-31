"""Database layer — SQLAlchemy engine, session, and ORM models.

Tables: users, audit_logs. All access goes through the ORM (parameterized,
so no SQL injection surface).
"""
import datetime as dt
import uuid
import os
import datetime

from sqlalchemy import (
    create_engine, String, Integer, Boolean, DateTime, Text, Index,
    inspect,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, sessionmaker, scoped_session

from . import settings


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


# Note: columns are declared without `Mapped[...]` generics on purpose — this
# keeps the models compatible across Python versions (PEP 604 unions in Mapped
# annotations break under some interpreter/SQLAlchemy combinations).
class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True)
    username = mapped_column(String(32), unique=True, index=True, nullable=False)
    workspace_key = mapped_column(String(64), unique=True, nullable=False,
                                  default=lambda: "u-" + uuid.uuid4().hex)
    password_hash = mapped_column(String(255), nullable=False)
    role = mapped_column(String(16), default="user", nullable=False)
    is_active = mapped_column(Boolean, default=True, nullable=False)

    # Auth / session control
    token_version = mapped_column(Integer, default=1, nullable=False)
    failed_logins = mapped_column(Integer, default=0, nullable=False)
    locked_until = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at = mapped_column(DateTime(timezone=True), nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = mapped_column(Integer, primary_key=True)
    ts = mapped_column(DateTime(timezone=True), default=_utcnow, index=True, nullable=False)
    username = mapped_column(String(32), index=True, nullable=True)
    action = mapped_column(String(64), nullable=False)
    detail = mapped_column(Text, nullable=True)
    ip = mapped_column(String(64), nullable=True)


Index("ix_audit_ts_action", AuditLog.ts, AuditLog.action)


# ── Engine / session ──────────────────────────────────────────────────────────
_engine = None
SessionLocal: scoped_session = None  # type: ignore


def init_engine(database_url: str | None = None):
    """Create the engine + session factory. Idempotent."""
    global _engine, SessionLocal
    if _engine is not None:
        return _engine
    url = database_url or settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(
        url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    SessionLocal = scoped_session(sessionmaker(bind=_engine, expire_on_commit=False, future=True))
    return _engine


def get_engine():
    return _engine or init_engine()


def create_all():
    """Create tables if they don't exist (used for SQLite/dev bootstrap)."""
    Base.metadata.create_all(get_engine())


def upgrade_schema():
    """Upgrade both Alembic-managed and original create_all databases.

    Run during startup with web workers stopped. No user data is relocated.
    A legacy SQLite database is backed up before its first schema upgrade.
    """
    from alembic import command
    from alembic.config import Config
    engine = get_engine()
    inspector = inspect(engine)
    config = Config(os.path.join(settings.BASE_DIR, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(settings.BASE_DIR, "migrations"))
    # migrations/env.py only calls fileConfig() when config_file_name is set.
    # Letting it run would disable the "xbot" logger and replace the root
    # handlers configured by logging_config — after that the app logs nothing
    # (console or file). Keep the application logging configuration intact.
    config.config_file_name = None
    if inspector.has_table("users") and not inspector.has_table("alembic_version"):
        columns = {col["name"] for col in inspector.get_columns("users")}
        expected = {col.name for col in User.__table__.columns} - {"workspace_key"}
        if not expected.issubset(columns) or not inspector.has_table("audit_logs"):
            raise RuntimeError("Unrecognized database schema; manual migration required")
        if "workspace_key" not in columns and engine.dialect.name == "sqlite":
            import sqlite3
            database = engine.url.database
            if database and database != ":memory:":
                backup = database + ".before-workspaces-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".bak"
                with sqlite3.connect(database) as source, sqlite3.connect(backup) as dest:
                    source.backup(dest)
        command.stamp(config, "0002" if "workspace_key" in columns else "0001")
    command.upgrade(config, "head")


def session():
    """Return the scoped session (one per thread)."""
    if SessionLocal is None:
        init_engine()
    return SessionLocal
