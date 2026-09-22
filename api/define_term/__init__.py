"""Plain-language definitions of phrases a reader highlights.

    POST /define {phrase, surrounding_context} -> {definition}
"""

from api.define_term.routes import router

__all__ = ["router"]
