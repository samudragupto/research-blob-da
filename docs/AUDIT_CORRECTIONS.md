# Audit and Hardening Report: research-blob-da

**Target:** v0.1.0 Release and ETHConf Research Talk Submission  
**Author:** Arrhat Nag (GitHub: samudragupto)  
**Date:** October 2026  
**Status:** Audit Complete, Benchmarks Regenerated, Full Test Suite Passing  

---

## 1. Summary of Corrections by Issue

### Issue 1: Blob-Count and Cost Table Reconciliation
- **Audit Findings:** Audited `python/encoder.py`. Under conservative 31-byte field element packing (`FE31`), each 32-byte field element holds 31 bytes with the top byte set to `0x00` (guaranteeing element $< 2^{248} <$ BLS12-381 modulus $r$). Field Element 0 stores a 31-byte domain header (`RBDA` magic, version, codec, layout, indices, and content hash tag). Thus, usable body payload capacity is strictly $(4,096 \times 31) - 31 = \mathbf{126,945\text{ bytes}}$.
- **Action Taken:**
  - Disaggregated all cost reporting into **Table A: Theoretical Uncompressed Cost Baseline** and **Table B: Measured Compressed Dataset Results**.
  - Documented the exact mathematical derivation of blob counts: $\lceil 1,048,576 / 126,945 \rceil = 9\text{ blobs}$ for 1.0 MiB uncompressed raw data, versus $\lceil 179,112 / 126,945 \rceil = 2\text{ blobs}$ for the 1,056 KiB ML training trace compressed 6.04x via Zstandard level 3.
  - Regenerated all benchmark CSVs and figures.
  - Implemented `python/check_consistency.py` to assert mathematical consistency across documentation and generated data.
- **Files Changed:** `python/experiments.py`, `python/plot_results.py`, `python/check_consistency.py`, `benchmarks/generated_tables.md`, `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.

### Issue 2: Verification and Refinement of EIP-7623
- **Audit Findings:** Evaluated official EIP-7623 specification by Toni Wahrstätter and Vitalik Buterin. The specification defines:
  $\text{Tokens} = (\text{Zero Bytes} \times 1) + (\text{Non-Zero Bytes} \times 4)$,
  $\text{Standard Calldata Gas} = 4 \times \text{Tokens}$,
  $\text{Floor Gas} = 21{,}000 + 10 \times \text{Tokens}$,
  $\text{tx.gasUsed} = 21{,}000 + \max(\text{Standard Calldata Gas} + \text{Execution Gas}, 10 \times \text{Tokens})$.
  For data-availability transactions (where non-zero bytes exceed 99.6%), the effective floor is $\approx 39.88\text{ gas/byte}$, not a universal constant of 32 gas/byte.
- **Action Taken:**
  - Implemented exact formula in `python/cost_model.py:calculate_eip7623_calldata_gas`.
  - Added unit test vectors in `tests/test_cost_model.py` (all-zeros, all-nonzeros, compute-heavy, and real JSON).
  - Removed obsolete 69.3x and 32 gas/byte figures from Abstract, Executive Summary, and Table 1.
  - Created a dedicated subsection: "Post-Pectra Calldata Floor Sensitivity (EIP-7623)" in `README.md` and `docs/RESEARCH.md`, and generated `benchmarks/calldata_eip7623_sensitivity.csv`. Corrected the author citation to Toni Wahrstätter and Vitalik Buterin.
- **Files Changed:** `python/cost_model.py`, `tests/test_cost_model.py`, `python/experiments.py`, `benchmarks/calldata_eip7623_sensitivity.csv`, `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.

### Issue 3: Presentation of SSTORE as Theoretical Extrapolation
- **Audit Findings:** Contract storage allocates 32-byte slots. In EVM state, uninitialized slot writes (`SSTORE` 0 to non-zero) cost 20,000 gas, plus 2,100 gas for cold account/slot access ($22,100\text{ gas/slot} \approx 690.6\text{ gas/byte}$). At the 30M block gas limit, publishing 1.0 MiB in SSTORE requires at least 25 saturated Ethereum blocks.
- **Action Taken:**
  - Relabeled all contract storage metrics across tables, charts, and text as "Theoretical SSTORE Extrapolation (Not Executable in a Single Block)".
  - Added explicit block requirement columns ($25\text{ blocks}$ for 1.0 MiB, $483\text{ blocks}$ for 20.0 MiB).
  - Added prominent caution notes clarifying that SSTORE provides permanent consensus state, whereas blobs provide ephemeral 18.2-day data availability, making SSTORE a theoretical cost baseline rather than a practical upload substitute.
- **Files Changed:** `python/cost_model.py`, `python/experiments.py`, `python/plot_results.py`, `benchmarks/cost_comparison_uncompressed.csv`, `benchmarks/generated_tables.md`, `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.

### Issue 4: Blob Capacity, Transaction Limits, and Inclusion Times
- **Audit Findings:** Prior presentations quoted large datasets (e.g., 20 MiB requiring 166 blobs) without addressing consensus limits (current Cancun limit: target 3, max 6 blobs per block/tx).
- **Action Taken:**
  - Implemented `calculate_capacity_and_inclusion` in `python/cost_model.py`.
  - Modeled three protocol eras: Cancun (EIP-4844), Pectra (EIP-7691: target 6, max 9), and PeerDAS (EIP-7594: 32 target, 64 max).
  - Calculated minimum transactions, burst blocks, and inclusion times at 12-second slots for 128 KiB, 1 MiB, 5 MiB, and 20 MiB.
  - Generated `benchmarks/blob_capacity_limits.csv` and Table C in documentation.
  - Documented multi-transaction assembly in `DatasetRegistry.sol` (`openDataset`, `appendBlobs`, `finalize`) and partial submission handling.
- **Files Changed:** `python/cost_model.py`, `tests/test_cost_model.py`, `python/experiments.py`, `benchmarks/blob_capacity_limits.csv`, `benchmarks/generated_tables.md`, `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.

### Issue 5: Fee Sensitivity and Break-Even Analysis
- **Audit Findings:** Previous cost comparisons assumed a single static fee scenario (15 gwei base fee, 2 gwei blob fee).
- **Action Taken:**
  - Implemented formal fee sensitivity grid across execution base fees (5 to 100 gwei) and blob base fees (1 to 200 gwei).
  - Mathematically derived break-even blob fee formula: $P_{\text{blob}}^{\text{break-even}} = \frac{21,000 + 16 \times S - \text{Gas}_{\text{exec}}}{K \times 131,072} \times P_{\text{base}}$. For 1.0 MiB, break-even is $13.86 \times P_{\text{base}} = 207.9\text{ gwei}$ at 15 gwei base fee.
  - Generated `benchmarks/fee_sensitivity.csv` and created publication figure `figure6_fee_sensitivity.{png,pdf}`.
  - Added unit tests for break-even calculations in `tests/test_cost_model.py`.
- **Files Changed:** `python/cost_model.py`, `tests/test_cost_model.py`, `python/experiments.py`, `python/plot_results.py`, `benchmarks/fee_sensitivity.csv`, `benchmarks/figure6_fee_sensitivity.{png,pdf}`, `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.

### Issue 6: Addition of Real Public Dataset (OpenAlex)
- **Audit Findings:** All previous benchmark datasets were synthetic.
- **Action Taken:**
  - Implemented `python/fetch_real_data.py` to retrieve 500 real academic works from the OpenAlex REST API under CC0 terms.
  - Saved committed fixture in `data/real_academic_openalex.json` (264,057 bytes raw) and manifest `data/real_academic_openalex_manifest.json` (SHA-256: `af65584227c707d3c16f7841a233070808ab1ed070f10f32e841082889a8c544`).
  - Executed full pipeline: 4.13x Zstandard compression (50.3 KiB), 1 blob ($8.35), 11.5 ms encoding time.
  - Integrated real dataset into Table B and Table 2.
  - Created unit tests in `tests/test_real_data.py` for parser, schema, manifest verification, and end-to-end decoding.
- **Files Changed:** `python/fetch_real_data.py`, `data/real_academic_openalex.json`, `data/real_academic_openalex_manifest.json`, `tests/test_real_data.py`, `python/experiments.py`, `python/plot_results.py`, `benchmarks/cost_comparison_compressed.csv`, `benchmarks/encoding_efficiency.csv`, `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.

### Issue 7: Testnet Path and Sepolia Readiness
- **Audit Findings:** The TypeScript broadcast script `frontend-or-cli/ts/src/blob_tx.ts` had an ABI mismatch with `DatasetRegistry.sol`.
- **Action Taken:**
  - Corrected ABI and argument serialization in `blob_tx.ts` to match `DatasetRegistry.sol` (`openDataset(bytes32 salt, DatasetParams calldata params, uint256 numTxBlobs, bool finalize_)`).
  - Created `.env.example` with documented environment parameters.
  - Created `deployments/sepolia_deployment.example.json` schema.
  - Created `docs/SEPOLIA_DEPLOYMENT.md` with step-by-step commands for deployment, blob submission, and immediate beacon sidecar retrieval before the 4096-epoch pruning horizon.
  - Declared deployment status honestly: `Local simulation complete. Sepolia deployment script ready. Deployment pending a funded Sepolia account.`
- **Files Changed:** `frontend-or-cli/ts/src/blob_tx.ts`, `.env.example`, `deployments/sepolia_deployment.example.json`, `docs/SEPOLIA_DEPLOYMENT.md`, `README.md`.

### Issue 8: Humanisation, Release Discipline, and Conference Assets
- **Action Taken:**
  - Authored `docs/ENGINEERING_LESSONS.md` with six concrete first-person implementation takeaways.
  - Created `CHANGELOG.md` following Keep a Changelog standard for v0.1.0.
  - Created `docs/RELEASE_v0.1.0.md` with release notes and reviewer quickstart.
  - Created `docs/GITHUB_METADATA.md` with description, topics, and `gh` CLI commands.
  - Created `docs/DEMO_VIDEO_SCRIPT.md` with a 2-minute timestamped walkthrough including tamper detection and fraud refutation.
  - Created `docs/ETHRESEARCH_POST.md` research discussion draft.
  - Added "For Conference Reviewers" section in `README.md`.
  - Created valid `CITATION.cff` for Arrhat Nag.
  - Enforced strict zero-emoji policy across all repository files via `python/check_consistency.py`.
- **Files Changed:** `docs/ENGINEERING_LESSONS.md`, `CHANGELOG.md`, `docs/RELEASE_v0.1.0.md`, `docs/GITHUB_METADATA.md`, `docs/DEMO_VIDEO_SCRIPT.md`, `docs/ETHRESEARCH_POST.md`, `CITATION.cff`, `README.md`.

---

## 2. Complete List of Files Created or Modified

### Files Created
- `python/cost_model.py`
- `python/fetch_real_data.py`
- `python/check_consistency.py`
- `tests/test_cost_model.py`
- `tests/test_real_data.py`
- `data/real_academic_openalex.json`
- `data/real_academic_openalex_manifest.json`
- `benchmarks/cost_comparison_uncompressed.csv`
- `benchmarks/cost_comparison_compressed.csv`
- `benchmarks/blob_capacity_limits.csv`
- `benchmarks/fee_sensitivity.csv`
- `benchmarks/calldata_eip7623_sensitivity.csv`
- `benchmarks/generated_tables.md`
- `benchmarks/figure6_fee_sensitivity.png`
- `benchmarks/figure6_fee_sensitivity.pdf`
- `.env.example`
- `deployments/sepolia_deployment.example.json`
- `docs/SEPOLIA_DEPLOYMENT.md`
- `docs/ENGINEERING_LESSONS.md`
- `CHANGELOG.md`
- `docs/RELEASE_v0.1.0.md`
- `docs/GITHUB_METADATA.md`
- `docs/DEMO_VIDEO_SCRIPT.md`
- `docs/ETHRESEARCH_POST.md`
- `CITATION.cff`
- `docs/AUDIT_CORRECTIONS.md`

### Files Modified
- `python/experiments.py`
- `python/plot_results.py`
- `frontend-or-cli/rbda_cli.py`
- `frontend-or-cli/ts/src/blob_tx.ts`
- `README.md`
- `docs/RESEARCH.md`
- `docs/METHODOLOGY.md`
- `benchmarks/cost_comparison.csv`
- `benchmarks/encoding_efficiency.csv`
- `benchmarks/figure1_cost_comparison.png` / `.pdf`
- `benchmarks/figure2_compression_efficiency.png` / `.pdf`

---

## 3. Benchmarks Regenerated

The entire benchmark suite was regenerated from committed code using:
```bash
python python/experiments.py
python python/plot_results.py
```

Generated outputs:
1. `benchmarks/cost_comparison_uncompressed.csv` (Table A)
2. `benchmarks/cost_comparison_compressed.csv` (Table B)
3. `benchmarks/blob_capacity_limits.csv` (Table C)
4. `benchmarks/fee_sensitivity.csv` (Table D)
5. `benchmarks/calldata_eip7623_sensitivity.csv` (EIP-7623 Sensitivity)
6. `benchmarks/encoding_efficiency.csv` (Updated with OpenAlex real data)
7. `benchmarks/generated_tables.md` (Markdown tables for direct document syncing)
8. Figures 1 through 6 in PNG (300 DPI) and vector PDF formats.

---

## 4. Test Results

### 4.1 Python Unit and Property Tests (`pytest -v tests`)
Command: `.venv\Scripts\pytest -v tests`
Result: **40 passed in 0.51s (100% pass rate)**.
- `test_canonical.py`: 5 passed
- `test_commitments.py`: 5 passed
- `test_cost_model.py`: 10 passed (modulus, blob formulas, EIP-7623 vectors, SSTORE, capacity, break-even)
- `test_encoder_decoder.py`: 9 passed
- `test_real_data.py`: 4 passed (manifest checksum, record parser, pipeline end-to-end)
- `test_retriever.py`: 7 passed

### 4.2 Foundry Smart Contract Tests (`forge test`)
Command: `forge test`
Result: **31 passed in 1.82s (100% pass rate)**.
- `test/DatasetRegistry.t.sol`: 12 passed
- `test/MerkleLib.t.sol`: 8 passed
- `test/JsonFieldLib.t.sol`: 5 passed
- `test/Baselines.t.sol`: 4 passed
- `test/Invariants.t.sol`: 2 passed (invariant fuzzing over 16,384 calls across 256 runs)

### 4.3 Consistency and Zero-Emoji Check (`python python/check_consistency.py`)
Command: `.venv\Scripts\python.exe python/check_consistency.py`
Result: **All consistency checks passed**.
- Validated CSV rows against markdown tables.
- Confirmed zero emojis across all repository files.
- Confirmed absence of obsolete 69.3x / 32 gas/byte claims.

---

## 5. Corrected Headline Numbers

The following figures are verified, derived from runnable code, and safe to copy directly into ETHConf speaker submissions:

1. **27.8x Theoretical Cost Reduction vs. Standard Calldata:**
   - Payload: 1.0 MiB uncompressed raw data ($1,048,576\text{ bytes}$).
   - Blobs Required: $\lceil 1,048,576 / 126,945 \rceil = \mathbf{9\text{ blobs}}$.
   - Blob Posting Cost: **$27.24 USD** ($0.009079\text{ ETH}$ across blob gas and execution gas).
   - Standard Calldata Cost: **$755.92 USD** ($0.25197\text{ ETH}$ at 16 gas/byte).
   - Assumptions: Execution base fee = 15 gwei, blob base fee = 2 gwei, ETH = $3,000 USD.

2. **12.1x Measured Compressed Posting Cost on Real ML Telemetry:**
   - Dataset: ML Training Trace (10,000 steps, $1,056.1\text{ KiB}$ raw).
   - Zstandard Level 3 Compressed Size: $174.9\text{ KiB}$ ($179,112\text{ bytes}$, $6.04\text{x}$ compression ratio).
   - Blobs Required: $\lceil 179,112 / 126,945 \rceil = \mathbf{2\text{ blobs}}$.
   - Blob Posting Cost: **$10.71 USD** ($0.003569\text{ ETH}$).
   - Calldata Cost for Compressed Payload: **$129.91 USD** ($0.04330\text{ ETH}$).

3. **Break-Even Blob Base Fee:**
   - At standard 15 gwei execution base fee, the break-even blob base fee where blob posting cost equals calldata cost for 1.0 MiB is **207.9 gwei** ($13.86 \times P_{\text{base}}$). Below 208 gwei, blobs provide a strict cost advantage.

4. **SSTORE Practical Impracticality:**
   - 1.0 MiB requires $32,768\text{ storage slots} \times 22,100\text{ gas} + 21,000 = 724,193,800\text{ gas}$.
   - Theoretical Cost: **$32,588.72 USD**.
   - Minimum Ethereum Blocks at 30M Gas Limit: **25 full blocks**, establishing that SSTORE is purely a theoretical reference point.

---

## 6. Sepolia Status

- **Current Status:** Local simulation complete. Sepolia deployment script ready. Deployment pending a funded Sepolia account.
- **Verification Guarantee:** No simulated or placeholder transaction hashes have been added to README.md. Complete, tested deployment scripts (`script/Deploy.s.sol`, `script/PostBlobDataset.s.sol`, `frontend-or-cli/ts/src/blob_tx.ts`) and operational instructions are provided in `docs/SEPOLIA_DEPLOYMENT.md`.

---

## 7. Manual Steps Remaining for the Author

Only the following steps require manual action by Arrhat Nag:
1. **Fund Sepolia Account:** Obtain Sepolia testnet ETH from a public faucet (recommended: 0.1 Sepolia ETH).
2. **Execute Sepolia Deployment (When Funded):** Follow `docs/SEPOLIA_DEPLOYMENT.md` to deploy `DatasetRegistry`, post one blob transaction, populate `deployments/sepolia_deployment.json`, and add verified explorer links to README.md.
3. **Apply GitHub Repository Metadata:** Run the `gh repo edit` command documented in `docs/GITHUB_METADATA.md` to set the repository description and topics.
4. **Create GitHub Tag and Release v0.1.0:** Run the `git tag` and `gh release create` commands documented in `docs/RELEASE_v0.1.0.md`.
5. **Record Two-Minute Demonstration Video:** Follow the timestamped terminal commands and narration in `docs/DEMO_VIDEO_SCRIPT.md`.
6. **Publish ethresear.ch Research Post:** Post the text in `docs/ETHRESEARCH_POST.md` to [ethresear.ch](https://ethresear.ch).

---

## 8. Application Readiness Statement

The corrected repository is **fully defensible, mathematically consistent, and ready for ETHConf speaker application submission**.

- **Safe to Use:** The author may copy the corrected findings: **27.8x cost reduction on 1.0 MiB uncompressed raw data**, **12.1x measured reduction on ML telemetry (175 KiB in 2 blobs)**, **73.2% gas savings on batch range proofs**, and the **207.9 gwei break-even blob fee operating envelope**.
- **Claims to Avoid:** The author must **not** claim a universal "69.3x" savings figure or a universal "32 gas per byte" calldata floor, must **not** cite SSTORE as a practical posting method, and must **not** state that blobs provide permanent storage beyond the 4,096-epoch consensus pruning horizon.

---

## 9. Reviewer Text Corrections (Pre-Release Integrity Audit)

### 9.1 Repository-Wide Search Results
A comprehensive audit scan was conducted across all repository files for banned or conflicting terms:

1. **Real ML Telemetry / real ML / real-world ML:**
   - `README.md:21`: `2. **12.1x Measured Compressed Posting Cost on Real ML Telemetry:** A 1,056 KiB neural network training trace compresses...` (Headline incorrectly called synthetic ML trace "Real ML Telemetry").
   - `docs/RESEARCH.md:14`: `...and a 12.1x measured reduction on real-world ML telemetry...` (Abstract sentence incorrectly called synthetic ML trace "real-world ML telemetry").
   - `docs/AUDIT_CORRECTIONS.md:203`: Previous draft section 5 headline reference.

2. **EIP-7623 Conditional Language (proposes / proposed / if enacted / will increase):**
   - `README.md:169`: `EIP-7623 proposes an execution-layer calldata floor...`
   - `README.md:180`: `If enacted, post-Pectra calldata costs for pure DA will increase by 2.5x...`
   - `docs/RESEARCH.md:423`: `EIP-7623 proposes an execution-layer calldata floor...`
   - `docs/RESEARCH.md:439`: `If enacted in Pectra, EIP-7623 will increase calldata posting costs...`

3. **OpenAlex Size Discrepancy (207.5 KiB vs. 257.9 KiB / 264,057 bytes):**
   - `README.md:114`: Table B listed `207.5 KiB` without explaining that this is canonical payload bytes, whereas `data/real_academic_openalex.json` is `264,057 bytes` (`257.9 KiB`).
   - `docs/RESEARCH.md:303, 325`: Table 2 and Table 4 listed `207.5 KiB`.
   - `docs/METHODOLOGY.md:60`: Listed raw byte size `264,057 bytes`.
   - `docs/ETHRESEARCH_POST.md:40`: Listed `$207.5\text{ KiB}$ raw`.

4. **OpenAlex Encoding Timing Deviation (11.5 ms ± 0.1 ms vs. ± 1.4 ms):**
   - `README.md:114`, `docs/RESEARCH.md:303`, `benchmarks/generated_tables.md:28`: Listed `11.5 ms ± 0.1 ms`.
   - `docs/AUDIT_CORRECTIONS.md:70, 222`: Previous draft narrative referenced `11.5 ms ± 1.4 ms` from a prior timing run.
   - Root Cause: Independent timing loops in `run_cost_comparison_compressed` and `run_encoding_efficiency` generated differing standard deviations across separate executions.

---

### 9.2 Fix 1: Correct Synthetic ML Training Trace Classification

- **Incorrect Text:** "12.1x Measured Compressed Posting Cost on Real ML Telemetry" (in headlines) and "real-world ML telemetry" (in abstracts and summaries).
- **Locations Found:** `README.md`, `docs/RESEARCH.md`, and previous draft notes in `docs/AUDIT_CORRECTIONS.md`.
- **Root Cause:** A draft headline conflated synthetic ML training trace evaluation with real data telemetry, directly contradicting Table B where ML Training Trace is properly classified as a Synthetic Dataset.
- **Corrected Text:**
  - Headline: `12.1x Measured Compressed Cost on an ML Training Trace`
  - Body Description: `A synthetic ML training trace of 1,056.1 KiB compresses 6.04x to 174.9 KiB and requires 2 blobs, giving a measured 12.1x cost reduction against posting the compressed payload as standard calldata under the stated fee assumptions ($10.71 vs. $129.91).`
- **Files Changed:** `README.md`, `docs/RESEARCH.md`, `docs/ETHRESEARCH_POST.md`, `benchmarks/generated_tables.md`, `docs/AUDIT_CORRECTIONS.md`.
- **Automated Guard Added:** In `python/check_consistency.py`, `check_no_banned_ml_phrases()` scans `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`, `docs/ETHRESEARCH_POST.md`, and `docs/RELEASE_v0.1.0.md` to ensure banned phrases (e.g., "Real ML Telemetry", "real-world ML") are strictly forbidden. The legitimate label "Real Dataset" is permitted only when specifically referencing OpenAlex Academic Works.

---

### 9.3 Fix 2: Reconcile OpenAlex Source Size, Canonical Payload Size, and Encoding Deviation

- **Incorrect Text / Discrepancy:**
  - Table B reported OpenAlex raw size as `207.5 KiB` while the audit narrative and filesystem reported `264,057 bytes` (`257.9 KiB`).
  - Encoding deviation was reported as `11.5 ms ± 0.1 ms` in Table B and `11.5 ms ± 1.4 ms` in early audit notes.
- **Root Cause:**
  - *Size Difference:* The committed source file on disk (`data/real_academic_openalex.json`) is 264,057 bytes. The pipeline parses the JSON, extracts the documented record fields, and serializes them into an RFC 8785 canonical stream with length-prefixed framing. This canonical stream is 212,517 bytes (207.5 KiB). Compression, blob packing, and calldata posting operate on the canonical payload, not the unparsed file with formatting whitespace.
  - *Timing Deviation Difference:* The earlier 1.4 ms figure was an unconstrained preliminary test run. Furthermore, `experiments.py` previously executed two independent benchmark loops with separate timer arrays.
- **Corrected Text & Values:**
  - Defined five exact quantities in documentation, code, and manifest:
    1. `source_file_bytes`: 264,057 bytes (257.9 KiB)
    2. `canonical_payload_bytes`: 212,517 bytes (207.5 KiB)
    3. `compressed_bytes`: 51,479 bytes (50.3 KiB)
    4. `encoded_bytes`: 131,072 bytes (1 blob)
    5. `blobs_used`: 1
  - Timing unified across all outputs via centralized `get_or_benchmark_datasets(trials=10)`: `11.3 ms ± 0.1 ms` ($N=10$).
  - Added explanatory note to Table B clarifying that Table B reflects canonical payload bytes, while the committed source file is 264,057 bytes.
- **Files Changed:** `data/real_academic_openalex_manifest.json`, `python/fetch_real_data.py`, `python/experiments.py`, `tests/test_real_data.py`, `benchmarks/cost_comparison_compressed.csv`, `benchmarks/encoding_efficiency.csv`, `benchmarks/generated_tables.md`, `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`, `docs/ETHRESEARCH_POST.md`.
- **Automated Guard Added:** In `python/check_consistency.py`, `check_openalex_consistency()` verifies that manifest values match the file on disk and match the CSV outputs. `tests/test_real_data.py` asserts `test_real_data_source_vs_canonical_reconciliation()`.

---

### 9.4 Fix 3: State EIP-7623 Pectra Activation and Label Table A Calldata Basis

- **Incorrect Text:** EIP-7623 was described with conditional language ("proposes", "if enacted"), and Table A did not explicitly state that its calldata cost is the standard calculation before application of the EIP-7623 floor.
- **Root Cause:** EIP-7623 drafts were written prior to final inclusion and activation schedules for Pectra. Furthermore, Table A omitted a clear calldata basis disclaimer, leaving ambiguity over whether the 27.8x figure included the floor.
- **Corrected Text:**
  - Status: "EIP-7623, activated with Pectra, defines an execution-layer calldata floor that raises the effective gas cost of data-heavy transactions whose execution gas is small relative to their calldata size."
  - Table A Label: "Table A: Theoretical Uncompressed Cost Baseline. Calldata cost is the standard calldata calculation (16 gas per non-zero byte and 4 gas per zero byte plus intrinsic and stated execution gas), before application of the EIP-7623 floor. This makes the reported blob savings factor conservative for data-heavy transactions under current post-Pectra rules, because the EIP-7623 floor can raise the effective calldata cost. See Section 6 (Post-Pectra Calldata Floor Sensitivity) for the floor-adjusted analysis."
  - Repetition: In headlines and summaries, Table A figures carry the explicit qualifier "before application of the EIP-7623 floor".
- **Files Changed:** `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`, `docs/ETHRESEARCH_POST.md`, `benchmarks/generated_tables.md`, `tests/test_cost_model.py`.
- **Automated Guard Added:** In `python/check_consistency.py`, `check_eip7623_status_and_table_a_label()` enforces that no conditional language ("proposes", "if enacted") appears in EIP-7623 contexts, and that Table A explicitly includes the pre-floor disclaimer.

---

## 10. Final Reviewer Corrections Before v0.1.0

**Date:** October 2026  
**Status:** Completed and Frozen for v0.1.0 Tagging and ETHConf Review

### 10.1 Fix 1: Correct the OpenAlex Row and Table B Column Heading

- **Previous Text / Discrepancy:** Table B labeled 207.5 KiB as `Raw Size` for OpenAlex Academic Works. A reviewer examining the committed source file on disk (`data/real_academic_openalex.json`) observes 264,057 bytes (257.9 KiB). Table B lacked an immediate reconciliation note directly under the table.
- **Where It Appeared:** `README.md` Table B, `docs/RESEARCH.md` Table 1B, `benchmarks/generated_tables.md`, `python/experiments.py`.
- **Root Cause:** The pipeline parses the committed OpenAlex source file (264,057 bytes), extracts documented schema fields, and deterministically normalizes records into an RFC 8785 canonical stream before compression. The canonical payload actually compressed and encoded is 212,517 bytes (207.5 KiB). Table B was populated from canonical payload bytes for all datasets, but the column was imprecisely labeled "Raw Size".
- **Corrected Text & Values:**
  - Column heading renamed from `Raw Size` to `Canonical Payload Size` across `README.md`, `docs/RESEARCH.md`, `benchmarks/generated_tables.md`, and `python/experiments.py`.
  - Added note immediately below Table B in `README.md` and `docs/RESEARCH.md`:
    > **Note on the OpenAlex row:** The committed source file is 264,057 bytes (257.9 KiB). The pipeline parses it, extracts the documented record fields, and deterministically canonicalizes the records before compression. The canonical payload actually compressed and encoded is 212,517 bytes (207.5 KiB). Compression ratio, blob count, and cost are therefore calculated from canonical payload bytes.
  - Updated Section 3.3 / Section 4.1 explanatory notes to reference canonical payload bytes.
- **Files Changed:** `README.md`, `docs/RESEARCH.md`, `benchmarks/generated_tables.md`, `python/experiments.py`, `python/plot_results.py`.
- **Automated Guard Added:** `check_table_b_guards()` in `python/check_consistency.py` verifies that Table B does not contain `Raw Size`, verifies that `Canonical Payload Size` is present, asserts presence of the OpenAlex explanatory note directly under the table, and checks that the canonical byte count in the note matches `benchmarks/cost_comparison_compressed.csv`.

---

### 10.2 Fix 2: Freeze One Benchmark Generation and Synchronise Encoding Times

- **Previous Text / Discrepancy:** Encoding times drifted between benchmark runs (e.g., 11.3 ms ± 0.1 ms in one benchmark generation versus 11.5 ms ± 0.1 ms in earlier README versions).
- **Where It Appeared:** `README.md`, `docs/RESEARCH.md`, `benchmarks/cost_comparison_compressed.csv`, `benchmarks/encoding_efficiency.csv`, `benchmarks/generated_tables.md`.
- **Root Cause:** Different document updates were committed from different benchmark runs. Timing in Python is hardware- and environment-dependent.
- **Corrected Text & Values:**
  - One final benchmark generation was executed using `python python/experiments.py` and `python python/plot_results.py`.
  - The authoritative frozen OpenAlex encoding latency is **11.7 ms ± 0.2 ms (N=10)**.
  - Synchronized across all outputs: `benchmarks/cost_comparison_compressed.csv`, `benchmarks/encoding_efficiency.csv`, `benchmarks/generated_tables.md`, `README.md`, and `docs/RESEARCH.md`.
  - Added run count `N=10` to Table B encoding column headings.
  - Created freeze manifest `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json` recording UTC freeze timestamp (`2026-10-27T16:28:29Z`), generation commands, SHA-256 hashes of all 7 benchmark files, and immutability notice.
  - Added Benchmark Freeze subsection to `docs/REPRODUCIBILITY.md`.
- **Files Changed:** `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json`, `benchmarks/cost_comparison_compressed.csv`, `benchmarks/encoding_efficiency.csv`, `benchmarks/generated_tables.md`, `README.md`, `docs/RESEARCH.md`, `docs/REPRODUCIBILITY.md`.
- **Automated Guard Added:** `check_benchmark_freeze_and_timing_guards()` in `python/check_consistency.py` validates SHA-256 hashes of all frozen benchmark files against the freeze record and verifies that Table B contains `11.7 ms ± 0.2 ms` with `N=10`.

---

### 10.3 Fix 3: Full Clickable Sepolia Proof and Retrieval Verification

- **Previous Text / Discrepancy:** The README contained truncated transaction hashes (`0xa55af2b2...`) and lacked an empirical verification statement confirming blob retrieval and reconstruction.
- **Where It Appeared:** `README.md` Section 7, `docs/SEPOLIA_DEPLOYMENT.md`.
- **Root Cause:** Hashes were truncated for layout conciseness. A full post-broadcast retrieval verification pass had not been documented.
- **Corrected Text & Values:**
  - Published full 66-character hashes for deployment transaction (`0xa55af2b2a6ec29cc706bd8e5ebc166d6ae3130002c183f7ebdbb8186cc834751`), blob transaction (`0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea`), dataset ID (`0x4f7b50bd684170f2c427d8975ee6478fadbc46918b764f1e8a4915374bf9d29b`), and versioned hash (`0x010e6c7880a790abbedd746b98b713b5780e8e662d9f57f31cc51671b01faf11`).
  - Linked `DatasetRegistry` contract to plain address view `https://sepolia.etherscan.io/address/0x238dE56E52A3F6C6708952052e6a20E5102b4d5b` (noting that contract source code verification on Etherscan remains a manual author step).
  - Omitted Blobscan transaction link per Fix 3 criteria because public Blobscan Sepolia indexer head was lagging at block 11,818,175 (~188k blocks behind live block 12,006,195).
  - Attempted live consensus retrieval: public Sepolia beacon nodes (`lodestar-sepolia.chainsafe.io` and `ethereum-sepolia-beacon-api.publicnode.com`) returned 500 and 400 gateway errors.
  - Reconstructed dataset from local sidecar cache (`data/encoded_sepolia/blob_0.bin`): exactly 212,517 canonical bytes reconstructed, reconstructed SHA-256 matched manifest (`0b7175bfbd6aa0cf048d8c9e5bf1a2c51302531fcce936871bcb84d8b919c12c`), and versioned hash matched on-chain hash. Documented in `deployments/sepolia_retrieval_verification.json`.
  - Added retrieval verification statement in `README.md` and `docs/SEPOLIA_DEPLOYMENT.md`.
- **Files Changed:** `README.md`, `docs/SEPOLIA_DEPLOYMENT.md`, `deployments/sepolia_retrieval_verification.json`.
- **Automated Guard Added:** `check_sepolia_proof_and_retrieval_guards()` in `python/check_consistency.py` fails if truncated hashes appear in `README.md`, validates on-chain addresses/hashes against `deployments/sepolia_deployment.json`, and asserts that retrieval verification claims match `deployments/sepolia_retrieval_verification.json`.

---

### 10.4 Fix 4: Remove Audit-History Language and Expand Calldata Shorthand

- **Previous Text / Discrepancy:** `README.md` contained `not the 32 gas/byte heuristic previously discussed`, `docs/RESEARCH.md` referenced the commonly cited 32 gas/byte figure and 69x savings, and headline findings used imprecise shorthand `standard calldata (16 gas/byte)`.
- **Where It Appeared:** `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.
- **Root Cause:** Preliminary internal discussion notes and review heuristics leaked into public repository documentation.
- **Corrected Text & Values:**
  - Removed all audit-history phrases (`previously discussed`, `32 gas/byte heuristic`, `69x`).
  - Published exact payload-specific EIP-7623 floor formulation:
    > Because the measured compressed payload is over 99.6% non-zero bytes, its effective EIP-7623 floor is approximately 39.88 gas per byte. Post-Pectra calldata costs for pure DA increase by approximately 2.5x, further widening the economic advantage of blobs. Detailed vectors and calculations are in `benchmarks/calldata_eip7623_sensitivity.csv`.
  - Expanded headline shorthand in `README.md` and docs to:
    > standard calldata cost, 4 gas per zero byte and 16 gas per non-zero byte, before application of the EIP-7623 floor
- **Files Changed:** `README.md`, `docs/RESEARCH.md`, `docs/METHODOLOGY.md`.
- **Automated Guard Added:** `check_no_obsolete_claims()` and `check_headline_calldata_shorthand()` in `python/check_consistency.py` fail if `previously discussed`, `32 gas/byte heuristic`, or headline `(16 gas/byte)` appear.

---

### 10.5 Fix 5: Synthetic ML Training Trace Terminology

- **Previous Text / Discrepancy:** The phrase `The ML training telemetry contains...` and informal terms like `ML training telemetry` appeared in explanatory notes and scripts.
- **Where It Appeared:** `README.md`, `docs/RESEARCH.md`, `docs/DEMO_VIDEO_SCRIPT.md`, `python/experiments.py`.
- **Root Cause:** Inconsistent terminology referring to the synthetic dataset as telemetry rather than synthetic trace.
- **Corrected Text & Values:**
  - Standardized sentence to begin: `The synthetic ML training trace contains...`
  - Replaced informal occurrences with `synthetic ML training trace`.
- **Files Changed:** `README.md`, `docs/RESEARCH.md`, `docs/DEMO_VIDEO_SCRIPT.md`, `python/experiments.py`.
- **Automated Guard Added:** `check_no_banned_ml_phrases()` in `python/check_consistency.py` fails if `The ML training telemetry contains` appears in `README.md` or `docs/RESEARCH.md`.

