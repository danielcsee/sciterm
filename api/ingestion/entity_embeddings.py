"""Build the derived vectors used by experimental entity matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from api.db import session_scope
from api.db.models import Entity, EntityMentionEmbedding, PaperEntityMention
from api.ingestion.embedding import embed_texts


@dataclass(frozen=True)
class SearchText:
    id: int
    text: str


def _clean_rows(rows: Sequence[tuple[int, Optional[str]]]) -> list[SearchText]:
    return [SearchText(row_id, text.strip()) for row_id, text in rows if text and text.strip()]


def _clean_texts(rows: Sequence[tuple[Optional[str]]]) -> list[str]:
    return list(dict.fromkeys(text.strip() for (text,) in rows if text and text.strip()))


def _vectors_by_value(texts: Sequence[str]) -> dict[str, list[float]]:
    return dict(zip(texts, embed_texts(texts)))


def embed_search_terms_for_paper(paper_id: int) -> tuple[int, int]:
    """Refresh canonical-name and surface-form vectors associated with a paper."""
    with session_scope() as session:
        entity_rows = _clean_rows(
            session.execute(
                select(Entity.id, Entity.name)
                .join(PaperEntityMention, PaperEntityMention.entity_id == Entity.id)
                .where(PaperEntityMention.paper_id == paper_id)
                .distinct()
                .order_by(Entity.id)
            ).all()
        )
        mention_texts = _clean_texts(
            session.execute(
                select(PaperEntityMention.surface_text)
                .where(PaperEntityMention.paper_id == paper_id)
                .distinct()
                .order_by(PaperEntityMention.surface_text)
            ).all()
        )

    # Encoding is deliberately outside a transaction: model work should not
    # hold row locks that block concurrent paper imports.
    entity_vectors = _vectors_by_value([row.text for row in entity_rows])
    mention_vectors = _vectors_by_value(mention_texts)
    with session_scope() as session:
        if entity_rows:
            session.execute(
                update(Entity),
                [
                    {"id": row.id, "embedding": entity_vectors[row.text]}
                    for row in entity_rows
                ],
            )
        if mention_texts:
            statement = insert(EntityMentionEmbedding).values(
                [
                    {"surface_text": text, "embedding": mention_vectors[text]}
                    for text in mention_texts
                ]
            )
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=["surface_text"],
                    set_={"embedding": statement.excluded.embedding},
                )
            )
    return len(entity_rows), len(mention_texts)


def backfill_missing_embeddings(batch_size: int = 256) -> tuple[int, int]:
    """Fill all currently missing vectors in bounded batches."""
    entity_count = 0
    surface_form_count = 0
    while True:
        with session_scope() as session:
            rows = _clean_rows(
                session.execute(
                    select(Entity.id, Entity.name)
                    .where(
                        Entity.embedding.is_(None),
                        Entity.name.is_not(None),
                        func.length(func.btrim(Entity.name)) > 0,
                    )
                    .order_by(Entity.id)
                    .limit(batch_size)
                ).all()
            )
        if not rows:
            break
        vectors = _vectors_by_value([row.text for row in rows])
        with session_scope() as session:
            session.execute(
                update(Entity),
                [{"id": row.id, "embedding": vectors[row.text]} for row in rows],
            )
        entity_count += len(rows)

    while True:
        with session_scope() as session:
            texts = _clean_texts(
                session.execute(
                    select(PaperEntityMention.surface_text)
                    .outerjoin(
                        EntityMentionEmbedding,
                        EntityMentionEmbedding.surface_text
                        == PaperEntityMention.surface_text,
                    )
                    .where(
                        EntityMentionEmbedding.id.is_(None),
                        PaperEntityMention.surface_text.is_not(None),
                        func.length(func.btrim(PaperEntityMention.surface_text)) > 0,
                    )
                    .distinct()
                    .order_by(PaperEntityMention.surface_text)
                    .limit(batch_size)
                ).all()
            )
        if not texts:
            break
        vectors = _vectors_by_value(texts)
        with session_scope() as session:
            session.execute(
                insert(EntityMentionEmbedding)
                .values([
                    {"surface_text": text, "embedding": vectors[text]}
                    for text in texts
                ])
                .on_conflict_do_nothing(index_elements=["surface_text"])
            )
        surface_form_count += len(texts)
    return entity_count, surface_form_count
