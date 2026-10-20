"""Add task archival and generated file artifact metadata.

Revision ID: 0003_task_files
Revises: 0002_knowledge_rag
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_task_files"
down_revision = "0002_knowledge_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "artifacts",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="output"),
    )


def downgrade() -> None:
    op.drop_column("artifacts", "kind")
    op.drop_column("tasks", "archived")
