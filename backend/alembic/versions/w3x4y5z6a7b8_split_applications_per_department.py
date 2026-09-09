"""Give every department its own application row

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-09-09 00:00:00.000000

A candidate who ranked three departments previously produced ONE application
row, with the other two choices living only as ids in department_ranking. That
meant one status, one case study and one interview shared between three teams:
if Innovation moved someone to Interview, HR saw that too.

This splits the ranking into one row per department so each team runs its own
pipeline.

SAFETY: this migration is INSERT-only. It issues no UPDATE and no DELETE against
`applications`. Every existing row keeps its application_id, its status, its
case/interview state and all of its child rows. New sibling rows are added
beside the originals. The pre/post row-count assertions below abort the whole
transaction if that ever stops being true.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'w3x4y5z6a7b8'
down_revision: Union[str, None] = 'v2w3x4y5z6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Departments from the candidate's ranking that don't yet have their own row.
# jsonb_array_elements expands the ranking; the join to departments skips ids
# naming a department that has since been deleted (which would otherwise fail
# the foreign key); DISTINCT collapses a ranking that repeats a department or
# re-lists the first choice.
_MISSING_ROWS = """
    SELECT DISTINCT
           a.application_id AS source_id,
           d.department_id  AS dept_id
      FROM applications a
      JOIN LATERAL jsonb_array_elements_text(a.department_ranking) AS r(dept) ON TRUE
      JOIN departments d ON d.department_id = r.dept::int
     WHERE a.department_ranking IS NOT NULL
       AND jsonb_typeof(a.department_ranking) = 'array'
       AND NOT EXISTS (
             SELECT 1 FROM applications existing
              WHERE existing.candidate_id = a.candidate_id
                AND existing.cycle_id = a.cycle_id
                AND existing.department_applied_id = d.department_id
           )
"""


def upgrade() -> None:
    conn = op.get_bind()

    # ── Pre-flight ──────────────────────────────────────────────────────────
    before_count = conn.execute(sa.text("SELECT count(*) FROM applications")).scalar_one()
    conn.execute(sa.text("""
        CREATE TEMP TABLE _pre_split_ids ON COMMIT DROP AS
        SELECT application_id FROM applications
    """))

    # Must be dropped before inserting, or the new rows violate it.
    op.drop_constraint('uq_application_candidate_cycle', 'applications', type_='unique')

    # ── Insert one row per additional ranked department ─────────────────────
    # Deliberately NOT copied: status/match (a new row starts fresh at
    # 'applied'), all case_* columns, interview_invite_sent and
    # final_department_id - only the department that actually ran a stage
    # should show it.
    inserted = len(conn.execute(sa.text(f"""
        WITH missing AS ({_MISSING_ROWS})
        INSERT INTO applications (
            candidate_id, cycle_id, department_applied_id, department_ranking,
            answers, source, status, match_status, created_at, updated_at,
            interview_invite_sent
        )
        SELECT a.candidate_id, a.cycle_id, m.dept_id, a.department_ranking,
               a.answers, a.source, 'applied', 'pending', a.created_at, now(),
               false
          FROM missing m
          JOIN applications a ON a.application_id = m.source_id
        RETURNING application_id
    """)).fetchall())

    # Materials are per-application, so each sibling needs its own rows. The
    # s3_key is shared, not duplicated - the objects themselves stay put.
    conn.execute(sa.text("""
        INSERT INTO application_materials (application_id, s3_key, filename, note, created_at)
        SELECT new_app.application_id, m.s3_key, m.filename, m.note, m.created_at
          FROM applications new_app
          JOIN applications src
            ON src.candidate_id = new_app.candidate_id
           AND src.cycle_id = new_app.cycle_id
           -- Source only from the ORIGINAL row, never from another sibling
           -- created moments ago, or the copy fans out.
           AND src.application_id IN (SELECT application_id FROM _pre_split_ids)
          JOIN application_materials m ON m.application_id = src.application_id
         WHERE new_app.application_id NOT IN (SELECT application_id FROM _pre_split_ids)
           AND NOT EXISTS (
                 SELECT 1 FROM application_materials existing
                  WHERE existing.application_id = new_app.application_id
                    AND existing.s3_key = m.s3_key
               )
    """))

    # ── Post-flight assertions: abort (and roll back) on any surprise ───────
    after_count = conn.execute(sa.text("SELECT count(*) FROM applications")).scalar_one()
    if after_count != before_count + inserted:
        raise RuntimeError(
            f"Application row count is wrong after the split: expected "
            f"{before_count} + {inserted} = {before_count + inserted}, found {after_count}. "
            "Rolling back."
        )

    lost = conn.execute(sa.text("""
        SELECT count(*) FROM _pre_split_ids p
         WHERE NOT EXISTS (
               SELECT 1 FROM applications a WHERE a.application_id = p.application_id
         )
    """)).scalar_one()
    if lost:
        raise RuntimeError(
            f"{lost} pre-existing application(s) disappeared during the split. Rolling back."
        )

    # Added last so it validates the post-split data.
    op.create_unique_constraint(
        'uq_application_candidate_cycle_department',
        'applications',
        ['candidate_id', 'cycle_id', 'department_applied_id'],
    )


def downgrade() -> None:
    """
    Deliberately refuses to run once candidates hold more than one application.

    After the split there is no reliable way to tell a generated sibling from an
    application submitted normally afterwards, so an automatic reversal would
    risk deleting real applications. Restore from the pre-migration dump instead.
    """
    conn = op.get_bind()
    duplicates = conn.execute(sa.text("""
        SELECT count(*) FROM (
            SELECT 1 FROM applications
             GROUP BY candidate_id, cycle_id
            HAVING count(*) > 1
        ) dupes
    """)).scalar_one()
    if duplicates:
        raise RuntimeError(
            f"{duplicates} candidate/cycle pair(s) now hold multiple applications. "
            "Downgrading would mean deleting rows that may be real applications, so this "
            "migration will not reverse itself. Restore from the pre-split database dump."
        )

    op.drop_constraint('uq_application_candidate_cycle_department', 'applications', type_='unique')
    op.create_unique_constraint(
        'uq_application_candidate_cycle', 'applications', ['candidate_id', 'cycle_id']
    )
