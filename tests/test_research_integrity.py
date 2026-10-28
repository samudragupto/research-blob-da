"""
test_research_integrity.py: Automated regression tests for research integrity guards.

Covers:
1. Dataset provenance completeness and origin validation.
2. Statistical and cost claim guards (no unjustified p < claims).
3. Evidence-type presence across all paper tables.
4. Literature review claim scope (preliminary survey vs systematic review).
5. Archival bridge local prototype labelling.
6. RQ4 endpoint probe qualification.
"""

import os

import pandas as pd

from python.check_journal_consistency import (
    check_archival_bridge_claims,
    check_blob_counts_consistency,
    check_dataset_provenance,
    check_literature_review_claims,
    check_rq4_retrieval_claims,
    check_statistical_and_cost_claims,
)


def test_blob_counts_consistency_guard():
    """Validates that check_blob_counts_consistency executes without error."""
    check_blob_counts_consistency()


def test_dataset_provenance_guard():
    """Validates that check_dataset_provenance enforces origin and checksum rules."""
    check_dataset_provenance()


def test_rq4_retrieval_claims_guard():
    """Validates that check_rq4_retrieval_claims enforces probe framing."""
    check_rq4_retrieval_claims()


def test_archival_bridge_claims_guard():
    """Validates that check_archival_bridge_claims enforces local prototype scoping."""
    check_archival_bridge_claims()


def test_statistical_and_cost_claims_guard():
    """Validates that check_statistical_and_cost_claims passes on paper sections."""
    check_statistical_and_cost_claims()


def test_literature_review_claims_guard():
    """Validates that check_literature_review_claims passes on surveyed literature."""
    check_literature_review_claims()


def test_paper_tables_evidence_type_presence():
    """Asserts every LaTeX table file in paper/tables/ contains an explicit evidence-type marker."""
    tables_dir = "paper/tables"
    assert os.path.exists(tables_dir), f"Missing tables directory: {tables_dir}"

    valid_markers = [
        "measured",
        "simulated",
        "analytical",
        "probe",
        "estimated",
        "tested",
        "prototype",
    ]

    for fname in os.listdir(tables_dir):
        if fname.endswith(".tex"):
            tpath = os.path.join(tables_dir, fname)
            with open(tpath, "r", encoding="utf-8") as f:
                content = f.read().lower()
            has_marker = any(m in content for m in valid_markers)
            assert (
                has_marker
            ), f"Table {fname} lacks required evidence-type marker (e.g. [Measured locally], [Simulated], etc.)"


def test_baseline_comparison_provenance_schema():
    """Asserts baseline_comparison.csv contains all required audit columns and valid evidence_types."""
    csv_path = "benchmarks/journal-extension/baseline_comparison.csv"
    assert os.path.exists(csv_path), f"Missing {csv_path}"

    df = pd.read_csv(csv_path)
    required_cols = [
        "retrieval_date_utc",
        "source",
        "region_or_network",
        "duration_assumed",
        "egress_included",
        "evidence_type",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column {col} in {csv_path}"

    valid_types = {
        "measured",
        "estimated_from_documented_pricing",
        "analytically_derived",
    }
    for ev in df["evidence_type"]:
        assert ev in valid_types, f"Invalid evidence_type '{ev}' in {csv_path}"
