"""Backfill vectors introduced for entity matching.

    python -m api.ingestion.backfill_entity_embeddings
"""

from __future__ import annotations

import logging

from api.ingestion.entity_embeddings import backfill_missing_embeddings


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    entities, surface_forms = backfill_missing_embeddings()
    print(f"embedded {entities} entities and {surface_forms} mention surface forms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
