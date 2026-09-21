"""Build search terms from confirmed entities or from the query's noun phrases."""

from __future__ import annotations

import re
from collections.abc import Sequence

from spacy.lang.en.stop_words import STOP_WORDS

from api.entity_matching import QueryFragment
from api.llm.models import IntentEntity
from api.paper_search.models import SearchTerm

#: Nouns that frame a request rather than name its subject: "find *papers*
#: on...". Matching them would reward nearly every paper with a covered term.
REQUEST_NOUNS = frozenset(
    {
        "article",
        "articles",
        "literature",
        "paper",
        "papers",
        "publication",
        "publications",
        "research",
        "studies",
        "study",
        "work",
    }
)

_WORD_RE = re.compile(r"[\w-]+")


def entity_terms(entities: Sequence[IntentEntity]) -> list[SearchTerm]:
    """One term per distinct query phrase, holding every entity it resolved to."""
    by_phrase: dict[str, tuple[str, list[int]]] = {}
    for entity in entities:
        key = entity.phrase.casefold()
        phrase, entity_ids = by_phrase.setdefault(key, (entity.phrase, []))
        if entity.entity_id not in entity_ids:
            entity_ids.append(entity.entity_id)
    return [SearchTerm(phrase, tuple(ids)) for phrase, ids in by_phrase.values()]


def noun_phrase_terms(fragments: Sequence[QueryFragment]) -> list[SearchTerm]:
    """The query's noun phrases, minus ones made only of stop and request words."""
    terms: list[SearchTerm] = []
    seen: set[str] = set()
    for fragment in fragments:
        key = fragment.text.casefold()
        if fragment.method != "noun_phrase" or key in seen or not _is_topical(key):
            continue
        seen.add(key)
        terms.append(SearchTerm(fragment.text))
    return terms


def _is_topical(phrase: str) -> bool:
    words = _WORD_RE.findall(phrase)
    return any(word not in STOP_WORDS and word not in REQUEST_NOUNS for word in words)
