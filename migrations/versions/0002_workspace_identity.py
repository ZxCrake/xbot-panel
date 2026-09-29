"""Give each account a permanent workspace and session identity.

Existing accounts keep their directory; recreated accounts get a new UUID.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("workspace_key", sa.String(64), nullable=True))
    op.execute(sa.text("UPDATE users SET workspace_key = username"))
    with op.batch_alter_table("users") as batch:
        batch.alter_column("workspace_key", existing_type=sa.String(64), nullable=False)
        batch.create_unique_constraint("uq_users_workspace_key", ["workspace_key"])


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_workspace_key", type_="unique")
        batch.drop_column("workspace_key")
