"""Add recruitment module (departments, cohorts, candidates, applications) + recruiter role

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 's9t0u1v2w3x4'
down_revision: Union[str, None] = 'r8s9t0u1v2w3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- departments (stable catalog) ---
    op.create_table(
        'departments',
        sa.Column('department_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('skills_sought', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('has_case_stage', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('calendly_link', sa.Text(), nullable=True),
        sa.Column('scoring_criteria', postgresql.JSONB(), nullable=True),
        sa.Column('custom_questions', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    )

    # --- recruitment_cycles (cohorts) ---
    op.create_table(
        'recruitment_cycles',
        sa.Column('cycle_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('opens_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('closes_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_recruitment_cycles_is_active', 'recruitment_cycles', ['is_active'])

    # --- cycle_departments (which departments recruit in a cohort) ---
    op.create_table(
        'cycle_departments',
        sa.Column('cycle_id', sa.Integer(), sa.ForeignKey('recruitment_cycles.cycle_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.department_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('is_open', sa.Boolean(), nullable=False, server_default='true'),
    )

    # --- recruiter_departments (recruiter scoping) ---
    op.create_table(
        'recruiter_departments',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.department_id', ondelete='CASCADE'), primary_key=True),
    )

    # --- candidates (never platform users) ---
    op.create_table(
        'candidates',
        sa.Column('candidate_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('degree', sa.String(255), nullable=True),
        sa.Column('study_year', sa.String(50), nullable=True),
        sa.Column('links', postgresql.JSONB(), nullable=True),
        sa.Column('cv_s3_key', sa.Text(), nullable=True),
        sa.Column('cover_letter_s3_key', sa.Text(), nullable=True),
        sa.Column('gdpr_consent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('gdpr_consent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('talent_pool_consent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_candidates_email', 'candidates', ['email'])

    # --- applications ---
    op.create_table(
        'applications',
        sa.Column('application_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.candidate_id', ondelete='CASCADE'), nullable=False),
        sa.Column('cycle_id', sa.Integer(), sa.ForeignKey('recruitment_cycles.cycle_id', ondelete='CASCADE'), nullable=False),
        sa.Column('department_applied_id', sa.Integer(), sa.ForeignKey('departments.department_id', ondelete='SET NULL'), nullable=True),
        sa.Column('department_ranking', postgresql.JSONB(), nullable=True),
        sa.Column('answers', postgresql.JSONB(), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='applied'),
        sa.Column('suggested_department_id', sa.Integer(), sa.ForeignKey('departments.department_id', ondelete='SET NULL'), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('match_rationale', sa.Text(), nullable=True),
        sa.Column('match_ranking', postgresql.JSONB(), nullable=True),
        sa.Column('match_status', sa.String(20), nullable=True, server_default='pending'),
        sa.Column('match_flags', postgresql.JSONB(), nullable=True),
        sa.Column('final_department_id', sa.Integer(), sa.ForeignKey('departments.department_id', ondelete='SET NULL'), nullable=True),
        sa.Column('interview_invite_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('case_brief_url', sa.Text(), nullable=True),
        sa.Column('case_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('case_deadline_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('case_submitted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('case_submission_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.UniqueConstraint('candidate_id', 'cycle_id', name='uq_application_candidate_cycle'),
    )
    op.create_index('ix_applications_candidate_id', 'applications', ['candidate_id'])
    op.create_index('ix_applications_cycle_id', 'applications', ['cycle_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])
    op.create_index('ix_applications_created_at', 'applications', ['created_at'])

    # --- application_materials ---
    op.create_table(
        'application_materials',
        sa.Column('material_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.application_id', ondelete='CASCADE'), nullable=False),
        sa.Column('s3_key', sa.Text(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_application_materials_application_id', 'application_materials', ['application_id'])

    # --- interviews ---
    op.create_table(
        'interviews',
        sa.Column('interview_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.application_id', ondelete='CASCADE'), nullable=False),
        sa.Column('interviewer_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('scheduled_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('ends_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('meeting_link', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('scorecard', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_interviews_application_id', 'interviews', ['application_id'])

    # --- application_events (append-only timeline) ---
    op.create_table(
        'application_events',
        sa.Column('event_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.application_id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('actor', sa.String(255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_application_events_application_id', 'application_events', ['application_id'])
    op.create_index('ix_application_events_created_at', 'application_events', ['created_at'])

    # --- recruitment_tokens (magic links) ---
    op.create_table(
        'recruitment_tokens',
        sa.Column('token_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.application_id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(255), nullable=False, unique=True),
        sa.Column('purpose', sa.String(30), nullable=False, server_default='status'),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_recruitment_tokens_application_id', 'recruitment_tokens', ['application_id'])
    op.create_index('ix_recruitment_tokens_token', 'recruitment_tokens', ['token'])

    # --- seed the recruiter role (idempotent) ---
    op.execute("""
        INSERT INTO roles (role_name)
        SELECT 'recruiter'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_name = 'recruiter')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE role_name = 'recruiter'")
    op.drop_table('recruitment_tokens')
    op.drop_table('application_events')
    op.drop_table('interviews')
    op.drop_table('application_materials')
    op.drop_table('applications')
    op.drop_index('ix_candidates_email', table_name='candidates')
    op.drop_table('candidates')
    op.drop_table('recruiter_departments')
    op.drop_table('cycle_departments')
    op.drop_index('ix_recruitment_cycles_is_active', table_name='recruitment_cycles')
    op.drop_table('recruitment_cycles')
    op.drop_table('departments')
