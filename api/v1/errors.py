"""Domain errors raised by the repository/service layers.

Repositories must not depend on FastAPI. They raise these plain exceptions; an
app-level handler (see api.main) maps them to HTTP responses, keeping the data
layer transport-agnostic and unit-testable without a web stack.
"""

from __future__ import annotations


class EntityNotFoundError(Exception):
    """A requested row does not exist. Mapped to HTTP 404."""
