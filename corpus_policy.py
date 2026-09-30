"""Persistent source retirement, shared by raw and derived ingestion paths.

Retired files can remain in an excluded archive, but copying their PDF or
refined cache back must not silently restore them to the active corpus.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def _excluded_stems() -> frozenset[str]:
    # Missing/malformed policy must fail closed rather than resurrect sources.
    policy = json.loads(Path(__file__).with_name("corpus_policy.json").read_text(encoding="utf-8"))
    stems = policy["excluded_stems"]
    if not isinstance(stems, list) or any(not isinstance(s, str) or not s.strip() for s in stems):
        raise ValueError("corpus_policy.excluded_stems must contain nonempty strings")
    return frozenset(s.casefold() for s in stems)


def is_excluded_source(source: str | Path) -> bool:
    """Match exact PDF stems or cache directory components on either OS."""
    parts = str(source).replace("\\", "/").split("/")
    excluded = _excluded_stems()
    return any((part[:-4] if part.lower().endswith(".pdf") else part).casefold() in excluded
               for part in parts)


def require_active_source(source: str | Path) -> None:
    if is_excluded_source(source):
        raise ValueError(f"Source retired by corpus_policy.json: {source}")
