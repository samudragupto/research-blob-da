"""
EIP-4844 Blob Decoder and Dataset Reconstructor.

Reconstructs research datasets from retrieved blob sidecars:
- Parses domain-separated blob headers (magic 0x52424441, version, indices, tags).
- Unpacks field elements (FE31 / FE254).
- Reassembles compressed stream across blobs.
- Decompresses payload (zstd / raw).
- Verifies complete cryptographic integrity:
    1. contentHash matches keccak256(canonical_stream)
    2. recordsRoot matches MerkleTree(canonical_records).root
"""

from typing import Any

import zstandard as zstd

from .canonical import (
    compute_content_hash,
    deserialize_record_stream,
)
from .commitments import MerkleTree
from .encoder import (
    BYTES_PER_BLOB,
    HEADER_SIZE,
    parse_blob_header,
    unpack_fe31,
    unpack_fe254,
)


class DecodedDataset:
    """Container holding reconstructed records, metadata, and verification results."""

    def __init__(
        self,
        records: list[bytes],
        raw_stream: bytes,
        content_hash: bytes,
        records_root: bytes,
        header: dict[str, Any],
    ):
        self.records = records
        self.raw_stream = raw_stream
        self.content_hash = content_hash
        self.records_root = records_root
        self.header = header

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def raw_size(self) -> int:
        return len(self.raw_stream)


def decode_dataset(
    blobs: list[bytes],
    expected_content_hash: bytes | None = None,
    expected_records_root: bytes | None = None,
) -> DecodedDataset:
    """Decodes and verifies a dataset from a list of 128 KiB blob byte strings.

    Args:
        blobs: List of 128 KiB blob bytes, in order of blob_index.
        expected_content_hash: Optional expected 32-byte content hash for verification.
        expected_records_root: Optional expected 32-byte Merkle root for verification.

    Returns:
        DecodedDataset with validated records and streams.

    Raises:
        ValueError: If headers are inconsistent, payloads are corrupted, or commitments mismatch.
    """
    if not blobs:
        raise ValueError("No blobs provided for decoding")

    blob_count = len(blobs)
    body_chunks: list[bytes] = []
    first_header: dict[str, Any] | None = None

    for i, blob in enumerate(blobs):
        if len(blob) != BYTES_PER_BLOB:
            raise ValueError(
                f"Blob {i} has invalid size: {len(blob)} != {BYTES_PER_BLOB}"
            )

        # Unpack header in field element 0 (supports both FE31 and FE254)
        fe0 = int.from_bytes(blob[:32], byteorder="big")
        if (fe0 >> 216) == 0x52424441:  # FE31 ("RBDA" in bytes 1..4)
            header_raw = fe0.to_bytes(31, byteorder="big")
        elif ((fe0 >> 6) >> 216) == 0x52424441:  # FE254 ("RBDA" in bits 253..222)
            header_raw = (fe0 >> 6).to_bytes(31, byteorder="big")
        else:
            header_raw = (
                blob[1 : 1 + HEADER_SIZE] if blob[0] == 0x00 else blob[:HEADER_SIZE]
            )
        header = parse_blob_header(header_raw)

        if first_header is None:
            first_header = header
            if header["blob_count"] != blob_count:
                raise ValueError(
                    f"Header declared blob_count {header['blob_count']} but provided {blob_count}"
                )
        else:
            # Check consistency
            if header["codec"] != first_header["codec"]:
                raise ValueError(f"Codec mismatch in blob {i}")
            if header["packing"] != first_header["packing"]:
                raise ValueError(f"Packing mismatch in blob {i}")
            if header["content_tag"] != first_header["content_tag"]:
                raise ValueError(f"Content tag mismatch in blob {i}")

        if header["blob_index"] != i:
            raise ValueError(
                f"Blob index mismatch: expected {i}, got {header['blob_index']}"
            )

        packing = header["packing"]
        b_len = header["body_length"]

        if packing == 0:
            unpacked = unpack_fe31(blob)
            body = unpacked[HEADER_SIZE : HEADER_SIZE + b_len]
        elif packing == 1:
            total_payload_len = HEADER_SIZE + b_len
            unpacked = unpack_fe254(blob, expected_length=total_payload_len)
            body = unpacked[HEADER_SIZE : HEADER_SIZE + b_len]
        else:
            raise ValueError(f"Unsupported packing: {packing}")

        body_chunks.append(body)

    assert first_header is not None
    compressed_stream = b"".join(body_chunks)

    # Decompress
    codec = first_header["codec"]
    if codec == 1:
        dctx = zstd.ZstdDecompressor()
        raw_stream = dctx.decompress(compressed_stream)
    elif codec == 0:
        raw_stream = compressed_stream
    else:
        raise ValueError(f"Unsupported codec: {codec}")

    # Unpack records
    records = deserialize_record_stream(raw_stream)

    # Compute & verify commitments
    content_hash = compute_content_hash(raw_stream)
    if expected_content_hash is not None and content_hash != expected_content_hash:
        raise ValueError(
            f"Content hash mismatch: computed 0x{content_hash.hex()} != expected 0x{expected_content_hash.hex()}"
        )

    # Verify first 15 bytes match content tag in header
    expected_tag = content_hash[:15].hex()
    if first_header["content_tag"] != expected_tag:
        raise ValueError(
            f"Header tag 0x{first_header['content_tag']} != 0x{expected_tag}"
        )

    merkle_tree = MerkleTree(records=records)
    records_root = merkle_tree.root
    if expected_records_root is not None and records_root != expected_records_root:
        raise ValueError(
            f"Records root mismatch: computed 0x{records_root.hex()} != expected 0x{expected_records_root.hex()}"
        )

    return DecodedDataset(
        records=records,
        raw_stream=raw_stream,
        content_hash=content_hash,
        records_root=records_root,
        header=first_header,
    )
