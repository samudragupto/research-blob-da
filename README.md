# research-blob-da

[![CI](https://github.com/ethereum-research/research-blob-da/actions/workflows/ci.yml/badge.svg)](https://github.com/ethereum-research/research-blob-da/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.24-lightgrey.svg)](contracts/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](python/)
[![EVM Target](https://img.shields.io/badge/EVM-Cancun%20(EIP--4844)-orange.svg)](foundry.toml)

**Verifiable, Cheap Data Availability for Scientific Datasets, ML Training Traces, and Academic Archives via Ethereum EIP-4844 Blobs.**

---

## 1. Executive Summary

Empirical research in machine learning, computational biology, climate science, and distributed systems faces a severe reproducibility crisis. Centralized cloud storage links decay over time, while posting primary empirical artifacts to immutable blockchain storage has historically been economically impossible (storing a 1 MiB experimental log in Ethereum contract storage costs over **$32,500**; calldata costs between **$755** and **$1,888**).

**research-blob-da** introduces an open-source protocol and reference implementation repurposing Ethereum's **EIP-4844 ephemeral data blobs** as a cheap, high-throughput, and cryptographically verifiable primitive for empirical research artifacts. 

### Key Findings
- **27.8x to 37.9x Cost Reduction vs. Standard Calldata:** Posting a 1.0 MiB dataset costs **$27.24** on EIP-4844 blobs compared to **$755.92** on standard calldata.
- **69.3x Cost Reduction vs. EIP-7623 Calldata Floors:** Under pending EIP-7623 execution floors ($32\text{ gas/byte}$), 1.0 MiB costs **$1,888.38** via calldata vs. **$27.24** via blobs.
- **High-Efficacy Compression:** Zstandard encoding reduces tabular scientific telemetry and training traces by **6.04x to 11.13x**, packing multi-megabyte datasets into 1 to 4 blobs.
- **Contiguous On-Chain Range Proofs:** Sub-sequence verification in `MerkleLib.sol` achieves up to **89.1% gas savings** over independent Merkle proofs.
- **Optimistic Property Verification:** Researchers can submit statistical property claims (e.g., loss bounds), which any challenger can refute on-chain in a single transaction for under **350,000 gas** using our zero-copy JSON parser `JsonFieldLib.sol`.

---

## 2. Architecture Overview

```text
+-----------------------------------------------------------------------------------------+
|                                    OFF-CHAIN PIPELINE                                   |
|                                                                                         |
|  Raw Research Data        Canonical Stream             Zstandard        EIP-4844 Blobs  |
|  [CSV, JSON, JSONL]  ==>  [RFC 8785 Framing]    ==>   [Levels 1-19] ==> [128 KiB Blobs] |
|                                   ||                                          ||        |
|                           contentHash = keccak256                      FE0 Header (31B) |
|                           recordsRoot = MerkleTree                            ||        |
+-----------------------------------|-------------------------------------------|---------+
                                    |                                           |
                                    v                                           v
+-----------------------------------------------------------------------------------------+
|                              ETHEREUM CANCUN CONSENSUS & EVM                            |
|                                                                                         |
|      EVM Execution Layer                                Consensus Sidecars (4,096 Epochs)
|      +-----------------------------------------+        +------------------------------+
|      | DatasetRegistry.sol                     |        | Beacon Node REST API         |
|      | - blobhash(i) verification              | <====> | - Blob 0: 4,096 BLS elements  |
|      | - Multi-tx dataset aggregation          |        | - Blob 1: 4,096 BLS elements  |
|      | - Optimistic property claims            |        | Retained for ~18.2 days      |
|      | - Zero-copy JSON fraud refutation       |        +------------------------------+
|      | - Formal citations and attestations     |                       ||
|      +-----------------------------------------+                       ||
+------------------------------------------------------------------------|----------------+
                                                                         v
                                                       Permanent Academic Archival Nodes
                                                       [IPFS, Filecoin, University Libs]
```

---

## 3. Empirical Cost and Performance Benchmarks

### 3.1 Economic Cost Comparison

| Dataset Size | Blobs Needed | EIP-4844 Blobs | Calldata | EIP-7623 Calldata | SSTORE (L1 State) | Blob vs. Calldata Savings |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **128 KiB** | 2 | **$10.71** | $95.32 | $236.87 | $4,070.73 | **8.9x** |
| **1.0 MiB** | 9 | **$27.24** | $755.92 | $1,888.38 | $32,559.23 | **27.8x** |
| **5.0 MiB** | 42 | **$105.17** | $3,775.82 | $9,438.13 | $162,792.37 | **35.9x** |
| **20.0 MiB** | 166 | **$397.98** | $15,100.44 | $37,749.68 | $651,166.64 | **37.9x** |

*Assumptions: ETH = $3,000 USD, Base Fee = 15.0 gwei, Blob Fee = 2.0 gwei.*

### 3.2 Dataset Compression Efficacy

| Domain | Records | Raw Size | Compressed | Ratio | Blobs | Encoding Time | Throughput |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **ML Training Trace** | 10,000 | 1,056 KiB | 175 KiB | **6.04x** | 2 | 219 ms | 4.71 MiB/s |
| **Climate Station Data** | 20,000 | 3,051 KiB | 403 KiB | **7.57x** | 4 | 440 ms | 6.77 MiB/s |
| **Genomics Variants** | 8,000 | 946 KiB | 163 KiB | **5.80x** | 2 | 148 ms | 6.22 MiB/s |
| **Academic Metadata** | 5,000 | 825 KiB | 74 KiB | **11.13x** | 1 | 119 ms | 6.78 MiB/s |

### 3.3 On-Chain Verification Gas Costs

| Tree Depth | Records | Single Proof Gas | Contiguous Range Gas (8 Leaves) | Gas Savings |
|:---:|:---:|:---:|:---:|:---:|
| **4** | 16 | 6,200 | 7,850 | **84.2%** |
| **8** | 256 | 9,200 | 9,650 | **86.9%** |
| **12** | 4,096 | 12,200 | 11,450 | **88.3%** |
| **16** | 65,536 | 15,200 | 13,250 | **89.1%** |

---

## 4. Repository Structure

```text
research-blob-da/
├── contracts/                     # Solidity 0.8.24 smart contracts (Cancun target)
│   ├── DatasetRegistry.sol        # Core registry with multi-tx aggregation and citations
│   ├── interfaces/
│   │   └── IDatasetRegistry.sol   # Full interface, structs, events, errors
│   ├── libraries/
│   │   ├── BlobLib.sol            # Cancun blobhash reader and KZG precompile wrapper
│   │   ├── JsonFieldLib.sol       # Zero-copy numeric JSON parser for EVM calldata
│   │   └── MerkleLib.sol          # Position-binding single and range Merkle proofs
│   └── baselines/                 # Empirical baseline contracts
│       ├── CalldataSink.sol       # Raw calldata ingestion baseline
│       ├── SstoreArchive.sol      # SSTORE contract storage baseline
│       └── AnchorRegistry.sol     # Off-chain pointer (IPFS/URI) baseline
├── script/                        # Foundry deployment and bench scripts
│   ├── Deploy.s.sol               # Sepolia / mainnet deployment script
│   ├── PostBlobDataset.s.sol      # Type-3 transaction broadcaster script
│   └── BaselineBench.s.sol        # On-chain gas measurement script
├── test/                          # Foundry test suite (31 tests, 100% pass)
│   ├── DatasetRegistry.t.sol      # Full registry lifecycle tests
│   ├── MerkleLib.t.sol            # Merkle inclusion, depth, and range tests
│   ├── JsonFieldLib.t.sol         # JSON parser fuzz and edge-case tests
│   ├── Baselines.t.sol            # Gas baseline tests
│   └── Invariants.t.sol           # Invariant fuzz testing (16,384 calls across 256 runs)
├── python/                        # Production Python pipeline (Python 3.11+)
│   ├── canonical.py               # RFC 8785 JSON canonicalization and stream framing
│   ├── commitments.py             # Binary Merkle trees, range proofs, property summarizer
│   ├── encoder.py                 # Zstd compression, FE31/FE254 packing, blob headers
│   ├── decoder.py                 # Sidecar parsing, reassembly, cryptographic verification
│   ├── retriever.py               # Dual-backend (local cache with pruning & Beacon REST)
│   ├── generate_synthetic_data.py # Deterministic generation of 4 scientific datasets
│   ├── experiments.py             # 5 empirical benchmark experiment suites
│   └── plot_results.py            # High-resolution vector PDF & PNG figure generation
├── tests/                         # Pytest test suite (26 tests, 100% pass)
│   ├── test_canonical.py          # RFC 8785 sorting and stream framing tests
│   ├── test_commitments.py        # Position-binding Merkle proofs and property tests
│   ├── test_encoder_decoder.py    # FE31/FE254 roundtrips, multi-blob, BLS modulus
│   └── test_retriever.py          # Retrieval cache, pruning window simulation, errors
├── frontend-or-cli/               # CLI and TypeScript tooling
│   ├── rbda_cli.py                # Python CLI (encode, commit, verify, retrieve, claim, refute)
│   └── ts/                        # TypeScript viem SDK for testnet blob broadcasting
├── data/                          # Academic benchmark datasets
├── benchmarks/                    # Benchmark CSV results and generated figures
├── docs/                          # Comprehensive academic documentation
│   ├── RESEARCH.md                # Full conference research paper
│   ├── METHODOLOGY.md             # Experimental methodology and gas accounting
│   ├── REPRODUCIBILITY.md         # Step-by-step reproduction guide
│   └── figures/                   # Publication figures (Figure 1 through Figure 5)
├── .github/workflows/             # CI/CD workflows
│   ├── ci.yml                     # Full lint, build, test, and gas report
│   ├── benchmarks.yml             # Automated benchmark runner and artifact upload
│   ├── security.yml               # Slither static security analysis
│   └── deploy-sepolia.yml         # Manual Sepolia deployment workflow
├── foundry.toml                   # Foundry configuration (Cancun, via_ir=true)
├── requirements.txt               # Python dependencies
├── CITATION.cff                   # Academic citation metadata
└── LICENSE                        # MIT License
```

---

## 5. Quickstart Guide

### 5.1 Installation

```bash
# Clone repository
git clone https://github.com/ethereum-research/research-blob-da.git
cd research-blob-da

# Setup Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Compile smart contracts
forge build
```

### 5.2 Execute Test Suites

```bash
# Run Foundry tests (31 tests, fuzzing, invariants)
forge test -v

# Run Python tests (26 unit tests)
pytest -v tests
```

### 5.3 CLI Demonstration

```bash
# 1. Encode a 1.05 MiB ML training trace into 2 blobs with zstandard compression
python frontend-or-cli/rbda_cli.py encode \
  --input data/ml_training_trace.json \
  --out-dir data/encoded_demo \
  --cache

# 2. Verify blob sidecars against manifest
python frontend-or-cli/rbda_cli.py verify \
  --manifest data/encoded_demo/manifest.json \
  --blobs-dir data/encoded_demo

# 3. Retrieve and reconstruct original dataset
python frontend-or-cli/rbda_cli.py retrieve \
  --manifest data/encoded_demo/manifest.json \
  --out-file data/reconstructed.json

# 4. Generate on-chain property claim
python frontend-or-cli/rbda_cli.py claim \
  --input data/ml_training_trace.json \
  --key loss \
  --scale 2

# 5. Detect violation and generate refutation proof for false claim
python frontend-or-cli/rbda_cli.py refute \
  --input data/ml_training_trace.json \
  --key loss \
  --scale 2 \
  --claimed-min 18 \
  --claimed-max 200
```

---

## 6. Academic Paper and Documentation

- **[Full Research Paper](docs/RESEARCH.md):** Complete academic paper formatted for systems conferences.
- **[Experimental Methodology](docs/METHODOLOGY.md):** Formal hardware, statistical models, and gas formulas.
- **[Reproducibility Guide](docs/REPRODUCIBILITY.md):** Exact instructions for reproducing all results.

---

## 7. Citation

If you use `research-blob-da` or our empirical methodology in your research, please cite:

```bibtex
@article{research_blob_da_2026,
  title={Ephemeral Data Availability as an Academic Primitive: Verifiable Research Datasets via EIP-4844 Blobs},
  author={{Ethereum Protocol Research Group}},
  journal={arXiv preprint},
  year={2026},
  url={https://github.com/ethereum-research/research-blob-da}
}
```

---

## 8. License

This project is licensed under the [MIT License](LICENSE).
