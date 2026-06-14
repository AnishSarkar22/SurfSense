"""add search space onboarding state

Revision ID: 162
Revises: 161
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "162"
down_revision: str | None = "161"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return column_name in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    if not _column_exists("searchspaces", "onboarding_state"):
        op.add_column(
            "searchspaces",
            sa.Column(
                "onboarding_state",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )


def downgrade() -> None:
    if _column_exists("searchspaces", "onboarding_state"):
        op.drop_column("searchspaces", "onboarding_state")
