"""OpenPine contracts: schemas, hashing, validation, and compatibility."""

from .compatibility import AdmitPolicy, AdmitRequest, AdmitResult, admit, evaluate_admit
from .errors import (
    AdmitError,
    CanonicalizationError,
    ContractError,
    MoneyError,
    SchemaNotFoundError,
    SchemaValidationError,
    SchemaValidatorUnavailableError,
    WorkerProtocolSemanticError,
)
from .hashing import (
    SERIALIZER_ID,
    canonical_dumps,
    content_hash,
    seal_content_hash,
    verify_content_hash,
)
from .models import (
    ArtifactEnvelope,
    Finality,
    IntentKind,
    JobState,
    RevisionState,
    RunMode,
    SemanticProfile,
    SupportStatus,
    WarmupMode,
)
from .money import DECIMAL_POLICY, Money, decimal_string, unsafe_decimal_from_float
from .registry import get_schema, list_schema_ids, schema_bytes, schema_hash
from .validate import validate_payload
from .worker_protocol import aggregate_batch_hash, validate_worker_protocol_sequence

__version__ = "5.0.0rc4"

__all__ = [
    "AdmitError",
    "AdmitPolicy",
    "AdmitRequest",
    "AdmitResult",
    "ArtifactEnvelope",
    "CanonicalizationError",
    "ContractError",
    "DECIMAL_POLICY",
    "Finality",
    "IntentKind",
    "JobState",
    "Money",
    "MoneyError",
    "RevisionState",
    "RunMode",
    "SERIALIZER_ID",
    "SchemaNotFoundError",
    "SchemaValidationError",
    "SchemaValidatorUnavailableError",
    "SemanticProfile",
    "SupportStatus",
    "WarmupMode",
    "WorkerProtocolSemanticError",
    "__version__",
    "admit",
    "aggregate_batch_hash",
    "canonical_dumps",
    "content_hash",
    "decimal_string",
    "evaluate_admit",
    "get_schema",
    "list_schema_ids",
    "schema_bytes",
    "schema_hash",
    "seal_content_hash",
    "unsafe_decimal_from_float",
    "validate_payload",
    "validate_worker_protocol_sequence",
    "verify_content_hash",
]
