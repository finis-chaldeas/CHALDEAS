"""Add parent_status column to events

Revision ID: 006_add_parent_status
Revises: 005_add_event_location_hierarchy
Create Date: 2026-01-28

Adds:
- parent_status: Tracks classification state (none/unknown/confirmed/pending)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_parent_status'
down_revision: Union[str, None] = '005_add_event_location_hierarchy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # parent_status: Classification state
    # - 'none': No parent (confirmed top-level event)
    # - 'unknown': Not yet classified
    # - 'confirmed': Parent assigned and verified
    # - 'pending': Parent assigned but needs review
    op.add_column('events', sa.Column(
        'parent_status',
        sa.String(20),
        server_default='unknown',
        nullable=False
    ))

    op.create_index('ix_events_parent_status', 'events', ['parent_status'])

    # Set existing events with parent_event_id to 'confirmed'
    # Set events without parent to 'unknown' (default)
    op.execute("""
        UPDATE events
        SET parent_status = 'confirmed'
        WHERE parent_event_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_events_parent_status', 'events')
    op.drop_column('events', 'parent_status')
