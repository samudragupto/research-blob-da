# Reproducibility Checklist

This checklist audits the `research-blob-da` journal artifact against standard computational reproducibility criteria (e.g., ACM / IEEE / NeurIPS artifact standards).

---

## 1. Source Code and Licensing

- [x] **Open Source Repository**: Publicly accessible at `https://github.com/samudragupto/research-blob-da`.
- [x] **Permissive License**: MIT License committed in root `LICENSE`.
- [x] **Code Quality & Formatting**:
  - Solidity formatted via `forge fmt`.
  - Python formatted via Black and Ruff (`pyproject.toml`).
  - Zero-emoji policy strictly enforced across all files.
- [x] **Branch Isolation**: All journal extensions committed on `research/journal-extension`; main branch untouched.

---

## 2. Dependencies and Execution Environment

- [x] **Pinned Dependencies**: Pinned Python package dependencies in `requirements.txt` and `pyproject.toml`.
- [x] **Solidity Toolchain**: Foundry / Forge v1.5.1-stable with pinned compiler v0.8.24.
- [x] **Environment Capture**: Automated machine-readable manifest generator (`python/capture_environment.py`) generating `benchmarks/journal-extension/manifests/environment.json`.
- [x] **Privacy and Credentials**: Zero usernames, private home paths, RPC tokens, or private keys written to repository files.

---

## 3. Data Corpus and Provenance

- [x] **Authoritative Provenance**: Real datasets (OpenAlex, NOAA climate sensors, ML training traces) sourced from primary open endpoints.
- [x] **Machine-Readable Provenance Manifest**: `data/journal/manifests/dataset_provenance.json` recording source URLs, retrieval timestamps, licensing, record counts, and raw/canonical byte sizes.
- [x] **Cryptographic Checksums**: Pre-ingestion SHA-256 digests recorded in `data/journal/manifests/checksums.sha256`.
- [x] **Open Data Licensing**: CC0 and Public Domain licenses verified for all redistributed test fixtures.

---

## 4. Experimental Rigor and Statistics

- [x] **Deterministic Seeds**: Fixed PRNG seed (`42`) used across all synthetic data generation, train/test sampling, and bootstrap resampling.
- [x] **Warm-Up Protocol**: 2 unrecorded warm-up iterations executed prior to all local timing runs.
- [x] **Sample Sizes**: Micro-benchmarks execute across $N = 10$ recorded iterations; large payload runs execute across $N = 5$ iterations.
- [x] **Statistical Estimators**: Mean, standard deviation, median, IQR, and non-parametric $95\%$ percentile bootstrap confidence intervals ($B = 1,000$) reported.
- [x] **Extreme Percentiles**: $p_{99}$ reported only when $N \ge 100$ to prevent small-sample distortion.
- [x] **Raw Trial-Level Data**: All individual run measurements exported to CSV/JSONL under `benchmarks/journal-extension/`.

---

## 5. Security and Adversarial Testing

- [x] **Formal Threat Model**: Documented in `docs/journal/THREAT_MODEL.md`.
- [x] **Adversarial Scenarios**: 15 distinct threat vectors evaluated in `python/adversarial_evaluation.py` and `tests/test_adversarial.py`.
- [x] **Verified Detection**: $100\%$ detection rate achieved; false positive rate $0\%$.
- [x] **Dispute Game Simulation**: Smart contract fraud refutation verified in Foundry test suite.

---

## 6. Manuscript and Artifact Compilation

- [x] **Reproducible Generation**: All LaTeX tables (`paper/tables/`) and figures (`paper/figures/`) generated directly from raw CSV/JSON benchmark files via `python/generate_paper_artifacts.py`.
- [x] **Honest Claims**: Zero prohibited claims (no claims of permanent blob storage, universal cost superiority, or contract formal verification).
- [x] **Verified Bibliography**: All 14 references verified from primary publisher records and DOIs.
