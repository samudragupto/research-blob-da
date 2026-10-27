"""
Unit and property tests for EIP-4844 blob encoding and decoding.
"""

import os

import pytest
import zstandard as zstd

from python.decoder import decode_dataset
from python.encoder import (
    BYTES_PER_BLOB,
    FIELD_ELEMENTS_PER_BLOB,
    HEADER_SIZE,
    build_blob_header,
    compute_kzg_versioned_hash,
    encode_dataset,
    pack_fe31,
    pack_fe254,
    parse_blob_header,
    unpack_fe31,
    unpack_fe254,
)

# BLS12-381 scalar field modulus r
BLS_MODULUS = (
    52435875175126190479447740508185965837690552500527637822603658699938581184513
)


def test_fe31_pack_unpack_roundtrip():
    payload = os.urandom(1024)
    blob = pack_fe31(payload)
    assert len(blob) == BYTES_PER_BLOB

    # Verify every 32-byte element has high byte 0x00 and is < BLS_MODULUS
    for i in range(FIELD_ELEMENTS_PER_BLOB):
        word = blob[i * 32 : (i + 1) * 32]
        assert word[0] == 0x00
        val = int.from_bytes(word, byteorder="big")
        assert val < BLS_MODULUS

    unpacked = unpack_fe31(blob)
    assert unpacked[: len(payload)] == payload


def test_fe254_pack_unpack_roundtrip():
    payload = os.urandom(2048)
    blob = pack_fe254(payload)
    assert len(blob) == BYTES_PER_BLOB

    # Verify every 32-byte element has top 2 bits 0 and is < BLS_MODULUS
    for i in range(FIELD_ELEMENTS_PER_BLOB):
        word = blob[i * 32 : (i + 1) * 32]
        val = int.from_bytes(word, byteorder="big")
        assert (val >> 254) == 0
        assert val < BLS_MODULUS

    unpacked = unpack_fe254(blob, expected_length=len(payload))
    assert unpacked == payload


def test_blob_header_serialization():
    content_hash = os.urandom(32)
    hdr = build_blob_header(
        codec=1,
        layout=0,
        packing=0,
        blob_index=2,
        blob_count=5,
        body_length=65536,
        content_hash=content_hash,
    )
    assert len(hdr) == HEADER_SIZE
    parsed = parse_blob_header(hdr)
    assert parsed["magic"] == "RBDA"
    assert parsed["version"] == 1
    assert parsed["codec"] == 1
    assert parsed["layout"] == 0
    assert parsed["packing"] == 0
    assert parsed["blob_index"] == 2
    assert parsed["blob_count"] == 5
    assert parsed["body_length"] == 65536
    assert parsed["content_tag"] == content_hash[:15].hex()


def test_encode_decode_roundtrip_fe31_compressed():
    records = [{"step": i, "loss": 1.0 / (i + 1)} for i in range(100)]
    encoded = encode_dataset(records, compress=True, packing="fe31")

    assert len(encoded.blobs) >= 1
    assert len(encoded.blobs[0]) == BYTES_PER_BLOB
    assert len(encoded.versioned_hashes) == len(encoded.blobs)
    assert encoded.versioned_hashes[0].startswith(b"\x01")

    decoded = decode_dataset(
        encoded.blobs,
        expected_content_hash=encoded.content_hash,
        expected_records_root=encoded.records_root,
    )
    assert decoded.record_count == len(records)
    assert decoded.content_hash == encoded.content_hash
    assert decoded.records_root == encoded.records_root


def test_encode_decode_roundtrip_fe31_uncompressed():
    records = [{"item": f"entry_{i}", "val": i * 10} for i in range(50)]
    encoded = encode_dataset(records, compress=False, packing="fe31")

    decoded = decode_dataset(
        encoded.blobs,
        expected_content_hash=encoded.content_hash,
        expected_records_root=encoded.records_root,
    )
    assert decoded.record_count == len(records)


def test_encode_decode_roundtrip_fe254():
    records = [{"key": f"data_point_{i}", "val": i * 42} for i in range(80)]
    encoded = encode_dataset(records, compress=True, packing="fe254")

    decoded = decode_dataset(
        encoded.blobs,
        expected_content_hash=encoded.content_hash,
        expected_records_root=encoded.records_root,
    )
    assert decoded.record_count == len(records)


def test_multi_blob_encoding_and_reassembly():
    # Generate sufficient data to span across at least 2 blobs (> 127 KiB compressed)
    # Using incompressible random strings formatted as records
    records = [{"id": i, "payload": os.urandom(256).hex()} for i in range(600)]
    encoded = encode_dataset(records, compress=False, packing="fe31")

    assert len(encoded.blobs) > 1, f"Expected > 1 blob, got {len(encoded.blobs)}"
    assert len(encoded.versioned_hashes) == len(encoded.blobs)

    decoded = decode_dataset(
        encoded.blobs,
        expected_content_hash=encoded.content_hash,
        expected_records_root=encoded.records_root,
    )
    assert decoded.record_count == len(records)
    assert decoded.content_hash == encoded.content_hash
    assert decoded.records_root == encoded.records_root


def test_corrupted_payload_detection():
    records = [{"val": i} for i in range(20)]
    encoded = encode_dataset(records, compress=True, packing="fe31")

    # Corrupt a byte in the blob body
    corrupted_blob = bytearray(encoded.blobs[0])
    corrupted_blob[100] ^= 0xFF

    with pytest.raises((ValueError, zstd.ZstdError)):
        decode_dataset(
            [bytes(corrupted_blob)],
            expected_content_hash=encoded.content_hash,
            expected_records_root=encoded.records_root,
        )


def test_versioned_hash_kzg_format():
    blob = b"\x00" * BYTES_PER_BLOB
    vh = compute_kzg_versioned_hash(blob)
    assert len(vh) == 32
    assert vh[0] == 0x01  # EIP-4844 version byte
