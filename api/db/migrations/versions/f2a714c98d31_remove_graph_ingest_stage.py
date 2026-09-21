"""remove graph ingest stage

Revision ID: f2a714c98d31
Revises: c9e4b71d5f38
Create Date: 2026-09-21 00:00:00.000000

Neo4j was a derived projection of Postgres. Embedding is now the terminal
import stage, so its ledger rows are obsolete and can be discarded.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a714c98d31"
down_revision: Union[str, Sequence[str], None] = "c9e4b71d5f38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM paper_stage_runs WHERE stage = 'graph'"))
    op.drop_constraint("ck_stage_runs_stage", "paper_stage_runs", type_="check")
    op.create_check_constraint(
        "ck_stage_runs_stage", "paper_stage_runs", "stage in ('ingest','embed')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_stage_runs_stage", "paper_stage_runs", type_="check")
    op.create_check_constraint(
        "ck_stage_runs_stage",
        "paper_stage_runs",
        "stage in ('ingest','embed','graph')",
    )
