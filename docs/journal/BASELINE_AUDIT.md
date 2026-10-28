# Baseline Audit: research-blob-da v0.1.0

This audit establishes the frozen state, verified baselines, and empirical boundaries of `research-blob-da` as released at tag `v0.1.0` prior to journal extension.

## 1. Commit and Release Provenance

- **Repository**: `samudragupto/research-blob-da` (https://github.com/samudragupto/research-blob-da)
- **Author**: Arrhat Nag (`samudragupto`)
- **Baseline Git Commit (`origin/main`)**: `ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1`
- **Release Tag**: `v0.1.0` (`0b523e756d5421e640f4545dc3900e3081fd0d6d`)
- **Peeled Release Commit**: `428c7898dd5e5078ad466fa6955058936b33aac3`
- **Official Release URL**: https://github.com/samudragupto/research-blob-da/releases/tag/v0.1.0

## 2. Test Baseline Verification

Executed on 2026-10-28:

- **Smart Contract Test Suite (Foundry / Forge v1.5.1-stable)**:
  - `test/Baselines.t.sol`: 4 passed
  - `test/DatasetRegistry.t.sol`: 9 passed
  - `test/JsonFieldLib.t.sol`: 11 passed (including fuzz test with 1,024 runs)
  - `test/MerkleLib.t.sol`: 6 passed (including fuzz test with 1,024 runs)
  - `test/Invariants.t.sol`: 1 passed (stateful invariant test: 256 runs, 16,384 calls, 0 reverts)
  - **Total Forge Tests**: 31 passed, 0 failed, 0 skipped.
- **Python Test Suite (Pytest v9.1.1)**:
  - `tests/test_canonical.py`: 5 passed
  - `tests/test_commitments.py`: 5 passed
  - `tests/test_consistency_table.py`: 2 passed
  - `tests/test_cost_model.py`: 12 passed
  - `tests/test_encoder_decoder.py`: 9 passed
  - `tests/test_real_data.py`: 5 passed
  - `tests/test_retriever.py`: 7 passed
  - **Total Pytest Tests**: 45 passed, 0 failed, 0 skipped.
- **Combined Test Count**: 76 tests passing.

## 3. Frozen Benchmark Manifest Audit

Manifest location: `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json`  
Freeze Timestamp: `2026-10-27T16:28:29Z`

All 7 frozen benchmark artifacts were re-verified via SHA-256:

| Artifact File | Expected SHA-256 Hash | Audit Status |
|---|---|---|
| `benchmarks/cost_comparison_uncompressed.csv` | `833ce76fb0df34b40f3c72f9f1f6fd19589e691ec3ebed8f3fa7e16c1b318224` | Verified (Exact Match) |
| `benchmarks/cost_comparison_compressed.csv` | `c7f3c36590ef2984a4c28fdba70d2341070d733a63633fdd7c48168c2fbd4171` | Verified (Exact Match) |
| `benchmarks/encoding_efficiency.csv` | `a71a6464a06c70f875f23ce3910d68c2f533f19df481422bf8087c45d6db061b` | Verified (Exact Match) |
| `benchmarks/fee_sensitivity.csv` | `61c9379a2dd4325f67dd2db05c6c3ee6e64fa2eacb64935435a2d5f829387ff4` | Verified (Exact Match) |
| `benchmarks/calldata_eip7623_sensitivity.csv` | `03f86bcbbe3b43b2e3804267ec2cef85eae89d99062b4426397270642fe445ee` | Verified (Exact Match) |
| `benchmarks/blob_capacity_limits.csv` | `c766f6f38713ea66e052ae1e91e2d9569f3dcb7974fdedbe1e4cd0e95024b52a` | Verified (Exact Match) |
| `benchmarks/generated_tables.md` | `0d06f83ae5c788d60318f60d0f18da24d4f68cc9b672c0f8dfc1eee65836f233` | Verified (Exact Match) |

Frozen benchmark baseline measurement:
- Real OpenAlex Encoding Latency: `11.7 ms ± 0.2 ms (N=10)` (Mean: 11.67 ms, Std: 0.2 ms).

## 4. Deployed Network Artifacts (Ethereum Sepolia Testnet)

- **Network Chain ID**: 11155111
- **DatasetRegistry Deployment**:
  - Address: [`0x238dE56E52A3F6C6708952052e6a20E5102b4d5b`](https://sepolia.etherscan.io/address/0x238dE56E52A3F6C6708952052e6a20E5102b4d5b#code)
  - Verification Status: Verified Source on Etherscan (Solidity v0.8.24, Cancun EVM, 200 optimization runs)
  - Deployment Tx: `0xa55af2b2a6ec29cc706bd8e5ebc166d6ae3130002c183f7ebdbb8186cc834751` (Block 12006103)
- **Live EIP-4844 Blob Transaction**:
  - Tx Hash: `0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea` (Block 12006195)
  - Dataset ID: `0x4f7b50bd684170f2c427d8975ee6478fadbc46918b764f1e8a4915374bf9d29b`
  - KZG Versioned Hash: `0x010e6c7880a790abbedd746b98b713b5780e8e662d9f57f31cc51671b01faf11`

## 5. Local Reconstruction Evidence and Boundaries

As documented in `deployments/sepolia_retrieval_verification.json`:
- Local sidecar byte integrity was verified against the Sepolia KZG versioned hash on 2026-10-27T16:28:44Z.
- Canonical payload SHA-256 (`20b411d51a66ff641cb48f6572eb88f9184852ab16d56d10f844e31821cf02a3`) was verified.
- Public Beacon API sidecar queries failed or timed out during the initial demonstration, establishing the empirical reality that public Beacon endpoint availability is inconsistent without dedicated archival nodes.

## 6. Baseline Limitations Addressed in Journal Extension

1. **Empirical Depth**: v0.1.0 evaluated a single on-chain transaction. A journal-grade study requires systematic repeated network submission and retrieval harnesses with spending safety controls.
2. **Retrieval Infrastructure Evaluation**: The public consensus endpoint retrieval failure in v0.1.0 must be expanded into a structured retrieval study distinguishing Beacon API, archival provider, and local cache.
3. **Dataset Diversity**: v0.1.0 used two datasets (one real OpenAlex corpus, one synthetic ML trace). The journal extension introduces five distinct dataset classes (real OpenAlex, real climate sensors, real ML training logs, synthetic scaling traces, and incompressible controls).
4. **Archival Bridge Implementation**: The dual-horizon model (separating temporary blob publication from durable external preservation) is implemented as a tested, content-addressed archival subsystem.
5. **Guarantee-Aware Baselines**: Calldata, SSTORE, IPFS, Filecoin, Arweave, and cloud storage must be analyzed across durability, verification, and payer models rather than simplified cost-per-byte comparisons.
6. **Formal Security Analysis**: Comprehensive threat modeling with adversarial tests evaluating corruption, omission, reordering, duplicate blobs, and claim tampering.
