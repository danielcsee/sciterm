"""Clustering a group's papers into subgroups, and ordering and paging them.

Pure functions over plain data, so they are testable without a database.

Each paper is one vector: the mean of its paragraph embeddings, minus the
corpus-wide mean. Uncentred, paper means all lean the same way (measured on
this corpus: median pairwise cosine distance 0.12); centred, they spread out
(median 1.08), so a distance cutoff can tell topics apart.

Clustering is agglomerative with average linkage: every paper starts alone,
and the closest clusters merge until none are nearer than the cutoff. There is
no cluster count to pick, the result is deterministic, and a paper unlike the
rest stays a subgroup of one.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

#: Average cosine distance at which clusters stop merging. Chosen on this
#: corpus: at 0.7, fracture-risk, feline-ageing, and heart-transplant papers
#: each form one subgroup; at 0.9 unrelated topics begin to fuse.
DISTANCE_CUTOFF = 0.7

#: Below this norm a centred vector has no direction to compare.
_MIN_NORM = 1e-9

SortOrder = Literal["asc", "desc"]


@dataclass(frozen=True)
class MatchedPaper:
    paper_id: int
    #: Distinct group entities the paper mentions.
    match_count: int
    #: Mean paragraph embedding; None when the paper has no embedded chunks.
    embedding: Optional[np.ndarray]


def build_subgroups(
    papers: Sequence[MatchedPaper],
    corpus_mean: Optional[np.ndarray],
    cutoff: float = DISTANCE_CUTOFF,
) -> list[list[MatchedPaper]]:
    """Cluster papers; each subgroup is sorted by match count, most first."""
    labels = cluster_labels(papers, corpus_mean, cutoff)
    members: dict[int, list[MatchedPaper]] = {}
    for paper, label in zip(papers, labels):
        members.setdefault(label, []).append(paper)
    return [sort_members(group) for group in members.values()]


def cluster_labels(
    papers: Sequence[MatchedPaper],
    corpus_mean: Optional[np.ndarray],
    cutoff: float,
) -> list[int]:
    """One label per paper; equal labels share a subgroup.

    A paper without a usable vector keeps a label of its own.
    """
    labels = list(range(len(papers)))
    indices, vectors = _centred_vectors(papers, corpus_mean)
    if len(indices) < 2:
        return labels
    tree = linkage(np.vstack(vectors), method="average", metric="cosine")
    found = fcluster(tree, t=cutoff, criterion="distance")
    # Offset past the singleton labels so the two ranges cannot collide.
    for index, label in zip(indices, found):
        labels[index] = len(papers) + int(label)
    return labels


def sort_members(group: Sequence[MatchedPaper]) -> list[MatchedPaper]:
    """Most distinct entities first; paper id breaks ties for a stable order."""
    return sorted(group, key=lambda paper: (-paper.match_count, paper.paper_id))


def order_subgroups(
    subgroups: Sequence[list[MatchedPaper]], order: SortOrder
) -> list[list[MatchedPaper]]:
    """By size in `order`; equal sizes by best match count, then first paper id.

    The tiebreaks do not flip with `order`, so pages stay a total order either
    way. Expects each subgroup already sorted by `sort_members`.
    """
    sign = -1 if order == "desc" else 1
    return sorted(
        subgroups,
        key=lambda group: (sign * len(group), -group[0].match_count, group[0].paper_id),
    )


def page_of(
    items: Sequence[list[MatchedPaper]], page: int, page_size: int
) -> tuple[list[list[MatchedPaper]], int]:
    """One 1-based page of whole subgroups, and the total page count."""
    total_pages = math.ceil(len(items) / page_size)
    start = (page - 1) * page_size
    return list(items[start : start + page_size]), total_pages


def _centred_vectors(
    papers: Sequence[MatchedPaper], corpus_mean: Optional[np.ndarray]
) -> tuple[list[int], list[np.ndarray]]:
    """Indices of papers with a usable vector, and those vectors centred."""
    indices: list[int] = []
    vectors: list[np.ndarray] = []
    for index, paper in enumerate(papers):
        if paper.embedding is None:
            continue
        vector = paper.embedding if corpus_mean is None else paper.embedding - corpus_mean
        if np.linalg.norm(vector) < _MIN_NORM:
            continue
        indices.append(index)
        vectors.append(vector)
    return indices, vectors
