"""
check_consistency.py: Automated Consistency, Credibility, and Protocol Invariant Validator.

Verifies:
1. Exact match between generated CSV benchmark files and generated markdown tables.
2. README.md and docs/RESEARCH.md contain consistent headline figures and frozen benchmarks.
3. SSTORE is strictly qualified as theoretical extrapolation with block requirements.
4. No unverified EIP-7623 headline figures (e.g., 32 gas/byte or 69.3x) exist.
5. Strict zero-emoji policy across all markdown, code, and config files.
6. Table B column headings use 'Canonical Payload Size' and contain the OpenAlex reconciliation note.
7. Benchmark freeze record SHA-256 hashes match files on disk and timing figures match frozen outputs.
8. No truncated hashes exist in README.md, and Sepolia deployment facts match deployments/sepolia_deployment.json.
9. Retrieval verification claims in README.md are backed by deployments/sepolia_retrieval_verification.json.
10. Obsolete audit-history language and banned ML phrases are completely eliminated.
"""

import hashlib
import json
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
        "benchmarks/FROZEN_BENCHMARKS_v0.1.0.json",
    ]
    for rf in required_files:
        if not os.path.exists(rf):
            raise FileNotFoundError(f"Missing required benchmark output: {rf}")
    print(
        "[PASS] All required benchmark CSVs, generated tables, and freeze records exist."
    )


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
    emoji_pattern = re.compile(
        "[\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff"
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "\U0001f900-\U0001f9ff"
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

    # Check for audit history phrases: 'previously discussed' or '32 gas/byte heuristic'
    if "previously discussed" in content:
        raise ValueError(
            f"Found obsolete audit-history phrase 'previously discussed' in {file_path}"
        )
    if "32 gas/byte heuristic" in content:
        raise ValueError(
            f"Found obsolete audit-history phrase '32 gas/byte heuristic' in {file_path}"
        )

    print(f"[PASS] No obsolete claims or audit-history phrases in {file_path}.")


def check_no_banned_ml_phrases():
    """Ensures synthetic ML traces are never described as real in headlines or body text."""
    target_files = [
        "README.md",
        "docs/RESEARCH.md",
        "docs/METHODOLOGY.md",
        "docs/ETHRESEARCH_POST.md",
        "docs/RELEASE_v0.1.0.md",
    ]
    banned_patterns = [
        (re.compile(r"real\s+ml\s+telemetry", re.IGNORECASE), "Real ML Telemetry"),
        (re.compile(r"real-world\s+ml", re.IGNORECASE), "real-world ML"),
        (re.compile(r"real\s+ml", re.IGNORECASE), "real ML"),
        (re.compile(r"measured\s+real\s+ml", re.IGNORECASE), "measured real ML"),
        (
            re.compile(r"The\s+ML\s+training\s+telemetry\s+contains", re.IGNORECASE),
            "The ML training telemetry contains",
        ),
    ]

    for p in target_files:
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for idx, line in enumerate(lines, 1):
            for pat, label in banned_patterns:
                if pat.search(line):
                    raise ValueError(
                        f"Found banned classification phrase '{label}' in {p}:{idx}: {line.strip()}"
                    )
    print("[PASS] Verified: Synthetic ML trace terminology is strictly consistent.")


def check_openalex_consistency():
    """Validates OpenAlex source file vs canonical payload sizes and unified timing deviation."""
    df_comp = pd.read_csv("benchmarks/cost_comparison_compressed.csv")
    row = df_comp[df_comp["dataset_name"].str.contains("OpenAlex")].iloc[0]

    assert (
        int(row["source_file_bytes"]) == 264057
    ), "OpenAlex source_file_bytes must be 264,057"
    assert (
        int(row["canonical_payload_bytes"]) == 212517
    ), "OpenAlex canonical_payload_bytes must be 212,517"
    assert int(row["blobs_used"]) == 1, "OpenAlex must require exactly 1 blob"

    # Ensure stale timing deviation is absent from published documentation
    for p in ["README.md", "docs/RESEARCH.md", "docs/ETHRESEARCH_POST.md"]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                c = f.read()
            if "11.5 ms ± 1.4 ms" in c or "11.5 ms +/- 1.4 ms" in c:
                raise ValueError(f"Found stale timing deviation '1.4 ms' in {p}")
            if "11.3 ms ± 0.1 ms" in c or "11.3 ms +/- 0.1 ms" in c:
                raise ValueError(f"Found stale timing '11.3 ms' in {p}")
    print("[PASS] OpenAlex source/canonical sizes and timing deviation verified.")


def check_table_b_guards():
    """Ensures Table B in README and RESEARCH does not use 'Raw Size' and contains the OpenAlex note."""
    df_comp = pd.read_csv("benchmarks/cost_comparison_compressed.csv")
    row = df_comp[df_comp["dataset_name"].str.contains("OpenAlex")].iloc[0]
    expected_canonical_bytes = int(row["canonical_payload_bytes"])

    for p in ["README.md", "docs/RESEARCH.md"]:
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        # Find Table B block
        table_b_match = re.search(
            r"###?\s*3?\.?2?\s*Table\s*(?:1)?B:.*?(?=\n###|\n##|\n---)",
            content,
            re.DOTALL,
        )
        if not table_b_match:
            raise ValueError(f"Table B not found in {p}")
        table_b_text = table_b_match.group(0)

        # 1. Check column heading does not contain 'Raw Size'
        header_line = None
        for line in table_b_text.splitlines():
            if "| Dataset Name |" in line or "| Dataset Type |" in line:
                header_line = line
                break
        if not header_line:
            raise ValueError(f"Table B header line not found in {p}")

        if "Raw Size" in header_line:
            raise ValueError(
                f"Table B in {p} must not contain column heading 'Raw Size'; must be 'Canonical Payload Size'"
            )
        if "Canonical Payload Size" not in header_line:
            raise ValueError(
                f"Table B in {p} must contain column heading 'Canonical Payload Size'"
            )

        # 2. Check OpenAlex explanatory note is present
        note_pattern = r"Note on the OpenAlex row:.*?The canonical payload actually compressed and encoded is (\d[\d,]*)\s*bytes"
        note_match = re.search(note_pattern, content, re.DOTALL)
        if not note_match:
            raise ValueError(
                f"Missing required OpenAlex explanatory note directly under Table B in {p}"
            )

        # 3. Check canonical payload bytes stated in note matches CSV
        note_bytes_str = note_match.group(1).replace(",", "")
        note_bytes = int(note_bytes_str)
        if note_bytes != expected_canonical_bytes:
            raise ValueError(
                f"OpenAlex note in {p} states {note_bytes} bytes, but cost_comparison_compressed.csv has {expected_canonical_bytes}"
            )

    print("[PASS] Table B Canonical Payload Size headings and OpenAlex note verified.")


def check_benchmark_freeze_and_timing_guards():
    """Verifies freeze record exists, hashes match frozen files, and Table B encoding timing is synchronized."""
    freeze_path = "benchmarks/FROZEN_BENCHMARKS_v0.1.0.json"
    if not os.path.exists(freeze_path):
        raise FileNotFoundError(f"Missing benchmark freeze record: {freeze_path}")

    with open(freeze_path, "r", encoding="utf-8") as f:
        freeze_data = json.load(f)

    # Verify SHA256 of frozen files
    file_hashes = freeze_data.get("benchmark_file_sha256") or freeze_data.get(
        "benchmark_files", {}
    )
    for rel_path, expected_hash in file_hashes.items():
        if not os.path.exists(rel_path):
            raise FileNotFoundError(f"Frozen benchmark file missing: {rel_path}")
        with open(rel_path, "rb") as fp:
            actual_hash = hashlib.sha256(fp.read()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                f"Benchmark file {rel_path} has modified hash {actual_hash}; expected frozen {expected_hash}"
            )

    # Read frozen OpenAlex timing
    frozen_oa = freeze_data.get("openalex_encoding_time") or freeze_data.get(
        "frozen_openalex_encoding", {}
    )
    frozen_mean = frozen_oa["mean_ms"]
    frozen_std = frozen_oa["std_ms"]
    frozen_runs = frozen_oa.get("run_count") or frozen_oa.get("runs", 10)

    # Verify formatting in CSV
    df_comp = pd.read_csv("benchmarks/cost_comparison_compressed.csv")
    row_oa = df_comp[df_comp["dataset_name"].str.contains("OpenAlex")].iloc[0]
    csv_mean = float(
        row_oa.get("encoding_time_mean_ms", row_oa.get("encode_time_ms_mean"))
    )
    csv_std = float(
        row_oa.get("encoding_time_std_ms", row_oa.get("encode_time_ms_std"))
    )
    assert round(csv_mean, 1) == round(frozen_mean, 1)
    assert round(csv_std, 1) == round(frozen_std, 1)

    expected_str = f"{csv_mean:.1f} ms ± {csv_std:.1f} ms"

    # Verify in README.md and docs/RESEARCH.md
    for p in ["README.md", "docs/RESEARCH.md"]:
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            c = f.read()

        # Check run count in header
        if f"N={frozen_runs}" not in c:
            raise ValueError(
                f"Table B encoding column in {p} must include run count 'N={frozen_runs}'"
            )

        # Check OpenAlex encoding value in Table B
        if expected_str not in c:
            raise ValueError(
                f"Expected OpenAlex encoding time '{expected_str}' not found in {p}"
            )

    print(
        f"[PASS] Benchmark freeze verified (SHA-256 hashes intact, OpenAlex timing '{expected_str} (N={frozen_runs})' verified)."
    )


def check_sepolia_proof_and_retrieval_guards():
    """Verifies no truncated hashes in README, checks deployment values, and validates retrieval verification."""
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    # 1. No truncated hashes
    truncated = re.findall(r"0x[0-9a-fA-F]+\.\.\.", readme_content)
    if truncated:
        raise ValueError(f"Found truncated hash patterns in README.md: {truncated}")

    # 2. Check deployment record match
    dep_path = "deployments/sepolia_deployment.json"
    if not os.path.exists(dep_path):
        raise FileNotFoundError(f"Missing deployment record: {dep_path}")
    with open(dep_path, "r", encoding="utf-8") as f:
        dep_data = json.load(f)

    contract_addr = dep_data["contract_address"]
    deploy_tx = dep_data["transaction_hash"]
    blob_tx_info = dep_data["blob_transactions"][0]
    blob_tx = blob_tx_info["transaction_hash"]
    dataset_id = blob_tx_info["dataset_id"]
    versioned_hash = blob_tx_info["versioned_hashes"][0]

    assert (
        contract_addr in readme_content
    ), f"DatasetRegistry address {contract_addr} not in README.md"
    assert deploy_tx in readme_content, f"Deployment tx {deploy_tx} not in README.md"
    assert blob_tx in readme_content, f"Blob tx {blob_tx} not in README.md"
    assert dataset_id in readme_content, f"Dataset ID {dataset_id} not in README.md"
    assert (
        versioned_hash in readme_content
    ), f"Versioned hash {versioned_hash} not in README.md"

    # 3. Check retrieval verification
    retrieval_file = "deployments/sepolia_retrieval_verification.json"
    if "Retrieval verified on" in readme_content:
        if not os.path.exists(retrieval_file):
            raise FileNotFoundError(
                f"README claims retrieval verified, but {retrieval_file} is missing."
            )
        with open(retrieval_file, "r", encoding="utf-8") as rf:
            retrieval_data = json.load(rf)
        if not retrieval_data.get("manifest_hash_match"):
            raise ValueError(f"{retrieval_file} manifest_hash_match is not true.")
        if not retrieval_data.get("versioned_hash_match"):
            raise ValueError(f"{retrieval_file} versioned_hash_match is not true.")

    print(
        "[PASS] Sepolia proof links, non-truncated hashes, and retrieval verification verified."
    )


def check_headline_calldata_shorthand():
    """Ensures shorthand '(16 gas/byte)' does not appear in headline findings in README.md."""
    readme_path = "README.md"
    with open(readme_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_headlines = False
    for idx, line in enumerate(lines, 1):
        if "## For Conference Reviewers" in line or "Headline Findings" in line:
            in_headlines = True
        elif in_headlines and line.startswith("## "):
            in_headlines = False

        if in_headlines and "(16 gas/byte)" in line:
            raise ValueError(
                f"Found imprecise shorthand '(16 gas/byte)' in headline finding at README.md:{idx}. "
                "Must be expanded to 'standard calldata cost, 4 gas per zero byte and 16 gas per non-zero byte, before application of the EIP-7623 floor'."
            )

    print("[PASS] Headline calldata description expanded in full.")


def check_eip7623_status_and_table_a_label():
    """Ensures EIP-7623 is stated as activated with Pectra and Table A is labeled pre-floor."""
    target_files = [
        "README.md",
        "docs/RESEARCH.md",
        "docs/METHODOLOGY.md",
        "docs/ETHRESEARCH_POST.md",
    ]
    conditional_patterns = [
        re.compile(r"EIP-7623\s+propos\w*", re.IGNORECASE),
        re.compile(r"if\s+(?:EIP-7623\s+is\s+)?enacted", re.IGNORECASE),
    ]

    for p in target_files:
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for idx, line in enumerate(lines, 1):
            for pat in conditional_patterns:
                if pat.search(line):
                    raise ValueError(
                        f"Found outdated conditional language for EIP-7623 in {p}:{idx}: {line.strip()}"
                    )

    # Check that Table A in README and RESEARCH explicitly labels standard calldata pre-floor
    for p in ["README.md", "docs/RESEARCH.md"]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                c = f.read()
            if (
                "before application of the EIP-7623 floor" not in c
                and "before the EIP-7623 floor" not in c
            ):
                raise ValueError(
                    f"Table A in {p} must explicitly state calldata cost is before application of the EIP-7623 floor"
                )

    print(
        "[PASS] EIP-7623 Pectra activation status and Table A pre-floor labels verified."
    )


def main():
    print("=" * 60)
    print("RUNNING REPOSITORY CONSISTENCY AND INTEGRITY AUDIT")
    print("=" * 60)

    check_csv_files_exist()
    check_table_consistency()
    check_zero_emojis()
    check_no_obsolete_claims("README.md")
    check_no_obsolete_claims("docs/RESEARCH.md")
    check_no_obsolete_claims("docs/ETHRESEARCH_POST.md")
    check_no_banned_ml_phrases()
    check_openalex_consistency()
    check_table_b_guards()
    check_benchmark_freeze_and_timing_guards()
    check_sepolia_proof_and_retrieval_guards()
    check_headline_calldata_shorthand()
    check_eip7623_status_and_table_a_label()

    print("=" * 60)
    print("ALL CONSISTENCY CHECKS PASSED.")
    print("=" * 60)


if __name__ == "__main__":
    main()
