"""add entity and mention search embeddings

Revision ID: 3b0d52a8c144
Revises: f2a714c98d31
Create Date: 2026-09-21 00:00:00.000000

Vectors are derived data and are backfilled by
``python -m api.ingestion.backfill_entity_embeddings`` after this migration.
"""

from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "3b0d52a8c144"
down_revision: Union[str, Sequence[str], None] = "f2a714c98d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.add_column(
        "entities",
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=768), nullable=True),
    )
    op.create_table(
        "entity_mention_embeddings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("surface_text", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=768), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("surface_text"),
    )
    op.create_index(
        "ix_entities_name_trgm",
        "entities",
        ["name"],
        postgresql_using="gist",
        postgresql_ops={"name": "gist_trgm_ops"},
    )
    op.create_index(
        "ix_mentions_surface_text_trgm",
        "paper_entity_mentions",
        ["surface_text"],
        postgresql_using="gist",
        postgresql_ops={"surface_text": "gist_trgm_ops"},
    )
    op.execute(
        "CREATE INDEX ix_entities_embedding_hnsw ON entities "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_entity_mention_embeddings_hnsw ON entity_mention_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entity_mention_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_entities_embedding_hnsw")
    op.drop_index("ix_mentions_surface_text_trgm", table_name="paper_entity_mentions")
    op.drop_index("ix_entities_name_trgm", table_name="entities")
    op.drop_table("entity_mention_embeddings")
    op.drop_column("entities", "embedding")
    # pg_trgm is intentionally retained: another schema may use the extension.
