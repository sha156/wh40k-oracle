"""Persistent source retirement, shared by raw and derived ingestion paths.

Retired files can remain in an excluded archive, but copying their PDF or
refined cache back must not silently restore them to the active corpus.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def _policy() -> dict:
    # Missing/malformed policy must fail closed rather than resurrect sources.
    policy = json.loads(Path(__file__).with_name("corpus_policy.json").read_text(encoding="utf-8"))
    for key in ("excluded_stems", "excluded_book_names"):
        values = policy[key]
        if not isinstance(values, list) or any(
                not isinstance(s, str) or not s.strip() for s in values):
            raise ValueError(f"corpus_policy.{key} must contain nonempty strings")
        policy[key] = frozenset(s.casefold() for s in values)
    return policy


def is_excluded_source(source: str | Path) -> bool:
    """Match exact PDF stems or cache directory components on either OS."""
    parts = str(source).replace("\\", "/").split("/")
    excluded = _policy()["excluded_stems"]
    return any((part[:-4] if part.lower().endswith(".pdf") else part).casefold() in excluded
               for part in parts)


def is_excluded_book(book: str | Path) -> bool:
    """Match a source path/stem or an exact recorded metadata book label.

    Shortened book labels are scoped to this metadata API, never applied to
    path components, unit names or canonical IDs. No substring/version guessing.
    """
    return (is_excluded_source(book)
            or str(book).casefold() in _policy()["excluded_book_names"])


def require_active_source(source: str | Path) -> None:
    if is_excluded_source(source):
        raise ValueError(f"Source retired by corpus_policy.json: {source}")
