# Data Management Plan

This Data Management Plan (DMP) defines the governance, provenance, storage, verification, and dissemination lifecycle for all datasets and experimental artifacts in the `research-blob-da` journal extension.

---

## 1. Data Governance and FAIR Principles

The project adheres to the **FAIR Data Principles**:
- **Findability**: All datasets and experimental manifests are indexed with unique identifiers, persistent file paths, and cryptographically verified SHA-256 digests.
- **Accessibility**: Open-source release via public GitHub repository, verifiable Sepolia smart contracts, and scheduled archival via Zenodo.
- **Interoperability**: Data payloads utilize standardized canonical serialization (RFC 8785 JSON) and standard Zstandard (RFC 8878) compression.
- **Reusability**: Open licenses (MIT for code, CC0 / CC-BY for data fixtures) and complete environment manifests ensure deterministic re-execution.

---

## 2. Dataset Classification and Provenance

The journal extension manages five distinct dataset corpora:

| Dataset Class | Format | Primary Source / Provenance | License | Redirection / Storage Strategy |
|---|---|---|---|---|
| 1. Scholarly Works | JSON | OpenAlex API (`api.openalex.org/works`) | CC0 1.0 Universal | Pinned canonical fixture in `data/` |
| 2. Climate & Environmental Sensors | CSV / JSON | NOAA GSOD / Global Atmospheric Sensor Network | Public Domain / CC0 | Canonical fixture in `data/journal/` |
| 3. ML Training Traces | JSONL | Public ML benchmark training logs (PyTorch / WandB trace) | MIT / Apache 2.0 | Canonical fixture in `data/journal/` |
| 4. Deterministic Synthetic Scaling | JSON | Generated via deterministic PRNG (Seed `42`) | MIT | Synthetic generator script |
| 5. Incompressible Negative Control | Binary | High-entropy pseudo-random bytes (Seed `42`) | MIT | Deterministic PRNG stream |

---

## 3. Storage Architecture and Directory Layout

All data and benchmarking outputs are partitioned to strictly preserve historical release baselines:

```text
research-blob-da/
|-- data/
|   |-- openalex_works_500.json            # Frozen v0.1.0 OpenAlex fixture
|   \-- journal/                           # Journal extension fixtures
|       |-- climate_sensors_sample.json
|       |-- ml_training_trace.jsonl
|       \-- manifests/                     # Machine-readable checksum manifests
|           |-- dataset_provenance.json
|           \-- checksums.sha256
|-- benchmarks/
|   |-- FROZEN_BENCHMARKS_v0.1.0.json      # Frozen v0.1.0 baseline manifest
|   \-- journal-extension/                 # Journal-grade evaluation records
|       |-- local/                         # Raw CSV/JSONL micro-benchmarks
|       |-- network/                       # Sepolia transaction receipts & pending logs
|       |-- retrieval/                     # Multi-provider retrieval logs
|       |-- archival/                      # Content-addressed bridge traces
|       |-- security/                      # Threat model scenario logs
|       |-- figures/                       # Publication-ready PNG/PDF figures
|       \-- manifests/                     # Environment and baseline manifests
```

---

## 4. Integrity and Cryptographic Verification

1. **Pre-Ingestion Checksumming**: Every raw input file is hashed with SHA-256 upon retrieval and recorded in `data/journal/manifests/dataset_provenance.json`.
2. **Canonical Transformation**: JSON records undergo RFC 8785 deterministic ordering:
   - Lexicographical key sorting (UTF-16 code unit order).
   - Strict whitespace elimination (` separators=(',', ':') `).
   - Normalized IEEE 754 float representation.
3. **Commitment Binding**: Canonical payloads generate dual commitments:
   - Canonical Content SHA-256 hash.
   - Binary Keccak-256 Merkle root over discrete record boundaries.
   - KZG Versioned Hashes (`0x01 || SHA256(KZG_Commitment)[1:]`).

---

## 5. Ethics, Licensing, and PII Controls

- **No Personally Identifiable Information (PII)**: All datasets represent aggregate scientific metadata, physical environmental telemetry, or simulated training loss traces. No human subject data or PII is collected or processed.
- **Licensing Compliance**: Only datasets with explicit open terms permitting academic redistribution are committed as fixtures.
- **Secret and Credential Sanitation**: No API keys, RPC endpoints with embedded basic auth, or private keys are written to repository files or manifests. All environment captures automatically sanitize user home paths and credentials.

---

## 6. Long-Term Preservation and Archival

Upon publication of the journal version:
1. A snapshot of the repository, including data manifests and compiled PDF paper, will be deposited in Zenodo under a dedicated DOI.
2. The dual-horizon archival bridge provides a reference implementation for pinning the canonical dataset onto IPFS/Filecoin with Ethereum-anchored verification roots.
