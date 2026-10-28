# Journal Extension Research Integrity Corrections Log

This document records the audit findings, root causes, corrections, and automated regression guards for peer review issues identified on branch `research/journal-extension`.

---

## Overview of Audit Scope

| Issue ID | Domain | Severity | Pre-Audit Finding | Audit Status |
|---|---|---|---|---|
| ISSUE-01 | Blob-Count and Usable Capacity Inconsistency | High (Calculation inconsistency) | Discrepancy between 126,945 B and 126,976 B usable capacity | Corrected |
| ISSUE-02 | Real-Dataset Provenance Verification | Critical (Provenance mischaracterization) | Unverified external sources; generated data labeled real | Corrected |
| ISSUE-03 | RQ4 Overclaim Correction | High (Overgeneralized inference) | Small probe (12 attempts) generalized to consensus pruning | Corrected and Downgraded |
| ISSUE-04 | Archival Bridge Labelling | High (Ambiguous prototype scope) | Local CAS metrics presented without clear distinction from public networks | Corrected and Downgraded |
| ISSUE-05 | Statistical and Cost Claim Corrections | High (Unjustified statistical claims) | `p < 0.001` on deterministic runs; unqualified 100% detection; cost scope | Corrected |
| ISSUE-06 | Literature Review and v0.1.0 Asset Verification | High (Review scope & asset verification) | Systematic review claim without protocol screening logs; release asset check | Corrected and Downgraded |

---

## ISSUE-01: Blob-Count and Usable Capacity Inconsistency

### 1. Previous Claim or Value
The journal draft contained conflicting statements regarding the usable payload capacity per blob under field element 31-byte packing (`FE31`):
- Both 126,945 bytes and 126,976 bytes were cited as usable capacity.
- Theoretical uncompressed blob counts were reported as 8 blobs for 1 MiB (1,048,576 bytes), 39 blobs for 5 MiB (5,242,880 bytes), and 154 blobs for 20 MiB (20,971,520 bytes).
- Compressed local-evaluation counts in `benchmarks/journal-extension/local/summary_local_matrix.csv` were reported as 19 blobs for 2,398.1 KiB (2,455,654 bytes) and 76 blobs for 9,591.4 KiB (9,821,983 bytes).

### 2. Where Found
- `python/encoder.py` (inline comments and exported constants)
- `benchmarks/journal-extension/local/summary_local_matrix.csv`
- `benchmarks/journal-extension/local/trial_level_local_matrix.csv`
- `paper/tables/table_local_matrix.tex`
- `paper/sections/results.tex`
- `paper/sections/methodology.tex`
- `docs/journal/EXPERIMENTAL_PROTOCOL.md`

### 3. Root Cause
Conceptual confusion between gross field element payload capacity and net body capacity after header framing:
- An EIP-4844 blob comprises 4,096 BLS12-381 field elements.
- Under `FE31` packing, 31 bytes are packed per 32-byte field element to remain strictly below the BLS12-381 scalar field modulus $r$. This yields $4,096 \times 31 = 126,976$ gross bytes per blob.
- However, our framing specification places a 31-byte header (`HEADER_SIZE = 31`) in Field Element 0 (containing magic bytes, version, compression codec, total uncompressed length, and blob sequencing index).
- Therefore, the remaining 4,095 field elements provide exactly $4,095 \times 31 = 126,945$ usable body bytes per blob (`BODY_CAPACITY_FE31 = 126945`).
- The uncompressed estimates erroneously divided by 131,072 or 126,976 gross bytes without subtracting the mandatory header framing, producing truncated blob counts (8, 39, 154 instead of 9, 42, 166). Similarly, compressed payload counts were truncated due to using gross 126,976 capacity.

### 4. Corrected Claim or Value
Documented the exact mathematical derivation in `python/encoder.py` and exported explicit helpers:
- Formula: $\text{blobs} = \lceil \text{payload\_bytes} / 126,945 \rceil$ for `FE31`.
- 1 MiB uncompressed (1,048,576 bytes): $\lceil 1,048,576 / 126,945 \rceil = 9$ blobs.
- 5 MiB uncompressed (5,242,880 bytes): $\lceil 5,242,880 / 126,945 \rceil = 42$ blobs.
- 20 MiB uncompressed (20,971,520 bytes): $\lceil 20,971,520 / 126,945 \rceil = 166$ blobs.
- 2,398.1 KiB compressed (2,455,654 bytes): $\lceil 2,455,654 / 126,945 \rceil = 20$ blobs (corrected from 19).
- 9,591.4 KiB compressed (9,821,983 bytes): $\lceil 9,821,983 / 126,945 \rceil = 78$ blobs (corrected from 76).
- All theoretical estimates explicitly state they use the identical 126,945 usable body capacity.

### 5. Files Changed
- `python/encoder.py`: Added explicit derivation comments, exported `BODY_CAPACITY_FE31 = 126945`, `calculate_blob_count()`, and `get_usable_payload_bytes_per_blob()`.
- `python/journal_experiments.py`: Updated blob counting logic to use `calculate_blob_count()`.
- `benchmarks/journal-extension/local/summary_local_matrix.csv`: Corrected blob counts across all rows.
- `benchmarks/journal-extension/local/trial_level_local_matrix.csv`: Corrected trial-level blob counts.
- `paper/tables/table_local_matrix.tex`: Updated published blob count column.
- `paper/sections/results.tex`: Updated in-text blob counts and scaling ratios.
- `paper/sections/methodology.tex`: Clarified 126,945 usable body bytes vs 126,976 gross bytes.
- `docs/journal/EXPERIMENTAL_PROTOCOL.md`: Synchronized formulas and expected blob counts.
- `tests/test_blob_capacity.py`: Created dedicated test suite validating constants and recomputed counts.

### 6. Automated Guard Added
- Guard function `check_blob_counts_consistency()` in `python/check_journal_consistency.py`.
- Regression tests in `tests/test_blob_capacity.py`. Fails immediately if any published table, summary CSV, or trial CSV contains a blob count differing from $\lceil \text{bytes} / 126,945 \rceil$.

### 7. Status
Corrected.

---

## ISSUE-02: Real-Dataset Provenance Verification

### 1. Previous Claim or Value
The journal draft labeled three datasets as real:
1. `real_openalex_works`: Claimed 200 records, 761,429 source bytes, while claiming to preserve v0.1.0 baseline consistency.
2. `real_climate_sensor`: Claimed real external download from NOAA Integrated Surface Database (5,000 observations, 954,120 source bytes).
3. `real_ml_training_trace`: Claimed real external download of PyTorch training traces (5,000 steps, 1,248,310 source bytes).

### 2. Where Found
- `data/journal/manifests/dataset_provenance.json`
- `data/journal/manifests/checksums.sha256`
- `docs/journal/DATASETS.md`
- `python/prepare_journal_datasets.py`
- `python/journal_experiments.py`
- `python/network_harness.py`
- `paper/sections/methodology.tex`
- `paper/sections/results.tex`
- `paper/tables/table_local_matrix.tex`
- `benchmarks/journal-extension/local/summary_local_matrix.csv`

### 3. Root Cause
- OpenAlex: The actual committed file `data/real_academic_openalex.json` is the authentic 500-work v0.1.0 dataset (264,057 source bytes, SHA-256 `af655842...`). A draft script mistakenly documented an uncommitted 200-work subset, creating an apparent contradiction with the frozen baseline.
- Climate sensor & ML trace: These datasets were generated by local Python scripts conforming to realistic NOAA ISD and PyTorch training run schemas. Because they were locally generated rather than directly fetched from external endpoints, labeling them with the prefix `real_` violated research integrity standards.

### 4. Corrected Claim or Value
- OpenAlex: Verified against `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json`. The committed file contains exactly 500 records, 264,057 source bytes, and canonical payload SHA-256 `af65584227c707d3c16f7841a233070808ab1ed070f10f32e841082889a8c544`, preserving 100% v0.1.0 baseline parity.
- Climate sensor: Relabeled to `synthetic_climate_sensor_noaa_format`. Origin documented as `synthetic_generator_domain_schema` under CC0-1.0.
- ML training trace: Relabeled to `synthetic_ml_training_trace`. Origin documented as `synthetic_generator_domain_schema` under Apache-2.0.
- Negative control: Deterministic seeded PRNG (seed `0x5EED_4844`) documented and committed.
- Recomputed source file SHA-256 and canonical payload SHA-256 for all corpora.

### 5. Files Changed
- `data/journal/manifests/dataset_provenance.json`: Updated identifiers, origins, and verified URLs.
- `data/journal/manifests/checksums.sha256`: Updated filenames and exact SHA-256 digests.
- `docs/journal/DATASETS.md`: Updated taxonomy, provenance table, and licensing details.
- `python/prepare_journal_datasets.py`: Relabeled generated datasets.
- `python/journal_experiments.py`: Updated dataset keys and paths.
- `python/network_harness.py`: Updated pending experiment references.
- `benchmarks/journal-extension/local/summary_local_matrix.csv`: Relabeled dataset rows.
- `benchmarks/journal-extension/local/trial_level_local_matrix.csv`: Relabeled trial rows.
- `benchmarks/journal-extension/network/pending_experiments.json`: Synchronized dataset identifiers.
- `paper/sections/methodology.tex` and `paper/sections/results.tex`: Updated corpus descriptions.
- `paper/tables/table_local_matrix.tex`: Updated dataset column labels.

### 6. Automated Guard Added
- Guard function `check_dataset_provenance()` in `python/check_journal_consistency.py`.
- Regression tests in `tests/test_research_integrity.py`. Requires every `real_*` dataset to have `origin: external_download`, non-empty source URL, retrieval date, license, and committed file hash match. Rejects any generated dataset labeled `real_`.

### 7. Status
Corrected.

---

## ISSUE-03: RQ4 Overclaim Correction

### 1. Previous Claim or Value
The draft stated that public consensus Beacon endpoints exhibited 0% retrieval success and used HTTP 401 and 404 responses to support a broad claim regarding the 4,096-epoch consensus-layer blob pruning window. It also grouped simulated archival caches alongside public endpoints and reported bare percentages (e.g., 0.0%) without sample sizes across a total of 12 attempts.

### 2. Where Found
- `paper/sections/results.tex`
- `paper/tables/table_retrieval.tex`
- `docs/journal/RETRIEVAL_STUDY.md`
- `docs/journal/RESEARCH_QUESTIONS.md`
- `benchmarks/journal-extension/retrieval/summary.csv`
- `benchmarks/journal-extension/retrieval/attempts.jsonl`

### 3. Root Cause
Overgeneralizing from a limited probe study (12 total requests across 4 tiers) to an Ethereum-wide retrieval failure rate, and conflating gateway authentication barriers (HTTP 401), rate limits (HTTP 400), and explorer indexer lag (HTTP 404) with protocol-level consensus pruning.

### 4. Corrected Claim or Value
- Standardized findings across all sections with required academic qualification:
  > Unauthenticated public Sepolia Beacon API endpoints probed in this study did not return the requested blob sidecar. The failure reasons included authentication requirements (HTTP 401), endpoint unavailability (HTTP 400/500), and potential indexer lag. These observations do not distinguish consensus-layer pruning from access-control or indexing limitations. A dedicated pruning-window study requires archival-node access and age-stratified probes over multiple weeks.
- Reclassified `archival_provider` to `simulated_archival_cache`.
- Separated `table_retrieval.tex` into two distinct panels:
  - Panel A: Public Endpoint Probes (`chainsafe_lodestar_public`, `publicnode_beacon_api`, `drpc_beacon_sepolia`, `blobscan_sepolia_indexer`).
  - Panel B: Local Verification (`dual_horizon_archival_gateway` [simulated archival cache] and `local_mock_retriever` [local cache]).
- Added explicit attempt counts beside all success rates: `0/2 (0.0%)`, `0/1 (0.0%)`, `0/1 (0.0%)`, `0/2 (0.0%)`, `1/1 (100.0%)`, `2/2 (100.0%)`.

### 5. Files Changed
- `paper/sections/results.tex`: Rewrote RQ4 subsection.
- `paper/tables/table_retrieval.tex`: Separated public probes from local verification and added sample counts.
- `docs/journal/RETRIEVAL_STUDY.md`: Rewrote scope, failure mode taxonomy, and results table.
- `docs/journal/RESEARCH_QUESTIONS.md`: Updated RQ4 hypothesis and metric definitions.
- `benchmarks/journal-extension/retrieval/summary.csv`: Relabeled source types.

### 6. Automated Guard Added
- Guard function `check_rq4_retrieval_claims()` in `python/check_journal_consistency.py`.
- Regression tests in `tests/test_research_integrity.py`. Enforces required qualified text in `results.tex` and `RETRIEVAL_STUDY.md`, prohibits generalized pruning claims, and verifies source type relabeling.

### 7. Status
Corrected and Downgraded.

---

## ISSUE-04: Archival Bridge Labelling

### 1. Previous Claim or Value
Reported ingest latency (6.12 ms) and retrieval latency (2.84 ms) in contexts that could lead readers to infer that a public decentralized storage network (such as IPFS, Filecoin, or Arweave) was empirically benchmarked.

### 2. Where Found
- `paper/sections/design.tex`
- `paper/sections/results.tex`
- `paper/sections/discussion.tex`
- `docs/journal/ARCHIVAL_BRIDGE.md`
- `docs/journal/RESEARCH_QUESTIONS.md`
- `benchmarks/journal-extension/archival/results.json`

### 3. Root Cause
Conflating the conceptual dual-horizon architecture (which targets IPFS/Filecoin/Arweave) with the actual prototype evaluated in the paper, which was implemented as a local content-addressed store (CAS) to verify cryptographic roundtrip integrity after simulated blob expiry.

### 4. Corrected Claim or Value
- Explicitly stated across design, results, and discussion sections:
  > We implemented and evaluated a local content-addressed archival prototype that mirrors blob payloads into a deterministic content-addressed store and verifies them against Ethereum-anchored commitments after simulated blob expiry. Public decentralized storage backends such as IPFS pinning services, Filecoin deals, and Arweave transactions were not evaluated in this study.
- Relabeled measured latencies as `local_content_addressed_store` (Local prototype measurement).
- Added explicit discussion paragraph stating that bridging to public pinning or storage networks is future work, and noting that local NVMe CAS latencies are not representative of wide-area decentralized storage network latencies.

### 5. Files Changed
- `paper/sections/design.tex`: Added prototype scope clarification.
- `paper/sections/results.tex`: Updated latency reporting to specify local CAS prototype.
- `paper/sections/discussion.tex`: Added dedicated future work paragraph on public network integration.
- `docs/journal/ARCHIVAL_BRIDGE.md`: Added evaluation scope clarification and evidence-type notes.
- `docs/journal/RESEARCH_QUESTIONS.md`: Clarified RQ5 evaluation bounds.
- `benchmarks/journal-extension/archival/results.json`: Added `local_content_addressed_store` classifier.

### 6. Automated Guard Added
- Guard function `check_archival_bridge_claims()` in `python/check_journal_consistency.py`.
- Regression tests in `tests/test_research_integrity.py`. Rejects claims of measuring IPFS, Filecoin, or Arweave without an external transaction record and enforces presence of local prototype qualification.

### 7. Status
Corrected and Downgraded.

---

## ISSUE-05: Statistical and Cost Claim Corrections

### 1. Previous Claim or Value
- Claimed `p < 0.001` for roundtrip reconstruction across deterministic runs.
- Claimed unqualified `100% detection` and `zero false negatives` for adversarial security checks.
- Baseline cost table lacked dated sources, regions, fee assumptions, duration, and evidence-type classifications.
- Break-even fee was cited as `8.2 gwei` in draft notes versus `207.9 gwei` in v0.1.0 baseline.
- Unit confusion between execution gas and base fee.

### 2. Where Found
- `paper/sections/results.tex`
- `paper/sections/security.tex`
- `paper/tables/table_baselines.tex`
- `paper/tables/table_security.tex`
- `paper/tables/table_local_matrix.tex`
- `paper/tables/table_retrieval.tex`
- `benchmarks/journal-extension/baseline_comparison.csv`
- `docs/journal/THREAT_MODEL.md`
- `docs/journal/RESEARCH_QUESTIONS.md`

### 3. Root Cause
- Applying inferential p-value testing to deterministic unit tests with zero variance.
- Framing security scenario coverage as a general security proof rather than an empirical test suite.
- Compiling cost comparison figures without standardized provenance columns.
- Break-even fee calculation error: dividing gas quantities without multiplying by execution base fee ($15 \text{ gwei} \times 13.86 \approx 207.9 \text{ gwei}$, whereas $13.86 \text{ gwei}$ or $8.2 \text{ gwei}$ resulted from incorrect baseline subtraction).

### 4. Corrected Claim or Value
- Removed `p < 0.001` everywhere. Replaced with:
  > Roundtrip reconstruction succeeded for all 10 trials with zero byte discrepancies. This is a correctness result, not a statistical significance test.
- Reframed security detection as:
  > All 15 implemented adversarial test scenarios were detected by the corresponding verification checks (15/15 implemented scenarios detected). These results demonstrate that the specified checks function as designed for the tested scenarios. They do not constitute a formal security proof or a complete coverage of possible attacks.
- Extended `baseline_comparison.csv` and `table_baselines.tex` with: `retrieval_date_utc`, `source`, `region_or_network`, `duration_assumed`, `egress_included`, `evidence_type`.
- Documented break-even fee derivation: $B^* = \frac{G_{\text{call}} - G_{\text{exec}}}{131,072} \times \text{BaseFee}$. At 15 gwei execution base fee, $B^* \approx 207.9$ gwei. Documented that 8.2 gwei was an erroneous calculation omitting the execution fee multiplier.
- Added explicit evidence-type markers to all LaTeX tables in `paper/tables/`.

### 5. Files Changed
- `paper/sections/results.tex`: Removed `p < 0.001`, clarified break-even derivation.
- `paper/sections/security.tex`: Replaced 100% detection claim with bounded 15/15 scenario language.
- `paper/tables/table_baselines.tex`: Added evidence type and provenance columns.
- `paper/tables/table_local_matrix.tex`: Added evidence type marker.
- `paper/tables/table_retrieval.tex`: Added evidence type markers for panels A and B.
- `paper/tables/table_security.tex`: Added evidence type marker and sample counts.
- `benchmarks/journal-extension/baseline_comparison.csv`: Added standardized provenance columns.
- `docs/journal/THREAT_MODEL.md` & `docs/journal/RESEARCH_QUESTIONS.md`: Reframed invariants.

### 6. Automated Guard Added
- Guard function `check_statistical_and_cost_claims()` in `python/check_journal_consistency.py`.
- Regression tests in `tests/test_research_integrity.py`. Prohibits unqualified p-values, enforces 15/15 scenario wording, validates cost table columns, and requires evidence-type markers in every table.

### 7. Status
Corrected.

---

## ISSUE-06: Literature Review and v0.1.0 Asset Verification

### 1. Previous Claim or Value
- Claimed a "systematic review across five databases with 38 works screened and 14 verified references" without documented search strings or screening logs.
- Novelty claim: "To our knowledge, this is one of the first...".
- Potential concern regarding v0.1.0 release asset digests on GitHub versus frozen manifest.

### 2. Where Found
- `docs/journal/LITERATURE_REVIEW_PROTOCOL.md`
- `docs/journal/RELATED_WORK_MATRIX.md`
- `paper/sections/related_work.tex`
- GitHub release `v0.1.0` assets

### 3. Root Cause
Adopting formal PRISMA "systematic review" terminology for a preliminary targeted survey of related literature, and lack of an automated release-asset byte-level audit.

### 4. Corrected Claim or Value
- Downgraded claims from "systematic review" to "preliminary related-work survey" across all documents.
- Updated novelty claim:
  > To our knowledge, based on a preliminary survey of the literature cited in this work, this is among the early evaluations of EIP-4844 blobs as a temporary publication layer for structured research artifacts. A systematic review remains future work.
- Verified all 14 references in `paper/references.bib` against DOIs/URLs. None were fabricated.
- Executed clean-clone byte-level audit of release `v0.1.0`: cloned `v0.1.0` into a clean directory, downloaded release assets via `gh release download v0.1.0`, and verified every asset against `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json`. All 7 assets matched byte-for-byte with 100% parity across tagged files, freeze manifest, and GitHub API digests. Recorded full audit log in `docs/journal/RELEASE_ASSET_AUDIT.md`.

### 5. Files Changed
- `docs/journal/LITERATURE_REVIEW_PROTOCOL.md`: Downgraded protocol claims.
- `docs/journal/RELATED_WORK_MATRIX.md`: Reframed matrix as preliminary survey.
- `docs/journal/RELEASE_ASSET_AUDIT.md`: Created comprehensive byte-level audit log.
- `paper/sections/related_work.tex`: Updated related work framing and novelty language.

### 6. Automated Guard Added
- Guard function `check_literature_review_claims()` in `python/check_journal_consistency.py`.
- Regression tests in `tests/test_research_integrity.py`. Prohibits claiming a systematic review without screening log evidence and validates citation resolution.

### 7. Status
Corrected and Downgraded.

---

## Summary of Regression Guards

The automated consistency checker `python/check_journal_consistency.py` now implements 11 comprehensive automated guards:
1. `check_prohibited_claims`: Fails on prohibited marketing or ungrounded claims.
2. `check_latex_citations`: Fails if citations do not resolve to verified entries in `references.bib`.
3. `check_paper_tables_and_figures`: Fails if required LaTeX tables or PDF/PNG figures are missing.
4. `check_blob_counts_consistency`: Fails if published blob counts deviate from $\lceil \text{bytes} / 126,945 \rceil$.
5. `check_dataset_provenance`: Fails if synthetic datasets are labeled `real_`, or if `real_` datasets lack external download provenance.
6. `check_rq4_retrieval_claims`: Fails if RQ4 claims lack qualification or overgeneralize to consensus pruning.
7. `check_archival_bridge_claims`: Fails if archival bridge claims network measurements without execution logs.
8. `check_statistical_and_cost_claims`: Fails on unqualified `p <` claims, unbounded detection claims, or missing table evidence markers.
9. `check_literature_review_claims`: Fails if the paper claims a systematic review without screening logs.
10. `check_git_branch_and_provenance`: Fails if current branch is not `research/journal-extension` or if `origin/main` hash diverges.
11. `check_zero_emojis`: Fails if emojis are present in any tracked file.
