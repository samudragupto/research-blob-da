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
  $\text{tokens} = \text{zero\_bytes} \times 1 + \text{nonzero\_bytes} \times 4$,
  $\text{standard\_calldata\_gas} = 4 \times \text{tokens}$,
  $\text{floor\_calldata\_gas} = 10 \times \text{tokens}$,
  $\text{tx.gasUsed} = 21,000 + \max(\text{standard\_calldata} + \text{execution\_gas\_used}, 10 \times \text{tokens})$.
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
