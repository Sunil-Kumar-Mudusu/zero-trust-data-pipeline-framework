"""Custom exception hierarchy for the Zero-Trust Data Pipeline Framework."""


class ZTDPFError(Exception):
    """Base exception for all ZTDPF errors."""
    pass


class IngestionError(ZTDPFError):
    """Raised when data ingestion fails."""
    pass


class SchemaValidationError(ZTDPFError):
    """Raised when schema validation encounters a fatal error."""
    pass


class PolicyViolationError(ZTDPFError):
    """Raised when a zero-trust policy violation is detected."""
    pass


class TrustScoreError(ZTDPFError):
    """Raised when trust score calculation fails."""
    pass


class LineageError(ZTDPFError):
    """Raised when lineage recording fails."""
    pass


class MetadataStoreError(ZTDPFError):
    """Raised when metadata persistence fails."""
    pass
