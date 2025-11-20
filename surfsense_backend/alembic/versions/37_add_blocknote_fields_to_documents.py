"""37_add_blocknote_fields_to_documents

Revision ID: 37
Revises: 36

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '37'
down_revision: str | None = '36'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - Add BlockNote fields only."""
    
    op.add_column(
        'documents',
        sa.Column('blocknote_document', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'documents',
        sa.Column('is_collaborative', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'documents',
        sa.Column('content_needs_reindexing', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'documents',
        sa.Column('collaboration_session_id', sa.String(), nullable=True)
    )
    op.add_column(
        'documents',
        sa.Column('last_edited_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )

def downgrade() -> None:
    """Downgrade schema - Remove BlockNote fields."""
    op.drop_column('documents', 'last_edited_at')
    op.drop_column('documents', 'content_needs_reindexing')
    op.drop_column('documents', 'collaboration_session_id')
    op.drop_column('documents', 'is_collaborative')
    op.drop_column('documents', 'blocknote_document')