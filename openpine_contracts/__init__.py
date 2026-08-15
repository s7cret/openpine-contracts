"""OpenPine 5.0 contract kit. Zero runtime dependencies."""

from .hashing import canonical_dumps, content_hash
from .compatibility import admit
from .models import (
    Finality,
    RevisionState,
    SemanticProfile,
    WarmupMode,
)

__version__ = "0.1.0"

__all__ = [
    "Finality",
    "RevisionState",
    "SemanticProfile",
    "WarmupMode",
    "admit",
    "canonical_dumps",
    "content_hash",
    "__version__",
]
