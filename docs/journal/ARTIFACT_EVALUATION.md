# Artifact Evaluation and Replication Guide

This guide provides step-by-step instructions for reproducing the empirical benchmarks, smart contract verification campaigns, adversarial security tests, and paper compilation for the `research-blob-da` journal extension.

---

## 1. System Requirements

### 1.1 Hardware Specifications
- **CPU**: x86_64 architecture with at least 4 physical cores (8+ logical cores recommended; evaluated on AMD 16-thread CPU).
- **Memory**: Minimum 8~GiB RAM (16~GiB recommended for 50~MiB payload scaling simulations).
- **Storage**: At least 5~GB of free solid-state storage.

### 1.2 Software Dependencies
- **Operating System**: Windows 11 Enterprise, Ubuntu 22.04/24.04 LTS, or macOS Sonoma.
- **Python**: Version 3.10 through 3.13 (evaluated on Python 3.13.11).
- **Foundry / Forge**: Version 1.5.1-stable or later.
- **LaTeX Engine**: Tectonic 0.17+ (recommended portable single-binary compiler) or TeX Live / MiKTeX.
- **Git**: Version 2.40+.

---

## 2. Quick-Start Replication

Clone the repository and switch to the journal extension branch:

```bash
git clone https://github.com/samudragupto/research-blob-da.git
cd research-blob-da
git switch research/journal-extension
```

### 2.1 Virtual Environment Setup
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2.2 Verify Environment Capture
Generate a fresh machine-readable system environment manifest:
```bash
python python/capture_environment.py
```
Outputs: `benchmarks/journal-extension/manifests/environment.json`.

---

## 3. Reproduction Pipeline

### Step 1: Smart Contract Test Suite
Verify the Foundry contract suite (36 passing tests across 6 test suites, including invariant testing):
```bash
forge test
```
To run stateful invariant tests and fuzzing with gas reports:
```bash
forge test --gas-report
```

### Step 2: Python Unit and Adversarial Test Suite
Execute the complete 53-item pytest suite (covering canonical serialization, commitments, encoder/decoder, cost model, archival bridge, and the 15 adversarial security scenarios):
```bash
pytest -v
```

### Step 3: Dataset Corpus Preparation
Canonicalize and frame the five evaluation dataset classes:
```bash
python python/prepare_journal_datasets.py
```
Outputs:
- Canonical binary fixtures under `data/journal/`
- Provenance manifest: `data/journal/manifests/dataset_provenance.json`
- Cryptographic digests: `data/journal/manifests/checksums.sha256`

### Step 4: Local Evaluation Matrix and Ablations
Run the complete multi-size local scaling matrix, compression ablations (levels 0–19), packing ablations (\texttt{FE31} vs \texttt{FE254}), commitment ablations, and assembly simulations:
```bash
python python/journal_experiments.py
```
Outputs:
- Raw trial-level records: `benchmarks/journal-extension/local/trial_level_local_matrix.csv`
- Aggregate summary: `benchmarks/journal-extension/local/summary_local_matrix.csv`
- Ablation records: `ablation_compression.csv`, `ablation_packing.csv`, `ablation_commitments.csv`, `ablation_framing.csv`
- Fault simulations: `assembly_simulations.json`

### Step 5: Sidecar Retrieval Study
Execute the provider-agnostic retrieval evaluation:
```bash
python python/retrieval_study.py
```
Outputs:
- Attempt traces: `benchmarks/journal-extension/retrieval/attempts.jsonl`
- Summaries: `benchmarks/journal-extension/retrieval/summary.csv`

### Step 6: Dual-Horizon Archival Bridge Benchmark
Execute the complete dual-horizon lifecycle (publication, CID generation, simulated consensus blob eviction, CAS retrieval, and cryptographic verification):
```bash
python python/archival_bridge.py
```
Outputs: `benchmarks/journal-extension/archival/results.json`.

### Step 7: Guarantee-Aware Baseline Framework
Generate the multi-dimensional baseline comparison and publication figure:
```bash
python python/generate_baseline_comparison.py
```
Outputs:
- `benchmarks/journal-extension/manifests/storage_baselines.json`
- `benchmarks/journal-extension/baseline_comparison.csv`
- `benchmarks/journal-extension/figures/guarantee_cost_matrix.png` & `.pdf`

### Step 8: Security Threat-Model Scenarios
Run the 15 adversarial security scenarios:
```bash
python python/adversarial_evaluation.py
```
Outputs: `benchmarks/journal-extension/security/results.json`.

### Step 9: LaTeX Table and Figure Artifact Generation
Compile the raw benchmark files into LaTeX tables and publication figures:
```bash
python python/generate_paper_artifacts.py
```
Outputs:
- `paper/tables/table_local_matrix.tex`
- `paper/tables/table_retrieval.tex`
- `paper/tables/table_baselines.tex`
- `paper/tables/table_security.tex`
- `paper/figures/*.png` & `*.pdf`

### Step 10: Compile Manuscript PDF
Compile the LaTeX journal article:
```bash
cd paper
tectonic main.tex
# or using Makefile:
make pdf
```
Outputs: `paper/main.pdf`.

---

## 4. Deterministic vs. Machine-Dependent Outputs

- **Deterministic Results**:
  - Bitwise reconstruction parity ($100\%$).
  - Canonical payload byte lengths and SHA-256 digests.
  - Number of blobs required per payload size.
  - Merkle roots, KZG versioned hashes, and CIDv1 multihashes.
  - Smart contract gas consumption for invariant execution.
  - Adversarial detection rate ($100\%$, 15/15 scenarios).
- **Machine-Dependent Timings**:
  - Absolute compression latency (ms) and throughput (MiB/s).
  - Operating system page cache I/O latencies.
  - Peak resident set size (RSS).

---

## 5. Zenodo Archival Protocol

Following final acceptance of the manuscript:
1. Tag release `v0.2.0-journal` on `research/journal-extension`.
2. Connect GitHub repository to Zenodo via GitHub-Zenodo integration.
3. Zenodo will automatically mint a permanent Digital Object Identifier (DOI) and archive a full snapshot of code, manifests, and the compiled paper PDF.
