"""
Unit tests for the real academic dataset (OpenAlex) pipeline and manifest verification.
"""

import hashlib
import json
import os

import pandas as pd

from python.canonical import serialize_record_stream
from python.decoder import decode_dataset
from python.encoder import encode_dataset
from python.fetch_real_data import extract_work_record, verify_manifest


def test_real_data_manifest_verification():
    """Verifies that the committed real OpenAlex dataset matches its manifest checksum."""
    json_path = "data/real_academic_openalex.json"
    manifest_path = "data/real_academic_openalex_manifest.json"

    assert os.path.exists(json_path), f"Real dataset file not found: {json_path}"
    assert os.path.exists(manifest_path), f"Manifest file not found: {manifest_path}"

    assert verify_manifest(json_path, manifest_path) is True


def test_real_data_record_structure():
    """Validates the schema and field types of the records in the real dataset."""
    json_path = "data/real_academic_openalex.json"
    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    assert len(records) >= 500
    first = records[0]
    assert "id" in first and first["id"].startswith("https://openalex.org/W")
    assert "title" in first and len(first["title"]) > 0
    assert "publication_year" in first and isinstance(first["publication_year"], int)
    assert "cited_by_count" in first and isinstance(first["cited_by_count"], int)
    assert "is_oa" in first and isinstance(first["is_oa"], bool)
    assert "concepts" in first and isinstance(first["concepts"], list)


def test_extract_work_record_normalization():
    """Tests normalizer handles malformed or partial OpenAlex API responses safely."""
    raw_sample = {
        "id": "https://openalex.org/W12345",
        "doi": "https://doi.org/10.1000/182",
        "title": "Quantum Error Correction via Topological Codes",
        "publication_year": 2023,
        "publication_date": "2023-05-12",
        "cited_by_count": 42,
        "type": "article",
        "authorships": [{"author": {"display_name": "Alice Smith"}}],
        "open_access": {"is_oa": True},
        "concepts": [
            {"display_name": "Quantum computing"},
            {"display_name": "Topology"},
        ],
    }
    extracted = extract_work_record(raw_sample)
    assert extracted["id"] == "https://openalex.org/W12345"
    assert extracted["title"] == "Quantum Error Correction via Topological Codes"
    assert extracted["first_author"] == "Alice Smith"
    assert extracted["is_oa"] is True
    assert extracted["concepts"] == ["Quantum computing", "Topology"]


def test_real_data_pipeline_end_to_end():
    """Runs full encode, commit, chunk, decode, and verify pipeline on the real dataset."""
    json_path = "data/real_academic_openalex.json"
    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Encode with Zstandard compression and FE31 packing
    encoded = encode_dataset(records, codec=1, packing=0, zstd_level=3)
    assert encoded.record_count == len(records)
    assert encoded.blob_count >= 1
    assert encoded.compression_ratio > 1.0
    assert len(encoded.records_root) == 32
    assert len(encoded.content_hash) == 32

    # Decode and verify cryptographic commitments
    decoded = decode_dataset(
        encoded.blobs,
        expected_content_hash=encoded.content_hash,
        expected_records_root=encoded.records_root,
    )
    assert decoded.record_count == len(records)
    # Validate first record content matches
    decoded_first = json.loads(decoded.records[0].decode("utf-8"))
    assert decoded_first["id"] == records[0]["id"]
    assert decoded_first["title"] == records[0]["title"]


def test_real_data_source_vs_canonical_reconciliation():
    """Validates the distinction between source file bytes and canonical payload bytes,

    and ensures generated benchmark CSV rows match committed files exactly.
    """
    json_path = "data/real_academic_openalex.json"
    manifest_path = "data/real_academic_openalex_manifest.json"
    csv_path = "benchmarks/cost_comparison_compressed.csv"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(json_path, "rb") as f:
        raw_content = f.read().replace(b"\r\n", b"\n")

    # 1. Manifest source_file_bytes equals actual byte size of committed fixture (with LF)
    assert manifest["source_file_bytes"] == len(raw_content) == 264057

    # 2. Manifest source_file_sha256 matches committed fixture
    computed_src_sha256 = hashlib.sha256(raw_content).hexdigest()
    assert (
        manifest["source_file_sha256"]
        == computed_src_sha256
        == "af65584227c707d3c16f7841a233070808ab1ed070f10f32e841082889a8c544"
    )

    # 3. Canonical payload byte count produced by pipeline equals CSV value
    records = json.loads(raw_content.decode("utf-8"))
    canonical_stream = serialize_record_stream(records)
    canonical_bytes = len(canonical_stream)
    assert canonical_bytes == 212517
    assert manifest["canonical_payload_bytes"] == canonical_bytes
    assert (
        manifest["canonical_payload_sha256"]
        == hashlib.sha256(canonical_stream).hexdigest()
    )

    df = pd.read_csv(csv_path)
    openalex_row = df[df["dataset_name"].str.contains("OpenAlex")].iloc[0]
    assert int(openalex_row["source_file_bytes"]) == 264057
    assert int(openalex_row["canonical_payload_bytes"]) == 212517

    # 4. Compression ratio definition equals canonical_payload_bytes / compressed_bytes
    expected_ratio = round(canonical_bytes / int(openalex_row["compressed_bytes"]), 2)
    assert float(openalex_row["compression_ratio"]) == expected_ratio == 4.13

    # 5. OpenAlex encoding mean and std in generated tables match CSV source
    with open("benchmarks/generated_tables.md", "r", encoding="utf-8") as f:
        tables_md = f.read()

    expected_time_str = f"{openalex_row['encoding_time_mean_ms']:.1f} ms ± {openalex_row['encoding_time_std_ms']:.1f} ms"
    assert expected_time_str in tables_md
