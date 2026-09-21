"""Per-matcher score cutoffs, read from a TOML file once per process."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from api.app.config import get_settings
from api.entity_matching.models import MatchMethod

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class MatchCutoffs(BaseModel):
    """Minimum score per matcher; the matchers score on different scales."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trigram: float = Field(ge=0, le=1)
    embedding: float = Field(ge=0, le=1)

    def for_method(self, method: MatchMethod) -> float:
        return getattr(self, method)


def load_cutoffs(path: Path) -> MatchCutoffs:
    """Parse and validate a cutoffs file; a bad file raises rather than defaults."""
    with path.open("rb") as handle:
        return MatchCutoffs.model_validate(tomllib.load(handle))


@lru_cache(maxsize=1)
def get_cutoffs() -> MatchCutoffs:
    """The configured cutoffs. Called at startup so a bad file fails the boot."""
    return load_cutoffs(get_settings().entity_match_cutoffs_path)
