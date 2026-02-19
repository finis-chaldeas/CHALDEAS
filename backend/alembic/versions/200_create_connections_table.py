"""Create unified connections table.

Based on CLEAN_SCHEMA_PLAN.md - single table for all entity connections with required evidence.

Revision ID: 200_connections
Revises: 100_create_v2_schema
Create Date: 2026-02-01
"""
from alembic import op
import sqlalchemy as sa

revision = '200_connections'
down_revision = '008_location_names'  # After location_names
branch_labels = None
depends_on = None


def upgrade():
    # connections: 모든 엔티티 연결 (근거 필수!)
    op.create_table(
        'connections',
        sa.Column('id', sa.Integer(), primary_key=True),

        # From entity
        sa.Column('from_type', sa.String(20), nullable=False),  # person, location, event
        sa.Column('from_id', sa.Integer(), nullable=False),
        sa.Column('from_qid', sa.String(20)),  # Wikidata QID

        # To entity
        sa.Column('to_type', sa.String(20), nullable=False),  # person, location, event
        sa.Column('to_id', sa.Integer(), nullable=False),
        sa.Column('to_qid', sa.String(20)),  # Wikidata QID

        # Relation
        sa.Column('relation', sa.String(50), nullable=False),  # participant, leader, occurred_at, part_of, etc.

        # Evidence (REQUIRED!)
        sa.Column('evidence', sa.Text(), nullable=False),  # 근거 텍스트 - 반드시 있어야 함

        # Source tracking
        sa.Column('source_url', sa.String(500)),  # 출처 URL
        sa.Column('source_type', sa.String(20)),  # wikipedia, wikidata, book
        sa.Column('confidence', sa.Float(), default=0.7),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Indexes for fast lookup
    op.create_index('ix_connections_from', 'connections', ['from_type', 'from_id'])
    op.create_index('ix_connections_to', 'connections', ['to_type', 'to_id'])
    op.create_index('ix_connections_relation', 'connections', ['relation'])
    op.create_index('ix_connections_from_qid', 'connections', ['from_qid'])
    op.create_index('ix_connections_to_qid', 'connections', ['to_qid'])


def downgrade():
    op.drop_table('connections')
