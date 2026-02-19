"""V2 Schema - Complete CHALDEAS Implementation

Revision ID: 100_v2_schema
Revises: 007_add_event_parents
Create Date: 2026-01-31

This migration adds V2 tables:
1. events_v2 - Enhanced events with vector attributes
2. clusters - Event groupings
3. cluster_events - M2M cluster-event association
4. event_relations_v2 - Enhanced relations with Wikidata properties
5. person_event_roles - Role-based person-event connections
6. historicity_sources - Evidence for historical verification
7. fgo_servants - FGO servant data
8. fgo_history_comparison - Historical vs FGO comparison
9. event_completeness - Quality tracking
10. fill_queue - Work queue for data filling
11. work_logs - Checkpoint logging

Design Principles:
- V2 tables are NEW, not modifications of V0/V1
- V0/V1 remain fully operational
- Data can be migrated from V0 to V2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers
revision: str = '100_v2_schema'
down_revision: Union[str, None] = '007_add_event_parents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===========================================
    # 1. Work Logs (dependency for other tables)
    # ===========================================
    op.create_table(
        'work_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('checkpoint', sa.String(20), nullable=False, index=True),
        sa.Column('task_name', sa.String(200), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='started', index=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('duration_minutes', sa.Integer()),
        sa.Column('notes', sa.Text()),
        # Statistics
        sa.Column('records_processed', sa.Integer(), default=0),
        sa.Column('records_created', sa.Integer(), default=0),
        sa.Column('records_updated', sa.Integer(), default=0),
        sa.Column('errors_count', sa.Integer(), default=0),
        # Cost tracking
        sa.Column('llm_tier1_calls', sa.Integer(), default=0),
        sa.Column('llm_tier2_calls', sa.Integer(), default=0),
        sa.Column('llm_tier3_calls', sa.Integer(), default=0),
        sa.Column('estimated_cost', sa.Numeric(10, 4), default=0),
        sa.CheckConstraint(
            "status IN ('started', 'in_progress', 'completed', 'failed')",
            name='ck_work_logs_status'
        ),
    )
    op.create_index('idx_work_logs_checkpoint_status', 'work_logs', ['checkpoint', 'status'])

    # ===========================================
    # 2. Events V2 (Enhanced Events)
    # ===========================================
    op.create_table(
        'events_v2',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        # Basic info
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('title_ko', sa.String(500)),
        sa.Column('title_ja', sa.String(500)),
        sa.Column('slug', sa.String(500), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text()),
        sa.Column('description_ko', sa.Text()),
        sa.Column('description_ja', sa.Text()),

        # Temporal data (BCE support: negative numbers)
        sa.Column('date_start', sa.Integer(), nullable=False, index=True),
        sa.Column('date_start_month', sa.Integer()),
        sa.Column('date_start_day', sa.Integer()),
        sa.Column('date_end', sa.Integer(), index=True),
        sa.Column('date_end_month', sa.Integer()),
        sa.Column('date_end_day', sa.Integer()),
        sa.Column('date_precision', sa.String(20), default='year'),

        # Braudel's temporal scale
        sa.Column('temporal_scale', sa.String(20), default='evenementielle'),

        # Nature classification (NEW in V2)
        # war, battle, treaty, birth, death, coronation, discovery, invention,
        # founding, collapse, migration, cultural_event, natural_disaster, etc.
        sa.Column('nature', sa.String(50), index=True),

        # Event vectors (NEW in V2)
        # origin/destination for movement events
        sa.Column('origin_location_id', sa.Integer(), sa.ForeignKey('locations.id')),
        sa.Column('destination_location_id', sa.Integer(), sa.ForeignKey('locations.id')),
        # vector type: migration, conquest, trade, idea_spread, etc.
        sa.Column('vector_type', sa.String(50)),

        # Hierarchy
        sa.Column('parent_event_id', sa.Integer(), sa.ForeignKey('events_v2.id'), index=True),
        sa.Column('hierarchy_level', sa.Integer(), default=3, index=True),
        sa.Column('is_aggregate', sa.Boolean(), default=False, index=True),
        sa.Column('aggregate_type', sa.String(50)),

        # Classification
        sa.Column('certainty', sa.String(20), default='fact'),
        sa.Column('importance', sa.Integer(), default=3, index=True),

        # External references
        sa.Column('wikidata_id', sa.String(50), unique=True, index=True),
        sa.Column('wikipedia_url', sa.String(500)),
        sa.Column('image_url', sa.String(500)),

        # Embedding for vector search
        sa.Column('embedding', Vector(1536)),

        # Linked V0 event (for migration tracking)
        sa.Column('v0_event_id', sa.Integer(), sa.ForeignKey('events.id'), index=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Constraints
        sa.CheckConstraint(
            "temporal_scale IN ('evenementielle', 'conjuncture', 'longue_duree')",
            name='ck_events_v2_temporal_scale'
        ),
        sa.CheckConstraint(
            "certainty IN ('fact', 'probable', 'legendary', 'mythological')",
            name='ck_events_v2_certainty'
        ),
        sa.CheckConstraint(
            "importance >= 1 AND importance <= 5",
            name='ck_events_v2_importance'
        ),
    )
    op.create_index('idx_events_v2_temporal_range', 'events_v2', ['date_start', 'date_end'])
    op.create_index('idx_events_v2_nature', 'events_v2', ['nature', 'date_start'])

    # ===========================================
    # 3. Clusters
    # ===========================================
    op.create_table(
        'clusters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('name_ko', sa.String(300)),
        sa.Column('slug', sa.String(300), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text()),
        sa.Column('description_ko', sa.Text()),

        # Cluster type
        # spatiotemporal: Events close in space and time
        # causal: Events linked by cause-effect
        # thematic: Events sharing common theme
        # person_centric: Events around a person's life
        sa.Column('cluster_type', sa.String(30), nullable=False, index=True),

        # Temporal bounds
        sa.Column('date_start', sa.Integer(), index=True),
        sa.Column('date_end', sa.Integer()),

        # Spatial bounds (center point)
        sa.Column('center_lat', sa.Float()),
        sa.Column('center_lng', sa.Float()),
        sa.Column('radius_km', sa.Float()),

        # Focal entity (optional)
        sa.Column('focal_person_id', sa.Integer(), sa.ForeignKey('persons.id')),
        sa.Column('focal_location_id', sa.Integer(), sa.ForeignKey('locations.id')),

        # Stats
        sa.Column('event_count', sa.Integer(), default=0),
        sa.Column('importance', sa.Integer(), default=3),

        # Auto-generation metadata
        sa.Column('is_auto_generated', sa.Boolean(), default=False),
        sa.Column('generation_algorithm', sa.String(50)),
        sa.Column('quality_score', sa.Float()),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.CheckConstraint(
            "cluster_type IN ('spatiotemporal', 'causal', 'thematic', 'person_centric')",
            name='ck_clusters_type'
        ),
    )

    # ===========================================
    # 4. Cluster Events (M2M)
    # ===========================================
    op.create_table(
        'cluster_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('cluster_id', sa.Integer(), sa.ForeignKey('clusters.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role_in_cluster', sa.String(30), default='member'),  # core, member, peripheral
        sa.Column('sequence_number', sa.Integer()),  # For ordered clusters
        sa.Column('added_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('cluster_id', 'event_id', name='uq_cluster_event'),
    )

    # ===========================================
    # 5. Event Relations V2
    # ===========================================
    op.create_table(
        'event_relations_v2',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('from_event_id', sa.Integer(), sa.ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('to_event_id', sa.Integer(), sa.ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True),

        # Relation type
        # causes, follows, part_of, parallel_to, precedes, enables, opposes
        sa.Column('relation_type', sa.String(30), nullable=False, index=True),

        # Wikidata property (e.g., P361 = part of, P155 = follows)
        sa.Column('wikidata_property', sa.String(20)),

        # Strength and confidence
        sa.Column('strength', sa.Integer(), default=3),
        sa.Column('confidence', sa.Float(), default=1.0),

        # Evidence
        sa.Column('evidence_type', sa.String(30)),  # wikidata, scholarly, inferred
        sa.Column('evidence_source', sa.Text()),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),

        sa.UniqueConstraint('from_event_id', 'to_event_id', 'relation_type', name='uq_event_relation_v2'),
        sa.CheckConstraint(
            "relation_type IN ('causes', 'follows', 'part_of', 'parallel_to', 'precedes', 'enables', 'opposes')",
            name='ck_event_relations_v2_type'
        ),
    )

    # ===========================================
    # 6. Person Event Roles
    # ===========================================
    op.create_table(
        'person_event_roles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, index=True),

        # Role in the event
        # leader, participant, victim, witness, initiator, opponent, beneficiary
        sa.Column('role', sa.String(30), nullable=False, index=True),

        # Importance of this person to the event (1-5)
        sa.Column('importance', sa.Integer(), default=3),

        # Was this person a primary actor?
        sa.Column('is_primary', sa.Boolean(), default=False),

        # Evidence
        sa.Column('evidence_source', sa.String(100)),
        sa.Column('confidence', sa.Float(), default=1.0),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),

        sa.CheckConstraint(
            "role IN ('leader', 'participant', 'victim', 'witness', 'initiator', 'opponent', 'beneficiary', 'advisor', 'commander')",
            name='ck_person_event_roles_role'
        ),
    )
    op.create_index('idx_person_event_roles', 'person_event_roles', ['person_id', 'event_id'])

    # ===========================================
    # 7. Historicity Sources
    # ===========================================
    op.create_table(
        'historicity_sources',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('entity_type', sa.String(20), nullable=False, index=True),  # event, person
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),

        # Source type
        # primary: Contemporary documents
        # secondary: Later historical analysis
        # archaeological: Physical evidence
        # literary: Literary references
        sa.Column('source_type', sa.String(30), nullable=False),

        # Source details
        sa.Column('source_name', sa.String(300), nullable=False),
        sa.Column('source_url', sa.String(500)),
        sa.Column('author', sa.String(200)),
        sa.Column('publication_year', sa.Integer()),

        # Reliability assessment
        sa.Column('reliability_score', sa.Integer(), default=3),  # 1-5
        sa.Column('assessment_notes', sa.Text()),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),

        sa.CheckConstraint(
            "entity_type IN ('event', 'person')",
            name='ck_historicity_sources_entity_type'
        ),
        sa.CheckConstraint(
            "source_type IN ('primary', 'secondary', 'archaeological', 'literary', 'oral', 'epigraphic')",
            name='ck_historicity_sources_source_type'
        ),
    )
    op.create_index('idx_historicity_sources_entity', 'historicity_sources', ['entity_type', 'entity_id'])

    # ===========================================
    # 8. FGO Servants
    # ===========================================
    op.create_table(
        'fgo_servants',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('servant_id', sa.Integer(), unique=True, nullable=False, index=True),  # FGO game ID
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('name_jp', sa.String(200)),
        sa.Column('class_name', sa.String(50), nullable=False),  # Saber, Archer, etc.
        sa.Column('rarity', sa.Integer()),  # 1-5 stars

        # Linked historical person
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id'), index=True),

        # FGO-specific data
        sa.Column('noble_phantasm', sa.String(200)),
        sa.Column('attribute', sa.String(50)),  # Human, Earth, Sky, Star, Beast
        sa.Column('gender', sa.String(20)),

        # Image
        sa.Column('portrait_url', sa.String(500)),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ===========================================
    # 9. FGO History Comparison
    # ===========================================
    op.create_table(
        'fgo_history_comparison',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('servant_id', sa.Integer(), sa.ForeignKey('fgo_servants.id', ondelete='CASCADE'), nullable=False, index=True),

        # Comparison aspects
        sa.Column('aspect', sa.String(50), nullable=False),  # biography, appearance, abilities, personality
        sa.Column('fgo_description', sa.Text()),
        sa.Column('historical_description', sa.Text()),

        # Accuracy assessment
        sa.Column('accuracy_score', sa.Integer()),  # 1-5
        sa.Column('assessment', sa.String(30)),  # accurate, artistic_license, fictional
        sa.Column('notes', sa.Text()),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),

        sa.CheckConstraint(
            "aspect IN ('biography', 'appearance', 'abilities', 'personality', 'relationships', 'noble_phantasm')",
            name='ck_fgo_comparison_aspect'
        ),
        sa.CheckConstraint(
            "assessment IN ('accurate', 'artistic_license', 'fictional', 'composite', 'gender_swap')",
            name='ck_fgo_comparison_assessment'
        ),
    )

    # ===========================================
    # 10. Event Completeness (Quality Tracking)
    # ===========================================
    op.create_table(
        'event_completeness',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events_v2.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),

        # Field completeness (0-100)
        sa.Column('title_score', sa.Integer(), default=0),
        sa.Column('description_score', sa.Integer(), default=0),
        sa.Column('date_score', sa.Integer(), default=0),
        sa.Column('location_score', sa.Integer(), default=0),
        sa.Column('persons_score', sa.Integer(), default=0),
        sa.Column('relations_score', sa.Integer(), default=0),
        sa.Column('sources_score', sa.Integer(), default=0),

        # Overall completeness
        sa.Column('overall_score', sa.Integer(), default=0, index=True),

        # Flags
        sa.Column('needs_review', sa.Boolean(), default=False, index=True),
        sa.Column('is_stub', sa.Boolean(), default=True),

        sa.Column('last_calculated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # ===========================================
    # 11. Fill Queue (Work Queue)
    # ===========================================
    op.create_table(
        'fill_queue',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('entity_type', sa.String(20), nullable=False, index=True),  # event, person, cluster
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),

        # Task type
        # enrich_description, add_wikidata, find_relations, add_persons, add_locations
        sa.Column('task_type', sa.String(50), nullable=False, index=True),

        # Priority (higher = more urgent)
        sa.Column('priority', sa.Integer(), default=0, index=True),

        # Status
        sa.Column('status', sa.String(20), default='pending', index=True),

        # LLM tier to use
        sa.Column('llm_tier', sa.Integer(), default=1),

        # Processing info
        sa.Column('attempts', sa.Integer(), default=0),
        sa.Column('last_attempt_at', sa.DateTime()),
        sa.Column('error_message', sa.Text()),

        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),

        sa.CheckConstraint(
            "entity_type IN ('event', 'person', 'cluster')",
            name='ck_fill_queue_entity_type'
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'skipped')",
            name='ck_fill_queue_status'
        ),
    )
    op.create_index('idx_fill_queue_priority', 'fill_queue', ['status', 'priority', 'created_at'])

    # ===========================================
    # 12. Create System Completeness View
    # ===========================================
    op.execute("""
        CREATE OR REPLACE VIEW system_completeness AS
        SELECT
            (SELECT COUNT(*) FROM events_v2) as total_events_v2,
            (SELECT COUNT(*) FROM events_v2 WHERE wikidata_id IS NOT NULL) as events_with_wikidata,
            (SELECT COUNT(*) FROM events_v2 WHERE description IS NOT NULL AND length(description) > 100) as events_with_description,
            (SELECT COUNT(*) FROM clusters) as total_clusters,
            (SELECT COUNT(*) FROM event_relations_v2) as total_relations,
            (SELECT COUNT(*) FROM person_event_roles) as total_person_roles,
            (SELECT COUNT(*) FROM fgo_servants) as total_fgo_servants,
            (SELECT AVG(overall_score) FROM event_completeness) as avg_completeness_score,
            (SELECT SUM(estimated_cost) FROM work_logs) as total_estimated_cost
    """)


def downgrade() -> None:
    # Drop view first
    op.execute("DROP VIEW IF EXISTS system_completeness")

    # Drop tables in reverse order
    op.drop_table('fill_queue')
    op.drop_table('event_completeness')
    op.drop_table('fgo_history_comparison')
    op.drop_table('fgo_servants')
    op.drop_table('historicity_sources')
    op.drop_table('person_event_roles')
    op.drop_table('event_relations_v2')
    op.drop_table('cluster_events')
    op.drop_table('clusters')
    op.drop_table('events_v2')
    op.drop_table('work_logs')
