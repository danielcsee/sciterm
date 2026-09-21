"""Entity groups: named, shared sets of corpus entities.

    GET/POST /groups, PATCH/DELETE /groups/{id}, GET /entities/suggest?q=

Ungated — anyone can read and edit any group.
"""

from api.groups.routes import router

__all__ = ["router"]
