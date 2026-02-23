"""Create histories and history_entities tables.

Tables:
- histories: User/system authored historical essays with entity tagging
- history_entities: Links histories to persons, events, locations

Revision ID: 500_histories
Revises: 402_add_quote
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = '500_histories'
down_revision = '402_add_quote'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- histories ---
    op.create_table(
        'histories',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),

        # Meta
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('title_ko', sa.String(300)),
        sa.Column('title_ja', sa.String(300)),
        sa.Column('summary', sa.String(500)),

        # Temporal scope
        sa.Column('era_start', sa.Integer),
        sa.Column('era_end', sa.Integer),

        # Body (Markdown with [name](entity:type:id) tags)
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('body_ko', sa.Text),
        sa.Column('body_ja', sa.Text),

        # Classification
        sa.Column('category', sa.String(50), server_default='essay'),
        sa.Column('tags', sa.ARRAY(sa.Text)),

        # Author
        sa.Column('author_type', sa.String(20), server_default='system'),
        sa.Column('author_name', sa.String(100)),

        # Status
        sa.Column('status', sa.String(20), server_default='published'),
        sa.Column('importance', sa.Integer, server_default='3'),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_histories_era', 'histories', ['era_start', 'era_end'])
    op.create_index('idx_histories_status', 'histories', ['status'])

    # --- history_entities ---
    op.create_table(
        'history_entities',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('history_id', sa.Integer, sa.ForeignKey('histories.id', ondelete='CASCADE'), nullable=False),

        # Linked entity
        sa.Column('entity_type', sa.String(10), nullable=False),
        sa.Column('entity_id', sa.Integer, nullable=False),
        sa.Column('entity_name', sa.String(255)),

        # Role
        sa.Column('role', sa.String(20), server_default='mentioned'),

        sa.UniqueConstraint('history_id', 'entity_type', 'entity_id', name='uq_history_entities_unique'),
    )
    op.create_index('idx_he_history', 'history_entities', ['history_id'])
    op.create_index('idx_he_entity', 'history_entities', ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_table('history_entities')
    op.drop_table('histories')
