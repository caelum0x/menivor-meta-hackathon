"""Minimal extraction: the shared provider error taxonomy.

This is NOT the full Kling/fal.ai video adapter (that lives in the private
Menivor codebase and is unrelated to this hackathon submission). It is kept
at this import path (``kling_fal.KlingError``) only because every adapter in
Menivor's routing/providers package — including the two new Meta Model API
adapters in this repo — imports its error taxonomy from here, and the goal of
this extraction is for the two new files to import and run unmodified from
their real source locations.
"""

from __future__ import annotations

ACCEPTANCE_DEFINITE_NO = "definitely_not_accepted"
ACCEPTANCE_UNKNOWN = "unknown"
_ACCEPTANCE_VALUES = {ACCEPTANCE_DEFINITE_NO, ACCEPTANCE_UNKNOWN}


class KlingError(RuntimeError):
    """A provider-adapter error. Shared by every adapter in this package,
    named after the first adapter (Kling) that defined it."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "provider",
        retryable: bool = False,
        status: int = 0,
        acceptance: str = ACCEPTANCE_DEFINITE_NO,
    ) -> None:
        if acceptance not in _ACCEPTANCE_VALUES:
            raise ValueError(f"invalid provider acceptance certainty: {acceptance!r}")
        self.kind = kind  # auth | validation | rate_limit | transient | provider
        self.retryable = retryable
        self.status = status
        self.acceptance = acceptance
        super().__init__(message)

    @property
    def may_have_been_accepted(self) -> bool:
        return self.acceptance == ACCEPTANCE_UNKNOWN
