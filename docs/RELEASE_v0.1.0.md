# Release Notes: research-blob-da v0.1.0

**Release Tag:** `v0.1.0`  
**Release Title:** `research-blob-da v0.1.0: Verifiable Data Availability for Research Datasets via EIP-4844 Blobs`  
**Author:** Arrhat Nag (GitHub: samudragupto)  
**Date:** October 2026  

---

## Overview

`research-blob-da` is an empirical research prototype establishing Ethereum EIP-4844 blobs as a cheap, verifiable data-availability primitive for scientific research datasets, machine learning training traces, climate observations, and academic archives.

This v0.1.0 release provides a complete, tested, and reproducible pipeline:
- **Canonical Serialization & Packing:** Canonical length-prefixed stream format (RFC 8785) with conservative 31-byte field element modulus packing (`FE31`) and Zstandard compression.
- **Cryptographic Commitments:** Keccak-256 binary Merkle trees with single-leaf inclusion proofs and high-efficiency batch range proofs.
- **Foundry EVM Contracts:** `DatasetRegistry.sol` anchoring dataset records roots, content hashes, and versioned hashes read directly from the `BLOBHASH` opcode, with optimistic property refutations.
- **Empirical Evaluation:** Rigorous benchmark suite measuring monetary costs, encoding throughput, packing efficiency, and EVM gas scaling across four synthetic datasets and one real OpenAlex academic metadata dataset.
- **Economic & Protocol Models:** Exact implementations of usable blob payload limits, official EIP-7623 calldata floor formulas, multi-block SSTORE extrapolations, and fee break-even sensitivity grids.

---

## Release Artifacts

- **Core Codebase:**
  - Python Engine: `python/canonical.py`, `python/encoder.py`, `python/decoder.py`, `python/commitments.py`, `python/retriever.py`, `python/cost_model.py`, `python/fetch_real_data.py`.
  - Solidity Contracts: `contracts/DatasetRegistry.sol`, `contracts/libraries/`, `contracts/baselines/`.
  - CLI & TS Broadcast: `frontend-or-cli/rbda_cli.py`, `frontend-or-cli/ts/src/blob_tx.ts`.
- **Benchmark Data:**
  - `benchmarks/cost_comparison_uncompressed.csv` (Table A)
  - `benchmarks/cost_comparison_compressed.csv` (Table B)
  - `benchmarks/blob_capacity_limits.csv`
  - `benchmarks/fee_sensitivity.csv`
  - `benchmarks/calldata_eip7623_sensitivity.csv`
  - `benchmarks/encoding_efficiency.csv`
  - `benchmarks/verification_benchmarks.csv`
  - `benchmarks/throughput_latency.csv`
  - `benchmarks/ablation_compression.csv`
  - `benchmarks/ablation_packing.csv`
- **Publication Figures:**
  - `benchmarks/figure1_cost_comparison.{png,pdf}`
  - `benchmarks/figure2_compression_efficiency.{png,pdf}`
  - `benchmarks/figure3_verification_scaling.{png,pdf}`
  - `benchmarks/figure4_latency_breakdown.{png,pdf}`
  - `benchmarks/figure5_compression_ablation.{png,pdf}`
  - `benchmarks/figure6_fee_sensitivity.{png,pdf}`
- **Documentation:**
  - `docs/RESEARCH.md`: Comprehensive academic research paper.
  - `docs/METHODOLOGY.md`: Experimental setup, gas metrics, and hardware specifications.
  - `docs/ENGINEERING_LESSONS.md`: Concrete implementation insights and cryptographic edge cases.
  - `docs/SEPOLIA_DEPLOYMENT.md`: Step-by-step testnet deployment and sidecar retrieval guide.
  - `docs/ETHRESEARCH_POST.md`: Peer-review draft for ethresear.ch.
  - `docs/DEMO_VIDEO_SCRIPT.md`: 2-minute CLI walkthrough script.

---

## Reviewer Quickstart (Reproduction in Under 2 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/samudragupto/research-blob-da.git
cd research-blob-da

# 2. Run Foundry smart contract test suite
forge test

# 3. Set up Python environment and run test suite
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r python/requirements.txt
pytest -v tests

# 4. Regenerate all benchmarks, figures, and verified tables
python python/experiments.py
python python/plot_results.py

# 5. Run consistency check
python python/check_consistency.py
```

---

## Instructions for Author to Tag and Publish Release

When ready to tag and create the release on GitHub, execute the following commands:

```bash
# Create annotated Git tag
git tag -a v0.1.0 -m "research-blob-da v0.1.0: Verifiable Data Availability for Research Datasets via EIP-4844 Blobs"
git push origin v0.1.0

# Create GitHub release via GitHub CLI
gh release create v0.1.0 \
  --title "research-blob-da v0.1.0: Verifiable Data Availability for Research Datasets via EIP-4844 Blobs" \
  --notes-file docs/RELEASE_v0.1.0.md
```
