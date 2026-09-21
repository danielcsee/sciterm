"""Group paper search: a group's papers, clustered into subgroups of similar topics.

    GET /groups/{group_id}/papers?order=desc&page=1&page_size=10
    GET /entities/papers?entity_ids=1&entity_ids=2&order=desc&page=1
"""

from api.group_search.routes import router

__all__ = ["router"]
