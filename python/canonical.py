"""
Canonical JSON and record-stream serialization for research datasets.

Adheres strictly to RFC 8785 (JSON Canonicalization Scheme) subset:
- Object keys are sorted lexicographically by UTF-16 / UTF-8 code point order.
- No insignificant whitespace (no space after colons or commas).
- Floats are formatted with consistent decimal notation without exponents where feasible.
- Strings use standard JSON escaping.

Framing:
A dataset consists of an ordered sequence of canonical records. The canonical stream format is:
    [4-byte big-endian length][record_bytes]...
`contentHash` is defined as `keccak256(canonical_stream)`.
"""

import json
from collections.abc import Sequence
from typing import Any

from Crypto.Hash import keccak


def canonical_json_bytes(obj: Any) -> bytes:
    """Serializes a Python object into canonical JSON bytes (RFC 8785 subset).

    Args:
        obj: Dictionary, list, or primitive value.

    Returns:
        UTF-8 encoded canonical JSON bytes with sorted keys and no whitespace.
    """
    if isinstance(obj, float):
        # Format cleanly: if integer-valued, keep float representation or clean decimal
        if obj.is_integer():
            s = f"{int(obj)}.0"
        else:
            # Up to 8 decimal places for consistency without trailing zeros
            s = f"{obj:.8f}".rstrip("0")
            if s.endswith("."):
                s += "0"
        return s.encode("utf-8")

    # json.dumps with separators=(',', ':') and sort_keys=True
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def serialize_record_stream(records: Sequence[bytes | str | dict[str, Any]]) -> bytes:
    """Packs an ordered sequence of records into a length-prefixed canonical stream.

    Format:
        For each record: [uint32_be length] || [record bytes]

    Args:
        records: Sequence of raw bytes, JSON strings, or dicts.

    Returns:
        The concatenated canonical stream bytes.
    """
    chunks: list[bytes] = []
    for r in records:
        if isinstance(r, dict):
            b = canonical_json_bytes(r)
        elif isinstance(r, str):
            b = r.encode("utf-8")
        elif isinstance(r, (bytes, bytearray)):
            b = bytes(r)
        else:
            b = canonical_json_bytes(r)

        length_prefix = len(b).to_bytes(4, byteorder="big")
        chunks.append(length_prefix + b)

    return b"".join(chunks)


def deserialize_record_stream(stream: bytes) -> list[bytes]:
    """Unpacks a length-prefixed canonical stream into individual record byte strings.

    Args:
        stream: Canonical stream bytes.

    Returns:
        List of record bytes.

    Raises:
        ValueError: If the stream is truncated or has invalid framing.
    """
    records: list[bytes] = []
    offset = 0
    total = len(stream)
    while offset < total:
        if offset + 4 > total:
            raise ValueError(f"Truncated stream length header at offset {offset}")
        rec_len = int.from_bytes(stream[offset : offset + 4], byteorder="big")
        offset += 4
        if offset + rec_len > total:
            raise ValueError(
                f"Truncated record at offset {offset}, expected {rec_len} bytes"
            )
        records.append(stream[offset : offset + rec_len])
        offset += rec_len
    return records


def compute_content_hash(stream: bytes) -> bytes:
    """Computes keccak256 of the canonical record stream.

    Args:
        stream: Canonical stream bytes.

    Returns:
        32-byte keccak256 digest.
    """
    k = keccak.new(digest_bits=256)
    k.update(stream)
    return k.digest()
