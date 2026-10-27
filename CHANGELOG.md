# Changelog

All notable changes to `research-blob-da` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-27

### Added
- **Canonical Serialization Engine (`python/canonical.py`):** Length-prefixed record serialization adhering to RFC 8785 canonical JSON, guaranteeing deterministic byte streams across heterogeneous platforms.
- **EIP-4844 Blob Encoder (`python/encoder.py`):** Multi-blob chunking engine supporting conservative 31-byte field-element packing (`FE31`) and dense 254-bit packing (`FE254`), with domain-separated 31-byte headers in Field Element 0.
- **Cryptographic Commitments (`python/commitments.py`):** Keccak-256 binary Merkle tree implementation with single-leaf inclusion proofs and contiguous batch range proofs.
- **EVM Smart Contracts (`contracts/`):**
  - `DatasetRegistry.sol`: Anchors datasets, reads `BLOBHASH` inside Type-3 transactions, manages optimistic property claims, and records permissionless attestations.
  - `libraries/BlobLib.sol`: EIP-4844 constants, versioned hash validation, and retention calculations.
  - `libraries/MerkleLib.sol`: Efficient on-chain single-proof and range-proof verification.
  - `libraries/JsonFieldLib.sol`: Pure-Yul assembly parser for ASCII numeric floating-point fields.
  - `baselines/`: Exact comparison baseline contracts (`CalldataSink.sol`, `SstoreArchive.sol`, `AnchorRegistry.sol`).
- **Real Academic Dataset Harvester (`python/fetch_real_data.py`):** Deterministic OpenAlex API client with committed offline fixture (`data/real_academic_openalex.json`) and SHA-256 checksum manifest.
- **Formal Cost and Capacity Models (`python/cost_model.py`):** Exact mathematical modeling of usable blob payload bytes, official EIP-7623 calldata floor calculations, multi-block SSTORE extrapolations, and fee sensitivity grids.
- **Automated Consistency Checker (`python/check_consistency.py`):** Validates all documented headline figures against runnable CSV outputs and enforces a strict zero-emoji policy.

### Changed
- **Disaggregated Cost Reporting:** Separated all cost benchmarks into Table A (Theoretical Uncompressed Cost Baseline) and Table B (Measured Compressed Dataset Results).
- **Blob Count Reconciliation:** Formally documented why a 1.0 MiB theoretical uncompressed dataset requires 9 blobs (based on 126,945 usable body bytes per blob), whereas the 1,056 KiB ML training trace compresses to 174.9 KiB and requires only 2 blobs.
- **SSTORE Relabeling:** Relabeled all contract storage metrics as "Theoretical SSTORE Extrapolation (Not Executable in a Single Block)", documenting exact 30M gas limit block counts (e.g., 25 full blocks for 1.0 MiB).
- **EIP-7623 Isolation:** Removed obsolete heuristic claims (such as 32 gas/byte) from headline summaries and created a dedicated post-Pectra sensitivity analysis.
- **TypeScript CLI Alignment:** Corrected `frontend-or-cli/ts/src/blob_tx.ts` ABI and parameter serialization to match `DatasetRegistry.sol`.

### Verified
- 40 passing Python unit tests covering canonical serialization, encoding, decoding, commitments, real dataset parsing, and cost models.
- 31 passing Foundry tests covering contract registration, range proofs, property refutation, and baselines.
- Reproduction scripts regenerating all 6 benchmark CSV files and 6 publication figures (PNG and PDF).

### Known Limitations
- **Ephemeral Blob Retention:** Blob sidecars are pruned by consensus clients after approximately 4096 epochs (~18.2 days). Permanent archival requires external indexers or IPFS/Filecoin pinning.
- **Block and Transaction Limits:** Under current Cancun parameters (max 6 blobs per transaction), datasets exceeding 761 KiB compressed require multi-transaction submissions.
