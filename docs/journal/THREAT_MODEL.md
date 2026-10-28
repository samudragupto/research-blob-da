# Security Threat Model and Adversarial Evaluation

This document defines the formal security model, trust assumptions, actor capabilities, and empirical adversarial evaluations of `research-blob-da`.

---

## 1. System Assets, Actors, and Trust Boundaries

### 1.1 Protected Assets
1. **Canonical Scientific Records**: Raw observational, tabular, or parameter records that researchers rely upon for exact numerical replication.
2. **Cryptographic Commitments**: On-chain Ethereum state representing datasets:
   - Blob Versioned Hashes (`BLOBHASH` opcode, version prefix `0x01`).
   - Whole-dataset Canonical Content Hash (`keccak256(canonical_stream)`).
   - Record-level Merkle Root (`MerkleLib.sol` binary tree).
   - Off-chain Manifest Digest (`metadataHash`).
3. **Dispute Invariants**: Optimistic numeric range and summary claims registered in `DatasetRegistry`.
4. **Durable Archival Bindings**: Content identifiers (`archivalCidHash`) registered in `ResearchArchiveRegistry`.

### 1.2 Threat Actors
- **Malicious Publisher**: Seeks to publish corrupt, truncated, or falsified research artifacts while claiming valid publication.
- **Malicious Network Peer / RPC Node**: Modifies blob sidecar bytes, permutes chunk order, drops sidecars, or injects duplicates.
- **Corrupted Archival Provider**: An external IPFS gateway, Filecoin storage provider, or cloud bucket that serves altered bytes.
- **Frivolous / Sybil Challenger**: Submits invalid fraud refutations to attempt contract fund exhaustion or state griefing.

### 1.3 Trust Assumptions
- **Ethereum L1 Consensus**: Security of Ethereum proof-of-stake consensus, KZG point evaluation precompile (`0x0A`), and `BLOBHASH` execution opcode.
- **Cryptographic Primitives**: Preimage and collision resistance of Keccak-256 and SHA-256; discrete log hardness in BLS12-381.
- **Availability Asymmetry**: We explicitly assume that *cryptographic mechanisms can detect and refute tampering, but cannot force a pruned or offline node to serve data*. Data availability failure is an operational state that must be mitigated by redundant archival backends.

---

## 2. Adversarial Test Matrix (15 Scenarios)

Data source: `benchmarks/journal-extension/security/results.json` and `tests/test_adversarial.py`.

| ID | Threat Scenario | Adversary Capability | Detection Mechanism | Detection Layer | Test Outcome | Residual Risk & Recovery Path |
|---|---|---|---|---|---|---|
| **SEC-01** | Modified Blob Bytes | Mutates bytes in transit | Zstandard frame checksum failure or KZG commitment mismatch | Client Decoder | **DETECTED & REJECTED** | Zero; corrupt blob sidecar rejected before decompression. |
| **SEC-02** | Modified Canonical Payload | Alters 1 bit of decompressed data | `keccak256(stream) != contentHash` | On-Chain & Client | **DETECTED & REJECTED** | None; Keccak-256 collision resistance prevents acceptance. |
| **SEC-03** | Incorrect Metadata | Claims inflated record count | Deserialized count != registered `recordCount` | Client Reconstructor | **DETECTED & REJECTED** | None; client flags discrepancy and refuses verification. |
| **SEC-04** | Omitted Record | Drops 1 record from dataset | Recomputed Merkle root != onchain `recordsRoot` | Smart Contract & Client | **DETECTED & REJECTED** | None; binary leaf tree position binding detects omission. |
| **SEC-05** | Reordered Records | Permutes record sequence | Leaf index permutation alters root digest | Smart Contract `MerkleLib` | **DETECTED & REJECTED** | None; position-binding domain separation prevents reordering. |
| **SEC-06** | Missing Blob in Multi-Blob | Drops 1 of N blob sidecars | Header `blob_count` != received sidecars | Client Decoder | **DETECTED & REJECTED** | Data temporarily unavailable; recovery requires querying alternative peer. |
| **SEC-07** | Reordered Blobs | Swaps chunk sequence | Header `blob_index` sequential assertion fails | Client Decoder | **DETECTED & REJECTED** | None; reordered chunks rejected during assembly. |
| **SEC-08** | Duplicate Blob Insertion | Injects duplicate blob chunk | Duplicate `blob_index` rejected by assembler | Client Decoder | **DETECTED & REJECTED** | None; duplicate indices discarded. |
| **SEC-09** | Partial Multi-Tx Abandonment | Abandons dataset after 1 tx | Dataset remains in `Open` state; cannot finalize | Smart Contract `DatasetRegistry` | **DETECTED & REJECTED** | Publisher loses gas; unfinalized dataset never certified. |
| **SEC-10** | False Statistical Claim | Posts invalid numeric bound | Honest observer submits Merkle proof of violation | Smart Contract Dispute Game | **DETECTED & REFUTED** | Requires $\ge 1$ honest challenger within 18.2-day window. |
| **SEC-11** | Unavailable Sidecar | Consensus pruning or RPC drop | HTTP 404/410 / timeout triggers `BlobPrunedError` | Retriever Module | **DETECTED & MITIGATED** | Fallback to Dual-Horizon Archival Bridge. |
| **SEC-12** | Corrupted Archival Backend | Gateway alters archival bytes | SHA-256 and content hash check fail against anchor | `DualHorizonBridge` Client | **DETECTED & REJECTED** | None; client refuses to accept altered archival payload. |
| **SEC-13** | Archival CID Substitution | Binds unrelated CID on-chain | Finalization check & client payload hash match | `ResearchArchiveRegistry` | **DETECTED & REJECTED** | Fake CID ignored by clients if bytes do not hash to `contentHash`. |
| **SEC-14** | Encryption Key Loss | Key forgotten by researcher | AEAD authentication tag failure | Client Decryptor | **DETECTED & ISOLATED** | Irreversible data loss if key lost; consensus commitments remain unviolated. |
| **SEC-15** | Registry Metadata Mismatch | Modifies off-chain JSON schema | `keccak256(manifest) != metadataHash` | Client Manifest Validator | **DETECTED & REJECTED** | None; manifest mismatch detected during initial handshake. |

---

## 3. Empirical Security Invariants

1. **Detection Rate**: All 15 implemented adversarial test scenarios were detected by the corresponding verification checks (15/15 implemented scenarios detected). These results demonstrate that the specified checks function as designed for the tested scenarios. They do not constitute a formal security proof or a complete coverage of possible attacks.
2. **False Positive Rate**: 0/15 false positives in clean-state evaluation.
3. **Availability Honesty**: The system explicitly acknowledges that data availability cannot be cryptographically summoned once pruned; availability is preserved through verified dual-horizon replication.
