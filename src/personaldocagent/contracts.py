# -------------------------------------------------------------------
# Application  : personalDocAgent
# Script       : contracts.py
# Version      : 0.1.0
# Date         : 2026-11-11
# Design       : TSC + Mistral Vibe
# Build        : Mistral Vibe
# -------------------------------------------------------------------
"""Interface contracts (dataclasses) exchanged between the pipeline modules."""

from dataclasses import dataclass, field


@dataclass
class AcquisitionResult:
    """Output of step 0: accepted file and its extracted text (persisted in conversion)."""

    source_file: str
    route: str
    text: str
    model: str | None
    conversion_date: str


@dataclass
class AnalysisRecord:
    """Output of the agent-driven step 2: constrained decisions produced by the model."""

    category_id: int
    issuer_candidate: str | None
    keywords: list[str]
    summary: str
    attributes: dict
    confidence: float

    def validate(self, max_keywords: int) -> None:
        """Reject a record whose keyword count exceeds the analysis policy."""
        if len(self.keywords) > max_keywords:
            raise ValueError(f"{len(self.keywords)} keywords > limit of {max_keywords}")


@dataclass
class IssuerMatch:
    """Output of issuer matching: known, ambiguous or unknown."""

    status: str
    issuer_id: int | None = None
    proposed_label: str | None = None


@dataclass
class DocumentRecord:
    """Complete record assembled before the step 4 write (Dublin Core + technical columns + child tables)."""

    dc_title: str | None = None
    dc_date: str | None = None
    dc_type: str | None = None
    dc_format: str | None = None
    dc_identifier: str | None = None
    dc_language: str | None = None
    dc_rights: str | None = None
    source_file: str = ""
    date_added: str = ""
    status: str = "active"
    reference: str | None = None
    attributes: str = "{}"
    agents: list[tuple[str, str]] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    issuer_id: int | None = None
    categories: list[tuple[int, bool]] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class WriteResult:
    """Output of step 4: whether the document was written to the database."""

    doc_id: int
    written: bool
    reason: str | None = None


@dataclass
class SearchFilters:
    """Filters of the search_documents tool (query mode, read-only)."""

    category_id: int | None = None
    issuer_id: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    dc_type: str | None = None
    status: str | None = None
    keyword: str | None = None
