"""Create timeline narrative and feedback tables.

Tables:
- period_narratives: AI-generated period overviews (50-year windows)
- entity_narratives: AI-generated event/person narratives
- user_feedback: User curation reports

Revision ID: 400_timeline_narratives
Revises: 302_event_system
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = '400_timeline_narratives'
down_revision = '302_event_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- period_narratives ---
    op.create_table(
        'period_narratives',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('period_start', sa.Integer, nullable=False),
        sa.Column('period_end', sa.Integer, nullable=False),
        sa.Column('era_id', sa.String(20)),
        sa.Column('headline', sa.String(200)),
        sa.Column('headline_ko', sa.String(200)),
        sa.Column('narrative', sa.Text),
        sa.Column('narrative_ko', sa.Text),
        sa.Column('keywords', sa.ARRAY(sa.Text)),
        sa.Column('defining_moment', sa.String(500)),
        sa.Column('model_used', sa.String(50)),
        sa.Column('generated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('quality_score', sa.Integer),
        sa.Column('curated_status', sa.String(20), server_default='auto'),
        sa.Column('curated_by', sa.String(100)),
        sa.Column('curated_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('period_start', 'period_end', name='uq_period_narratives_range'),
    )
    op.create_index('idx_period_narratives_period', 'period_narratives', ['period_start'])

    # --- entity_narratives ---
    op.create_table(
        'entity_narratives',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('entity_type', sa.String(10), nullable=False),
        sa.Column('entity_id', sa.Integer, nullable=False),
        sa.Column('period_start', sa.Integer),
        sa.Column('narrative', sa.Text),
        sa.Column('narrative_ko', sa.Text),
        sa.Column('significance', sa.String(500)),
        sa.Column('causes', sa.ARRAY(sa.Text)),
        sa.Column('consequences', sa.ARRAY(sa.Text)),
        sa.Column('model_used', sa.String(50)),
        sa.Column('source_url', sa.String(500)),
        sa.Column('generated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('curated_status', sa.String(20), server_default='auto'),
        sa.Column('curated_by', sa.String(100)),
        sa.Column('curated_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('entity_type', 'entity_id', name='uq_entity_narratives_type_id'),
    )
    op.create_index('idx_entity_narratives_type_id', 'entity_narratives', ['entity_type', 'entity_id'])
    op.create_index('idx_entity_narratives_period', 'entity_narratives', ['period_start'])

    # --- user_feedback ---
    op.create_table(
        'user_feedback',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', sa.Integer, nullable=False),
        sa.Column('feedback_type', sa.String(20), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('suggested_fix', sa.Text),
        sa.Column('reporter_ip', sa.String(50)),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('reviewed_by', sa.String(100)),
        sa.Column('reviewed_at', sa.DateTime),
        sa.Column('review_note', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_user_feedback_status', 'user_feedback', ['status'])
    op.create_index('idx_user_feedback_target', 'user_feedback', ['target_type', 'target_id'])


def downgrade() -> None:
    op.drop_table('user_feedback')
    op.drop_table('entity_narratives')
    op.drop_table('period_narratives')
