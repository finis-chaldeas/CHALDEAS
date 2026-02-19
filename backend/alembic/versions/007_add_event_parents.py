"""Add event_parents table for multiple parent support

Revision ID: 007_add_event_parents
Revises: 006_add_parent_status
Create Date: 2026-01-28

Adds:
- event_parents table: Many-to-many relationship for event hierarchy
- Supports multiple parents with is_primary flag
- Context field for different relationship contexts (war, culture, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_add_event_parents'
down_revision: Union[str, None] = '006_add_parent_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create event_parents table
    op.create_table(
        'event_parents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('context', sa.String(50), nullable=True),  # war, culture, religion, politics, science, philosophy, general
        sa.Column('source', sa.String(50), nullable=True),  # wikidata, llm, manual, migration
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        # Constraints
        sa.UniqueConstraint('event_id', 'parent_event_id', name='uq_event_parents_event_parent'),
        sa.CheckConstraint('event_id != parent_event_id', name='ck_event_parents_no_self_ref'),
    )

    # Indexes
    op.create_index('ix_event_parents_event_id', 'event_parents', ['event_id'])
    op.create_index('ix_event_parents_parent_event_id', 'event_parents', ['parent_event_id'])
    op.create_index('ix_event_parents_is_primary', 'event_parents', ['is_primary'])
    op.create_index('ix_event_parents_context', 'event_parents', ['context'])

    # Migrate existing parent_event_id data to event_parents
    op.execute("""
        INSERT INTO event_parents (event_id, parent_event_id, is_primary, context, source, confidence)
        SELECT id, parent_event_id, true, 'general', 'migration', 1.0
        FROM events
        WHERE parent_event_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_event_parents_context', 'event_parents')
    op.drop_index('ix_event_parents_is_primary', 'event_parents')
    op.drop_index('ix_event_parents_parent_event_id', 'event_parents')
    op.drop_index('ix_event_parents_event_id', 'event_parents')
    op.drop_table('event_parents')
