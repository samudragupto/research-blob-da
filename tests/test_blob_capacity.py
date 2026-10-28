"""
test_blob_capacity.py: Strict validation of blob capacity formulas and recomputed blob counts.
"""

import math
import os

import pandas as pd

from python.encoder import (
    BODY_CAPACITY_FE31,
    BODY_CAPACITY_FE254,
    calculate_blob_count,
    get_usable_payload_bytes_per_blob,
)


def test_capacity_constants_and_formula():
    """Validates the mathematical derivation of usable payload body capacity."""
    # FE31: 4096 elements * 31 bytes - 31 bytes header = 126,945 bytes
    assert BODY_CAPACITY_FE31 == 126945
    assert get_usable_payload_bytes_per_blob(0) == 126945
    assert get_usable_payload_bytes_per_blob("fe31") == 126945

    # FE254: ((4096 * 254) // 8) - 31 bytes header = 130,017 bytes
    assert BODY_CAPACITY_FE254 == 130017
    assert get_usable_payload_bytes_per_blob(1) == 130017
    assert get_usable_payload_bytes_per_blob("fe254") == 130017


def test_uncompressed_theoretical_payload_blob_counts():
    """Asserts exact blob counts for canonical power-of-two scaling benchmarks."""
    # 1 MiB (1,048,576 bytes): ceil(1,048,576 / 126,945) = 9 blobs
    assert calculate_blob_count(1024 * 1024, "fe31") == 9
    assert math.ceil(1048576 / 126945) == 9

    # 5 MiB (5,242,880 bytes): ceil(5,242,880 / 126,945) = 42 blobs
    assert calculate_blob_count(5 * 1024 * 1024, "fe31") == 42
    assert math.ceil(5242880 / 126945) == 42

    # 20 MiB (20,971,520 bytes): ceil(20,971,520 / 126,945) = 166 blobs
    assert calculate_blob_count(20 * 1024 * 1024, "fe31") == 166
    assert math.ceil(20971520 / 126945) == 166


def test_summary_local_matrix_blob_counts_consistency():
    """Asserts every dataset in summary_local_matrix.csv matches exact recomputed blob count."""
    csv_path = "benchmarks/journal-extension/local/summary_local_matrix.csv"
    assert os.path.exists(csv_path), f"Missing summary matrix: {csv_path}"

    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        comp_bytes = int(row["compressed_bytes"])
        reported_blobs = int(row["blobs_needed"])
        expected_blobs = calculate_blob_count(comp_bytes, "fe31")
        assert (
            reported_blobs == expected_blobs
        ), f"Blob count mismatch in {row['dataset_id']}: reported {reported_blobs} != expected {expected_blobs} for {comp_bytes} compressed bytes"
