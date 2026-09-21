"""Postgres trigram and vector candidate retrieval for query fragments."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Float, bindparam, func, select
from sqlalchemy.orm import Session

from api.db.models import Entity, EntityMentionEmbedding, PaperEntityMention
from api.entity_matching.extraction import QueryFragment
from api.entity_matching.models import (
    EntityMatch,
    EntityMatchGroup,
    MatchMethod,
    MatchSource,
)


class EntityMatchManager:
    """Execute all entity candidate queries through one database session."""

    def __init__(
        self,
        session: Session,
        *,
        top_k: int,
        embedding_threshold: float,
        trigram_threshold: float,
    ) -> None:
        self._session = session
        self._top_k = top_k
        self._embedding_threshold = embedding_threshold
        self._trigram_threshold = trigram_threshold

    @staticmethod
    def _match(row: object) -> EntityMatch:
        return EntityMatch(
            entity_id=row.entity_id,
            identifier=row.identifier,
            entity_type=row.entity_type,
            database=row.database,
            name=row.name,
            matched_text=row.matched_text,
            score=round(float(row.score), 6),
        )

    def _unique_matches(self, rows: Sequence[object]) -> list[EntityMatch]:
        """Collapse repeated occurrences without disturbing score order."""
        matches: list[EntityMatch] = []
        seen: set[tuple[int, str]] = set()
        for row in rows:
            key = (row.entity_id, row.matched_text.casefold())
            if key in seen:
                continue
            seen.add(key)
            matches.append(self._match(row))
            if len(matches) == self._top_k:
                break
        return matches

    def _trigram_matches(
        self, fragment: QueryFragment, source: MatchSource
    ) -> list[EntityMatch]:
        if source == "entity_name":
            text_column = Entity.name
            statement = select(
                Entity.id.label("entity_id"),
                Entity.identifier,
                Entity.entity_type,
                Entity.database,
                Entity.name,
                Entity.name.label("matched_text"),
                func.similarity(Entity.name, fragment.text).label("score"),
            ).where(Entity.name.is_not(None))
        else:
            text_column = PaperEntityMention.surface_text
            statement = (
                select(
                    Entity.id.label("entity_id"),
                    Entity.identifier,
                    Entity.entity_type,
                    Entity.database,
                    Entity.name,
                    PaperEntityMention.surface_text.label("matched_text"),
                    func.similarity(PaperEntityMention.surface_text, fragment.text).label(
                        "score"
                    ),
                )
                .join(Entity, Entity.id == PaperEntityMention.entity_id)
                .where(PaperEntityMention.surface_text.is_not(None))
            )
        score = func.similarity(text_column, fragment.text)
        distance = text_column.op("<->")(fragment.text)
        rows = self._session.execute(
            statement.where(score >= self._trigram_threshold)
            .order_by(distance)
            .limit(self._top_k if source == "entity_name" else self._top_k * 10)
        ).all()
        return self._unique_matches(rows)

    def _embedding_matches(
        self,
        fragment: QueryFragment,
        vector: Sequence[float],
        source: MatchSource,
    ) -> list[EntityMatch]:
        if source == "entity_name":
            vector_column = Entity.embedding
            entity_statement = select(
                Entity.id.label("entity_id"),
                Entity.identifier,
                Entity.entity_type,
                Entity.database,
                Entity.name,
                Entity.name.label("matched_text"),
            ).where(Entity.name.is_not(None))
        else:
            vector_column = EntityMentionEmbedding.embedding
            surface_entities = (
                select(
                    PaperEntityMention.entity_id,
                    PaperEntityMention.surface_text,
                )
                .where(PaperEntityMention.surface_text.is_not(None))
                .distinct()
                .subquery()
            )
            entity_statement = (
                select(
                    Entity.id.label("entity_id"),
                    Entity.identifier,
                    Entity.entity_type,
                    Entity.database,
                    Entity.name,
                    EntityMentionEmbedding.surface_text.label("matched_text"),
                )
                .select_from(EntityMentionEmbedding)
                .join(
                    surface_entities,
                    surface_entities.c.surface_text == EntityMentionEmbedding.surface_text,
                )
                .join(Entity, Entity.id == surface_entities.c.entity_id)
            )
        query_vector = bindparam("entity_query_vector", value=list(vector), type_=vector_column.type)
        distance = vector_column.cosine_distance(query_vector)
        score = (1 - distance).cast(Float)
        rows = self._session.execute(
            entity_statement.add_columns(score.label("score"))
            .where(vector_column.is_not(None), score >= self._embedding_threshold)
            .order_by(distance)
            .limit(self._top_k if source == "entity_name" else self._top_k * 10)
        ).all()
        return self._unique_matches(rows)

    def search(
        self,
        fragments: Sequence[QueryFragment],
        vectors: Sequence[Sequence[float]],
    ) -> list[EntityMatchGroup]:
        """Return a group for every fragment, matcher, and searched column."""
        if len(fragments) != len(vectors):
            raise ValueError("every query fragment must have one embedding")
        groups: list[EntityMatchGroup] = []
        for fragment, vector in zip(fragments, vectors):
            for method in ("trigram", "embedding"):
                for source in ("entity_name", "mention_surface_text"):
                    matches = self._search_path(fragment, vector, method, source)
                    groups.append(
                        EntityMatchGroup(
                            query_fragment=fragment.text,
                            extraction_method=fragment.method,
                            match_method=method,
                            source=source,
                            matches=matches,
                        )
                    )
        return groups

    def _search_path(
        self,
        fragment: QueryFragment,
        vector: Sequence[float],
        method: MatchMethod,
        source: MatchSource,
    ) -> list[EntityMatch]:
        if method == "trigram":
            return self._trigram_matches(fragment, source)
        return self._embedding_matches(fragment, vector, source)
