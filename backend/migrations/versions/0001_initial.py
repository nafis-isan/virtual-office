"""Create Visual Office task and agent tables.

Revision ID: 0001_initial
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=40), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="idle"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="thinking"),
        sa.Column("summary", sa.Text()),
        sa.Column("error_message", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])
    op.create_table(
        "task_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("expected_output", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("output", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_steps_task_id", "task_steps", ["task_id"])
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_task_id", "messages", ["task_id"])
    op.create_table(
        "agent_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_activities_task_id", "agent_activities", ["task_id"])
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.Integer(), sa.ForeignKey("task_steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_artifacts_task_id", "artifacts", ["task_id"])
    op.create_index("ix_artifacts_step_id", "artifacts", ["step_id"])
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="waiting_approval"),
        sa.Column("decision_note", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime()),
    )
    op.create_index("ix_approvals_task_id", "approvals", ["task_id"])
    op.bulk_insert(
        sa.table(
            "agents",
            sa.column("name", sa.String),
            sa.column("display_name", sa.String),
            sa.column("role", sa.String),
            sa.column("status", sa.String),
        ),
        [
            {"name": "project_manager", "display_name": "Project Manager", "role": "Menyusun rencana dan merangkum hasil", "status": "idle"},
            {"name": "researcher", "display_name": "Researcher", "role": "Menganalisis kebutuhan dan informasi", "status": "idle"},
            {"name": "designer", "display_name": "Designer", "role": "Menyusun konsep dan spesifikasi UI/UX", "status": "idle"},
            {"name": "programmer", "display_name": "Programmer", "role": "Menyusun usulan implementasi dalam bentuk teks", "status": "idle"},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_approvals_task_id", table_name="approvals")
    op.drop_table("approvals")
    op.drop_index("ix_artifacts_step_id", table_name="artifacts")
    op.drop_index("ix_artifacts_task_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_agent_activities_task_id", table_name="agent_activities")
    op.drop_table("agent_activities")
    op.drop_index("ix_messages_task_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_task_steps_task_id", table_name="task_steps")
    op.drop_table("task_steps")
    op.drop_index("ix_tasks_created_at", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("agents")
