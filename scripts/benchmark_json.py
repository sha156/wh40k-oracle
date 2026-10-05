"""Strict parsing for benchmark documents without changing their raw-byte evidence."""
import json


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def loads_benchmark_json(raw):
    """Reject repeated decoded names in every object, including nested metadata."""
    return json.loads(raw, object_pairs_hook=_unique_object)
