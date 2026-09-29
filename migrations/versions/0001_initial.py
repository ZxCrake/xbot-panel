"""initial schema: users + audit_logs

Revision ID: 0001
Revises:
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("failed_logins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_audit_logs_ts", "audit_logs", ["ts"])
    op.create_index("ix_audit_logs_username", "audit_logs", ["username"])
    op.create_index("ix_audit_ts_action", "audit_logs", ["ts", "action"])


def downgrade():
    op.drop_table("audit_logs")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
