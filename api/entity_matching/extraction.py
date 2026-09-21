"""Turn a free-text query into observable entity-search fragments."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import spacy
from spacy.language import Language

ExtractionMethod = Literal["noun_phrase", "three_gram"]


@dataclass(frozen=True)
class QueryFragment:
    text: str
    method: ExtractionMethod


@lru_cache(maxsize=1)
def get_nlp() -> Language:
    """Load the parser once per API process."""
    return spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])


def _normalise(text: str) -> str:
    return " ".join(text.split()).strip()


def _unique_fragments(fragments: list[QueryFragment]) -> list[QueryFragment]:
    seen: set[tuple[ExtractionMethod, str]] = set()
    unique: list[QueryFragment] = []
    for fragment in fragments:
        key = (fragment.method, fragment.text.casefold())
        if not fragment.text or key in seen:
            continue
        seen.add(key)
        unique.append(fragment)
    return unique


def extract_query_fragments(query: str) -> list[QueryFragment]:
    """Return spaCy noun chunks followed by contiguous three-token n-grams."""
    doc = get_nlp()(_normalise(query))
    fragments = [
        QueryFragment(_normalise(chunk.text), "noun_phrase")
        for chunk in doc.noun_chunks
    ]
    words = [token.text for token in doc if not token.is_space and not token.is_punct]
    fragments.extend(
        QueryFragment(" ".join(words[index : index + 3]), "three_gram")
        for index in range(max(0, len(words) - 2))
    )
    return _unique_fragments(fragments)
