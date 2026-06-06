"""Initial migration

Revision ID: 20260606_0001
Revises:
Create Date: 2026-06-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

subscriptiontier = postgresql.ENUM(
    "FREE", "PRO", name="subscriptiontier", create_type=False
)
bookstatus = postgresql.ENUM(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="bookstatus", create_type=False
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    subscriptiontier.create(op.get_bind(), checkfirst=True)
    bookstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("plan_type", subscriptiontier, nullable=False),
        sa.Column("ocr_quota_remaining", sa.Integer(), nullable=False),
        sa.Column("ocr_quota_reset_date", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "books",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("status", bookstatus, nullable=False),
        sa.Column("progress_percentage", sa.Integer(), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=False),
        sa.Column("processed_pages", sa.Integer(), nullable=False),
        sa.Column("original_pdf_url", sa.String(length=512), nullable=False),
        sa.Column("parsed_content_url", sa.String(length=512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_status"), "books", ["status"], unique=False)
    op.create_index(op.f("ix_books_user_id"), "books", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_books_user_id"), table_name="books")
    op.drop_index(op.f("ix_books_status"), table_name="books")
    op.drop_table("books")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    bookstatus.drop(op.get_bind(), checkfirst=True)
    subscriptiontier.drop(op.get_bind(), checkfirst=True)
