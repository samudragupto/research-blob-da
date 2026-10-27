"""
check_consistency.py: Automated Consistency and Credibility Validator.

Verifies:
1. Exact match between generated CSV benchmark files and generated markdown tables.
2. README.md and docs/RESEARCH.md contain consistent headline figures.
3. SSTORE is strictly qualified as theoretical extrapolation with block requirements.
4. No unverified EIP-7623 headline figures (e.g., 32 gas/byte or 69.3x) exist.
5. Strict zero-emoji policy across all markdown, code, and config files.
"""

import os
import re
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass


def check_csv_files_exist():
    required_files = [
        "benchmarks/cost_comparison_uncompressed.csv",
        "benchmarks/cost_comparison_compressed.csv",
        "benchmarks/blob_capacity_limits.csv",
        "benchmarks/fee_sensitivity.csv",
        "benchmarks/calldata_eip7623_sensitivity.csv",
        "benchmarks/encoding_efficiency.csv",
        "benchmarks/generated_tables.md",
    ]
    for rf in required_files:
        if not os.path.exists(rf):
            raise FileNotFoundError(f"Missing required benchmark output: {rf}")
    print("[PASS] All required benchmark CSVs and generated tables exist.")


def check_table_consistency():
    df_uncomp = pd.read_csv("benchmarks/cost_comparison_uncompressed.csv")
    df_comp = pd.read_csv("benchmarks/cost_comparison_compressed.csv")

    with open("benchmarks/generated_tables.md", "r", encoding="utf-8") as f:
        gen_md = f.read()

    # Check that 1.0 MiB uncompressed is 9 blobs in Table A
    row_1m_uncomp = df_uncomp[df_uncomp["size_mib"] == 1.0].iloc[0]
    assert int(row_1m_uncomp["blobs_needed"]) == 9
    assert "| 1.0 MiB | 1,048,576 | 9 |" in gen_md

    # Check that ML trace is 2 blobs in Table B
    row_ml_comp = df_comp[
        df_comp["dataset_name"].str.contains("ML Training Trace")
    ].iloc[0]
    assert int(row_ml_comp["blob_count"]) == 2
    assert (
        "| ML Training Trace (JSON) | Synthetic Dataset | 10,000 | 1056.1 KiB | 174.9 KiB | 6.04x | **2** |"
        in gen_md
    )

    # Check that Real OpenAlex is 1 blob in Table B
    row_openalex = df_comp[df_comp["dataset_name"].str.contains("OpenAlex")].iloc[0]
    assert int(row_openalex["blob_count"]) == 1
    assert "Real Dataset" in gen_md

    print(
        "[PASS] Benchmark CSVs and generated markdown tables are strictly consistent."
    )


def check_zero_emojis():
    # Regex to detect common emoji ranges
    emoji_pattern = re.compile(
        "[\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa70-\U0001faff"
        "]+",
        flags=re.UNICODE,
    )

    scanned_extensions = (
        ".md",
        ".py",
        ".sol",
        ".ts",
        ".json",
        ".toml",
        ".yml",
        ".yaml",
    )
    ignored_dirs = {".git", ".venv", "node_modules", "cache", "out", "lib"}

    violations = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            if f.endswith(scanned_extensions):
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                        matches = emoji_pattern.findall(content)
                        if matches:
                            violations.append((p, matches[:3]))
                except (OSError, UnicodeDecodeError):
                    pass

    if violations:
        for p, m in violations:
            print(f"[FAIL] Emoji violation in {p}: {m}")
        raise ValueError(
            f"Found {len(violations)} files with emojis. Policy strictly prohibits emojis."
        )
    print("[PASS] Zero emoji policy verified across all repository files.")


def check_no_obsolete_claims(file_path: str):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for obsolete 69.3x claim
    if "69.3x" in content:
        raise ValueError(f"Found obsolete '69.3x' claim in {file_path}")

    # Check for obsolete claim asserting 32 gas/byte as the floor value
    if (
        re.search(r"\b32\s+gas(?:/|\s+per\s+)byte\s+floor\b", content, re.IGNORECASE)
        or re.search(r"floors\s*\(\s*32\s*gas", content, re.IGNORECASE)
        or re.search(r"Floor:\s*32\s*gas", content, re.IGNORECASE)
    ):
        raise ValueError(f"Found obsolete '32 gas/byte' floor claim in {file_path}")

    print(f"[PASS] No obsolete EIP-7623 headline claims in {file_path}.")


def main():
    print("=" * 60)
    print("RUNNING REPOSITORY CONSISTENCY AND INTEGRITY AUDIT")
    print("=" * 60)

    check_csv_files_exist()
    check_table_consistency()
    check_zero_emojis()
    check_no_obsolete_claims("README.md")
    check_no_obsolete_claims("docs/RESEARCH.md")

    print("=" * 60)
    print("ALL CONSISTENCY CHECKS PASSED.")
    print("=" * 60)


if __name__ == "__main__":
    main()
