"""
test_adversarial.py: Adversarial Test Suite for research-blob-da.

Tests all 15 threat scenarios against the integrity, commitment, and reconstruction pipelines:
- Bit flips and corrupted bytes
- Omitted / reordered records
- Position-binding Merkle violations
- Missing / reordered / duplicate blobs
- Content hash and metadata mismatches
- Dual-horizon archival tampering
"""

import json

import pytest

from python.adversarial_evaluation import run_threat_model_evaluation
from python.commitments import MerkleTree, keccak256, verify_proof
from python.encoder import (
    HEADER_SIZE,
    encode_dataset,
    unpack_fe31,
)


def test_threat_model_suite_execution():
    """Runs the 15-scenario threat model runner and verifies 100% detection rate."""
    run_threat_model_evaluation()
    with open(
        "benchmarks/journal-extension/security/results.json",
        "r",
        encoding="utf-8",
    ) as f:
        res = json.load(f)
    assert res["scenarios_tested"] == 15
    assert res["detection_rate_pct"] == 100.0


def test_bit_flip_in_blob_detected():
    records = [{"id": 1, "test": "DATA_ALPHA"}]
    encoded = encode_dataset(records, zstd_level=3)
    blob = bytearray(encoded.blobs[0])
    # Flip a bit in the body
    blob[HEADER_SIZE + 5] ^= 0x01

    import zstandard as zstd

    with pytest.raises((ValueError, RuntimeError, zstd.ZstdError)):
        unpacked = unpack_fe31(bytes(blob))
        # Decompression or verification must fail
        zstd.ZstdDecompressor().decompress(unpacked[HEADER_SIZE:])


def test_reordered_records_change_merkle_root():
    rec1 = b'{"id":1}'
    rec2 = b'{"id":2}'
    tree_normal = MerkleTree(records=[rec1, rec2])
    tree_reversed = MerkleTree(records=[rec2, rec1])
    assert tree_normal.root != tree_reversed.root


def test_omitted_record_fails_merkle_verification():
    rec1 = b'{"id":1}'
    rec2 = b'{"id":2}'
    tree = MerkleTree(records=[rec1, rec2])
    proof = tree.get_proof(0)

    # Verifying wrong leaf against proof must fail
    wrong_leaf = keccak256(b"FAKE_LEAF")
    assert verify_proof(tree.root, 2, 0, wrong_leaf, proof) is False
