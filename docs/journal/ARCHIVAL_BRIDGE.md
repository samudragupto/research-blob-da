# Dual-Horizon Archival Bridge

This document details the architectural design, implementation, and empirical verification of the **Dual-Horizon Archival Bridge** (`python/archival_bridge.py` and `contracts/ResearchArchiveRegistry.sol`).

---

## 1. Dual-Horizon Architecture

Scientific artifacts require two fundamentally different temporal availability guarantees:
1. **Horizon 1 (Temporary Publication & Consensus Commitment)**:
   - High-throughput, low-cost publication layer powered by Ethereum EIP-4844 blobs.
   - Retained by consensus clients for at least 4,096 epochs ($\approx 18.2\text{ days}$).
   - Guarantees that at block inclusion time, the data was made available to all validators and observers, anchored by cryptographic KZG commitments and on-chain `BLOBHASH` opcodes.
2. **Horizon 2 (Durable Scientific Preservation)**:
   - Indefinite retention layer powered by content-addressed storage (IPFS, Filecoin, Arweave, institutional CAS).
   - Retains exact canonical research bytes beyond the consensus pruning window.
   - Cryptographically bound to the Horizon 1 Ethereum anchor through content identifiers (CIDv1) and canonical SHA-256 / Keccak-256 roots.

---

## 2. On-Chain Extension Contract: ResearchArchiveRegistry

Contract path: `contracts/ResearchArchiveRegistry.sol`  
Test suite: `test/ResearchArchiveRegistry.t.sol` (5 passing Foundry tests)

### 2.1 Storage Optimization
Rather than storing multi-byte arbitrary IPFS CID strings in expensive EVM storage slots, `ResearchArchiveRegistry` stores a 32-byte hash of the content identifier (`bytes32 archivalCidHash`), packed into a compact two-slot struct:

```solidity
struct ArchivalRecord {
    StorageProvider provider;     // uint8 (IPFS=1, Filecoin=2, Arweave=3, LocalCAS=4)
    uint64 archivedAt;            // uint64 timestamp
    address archiver;             // address of submitting node
    bytes32 archivalCidHash;      // keccak256(cidString)
    bytes32 payloadSha256;        // sha256(canonicalPayload)
}
```

### 2.2 Invariant Guarantees
1. **Finality Dependency**: Archival registration reverts with `DatasetNotFinalized` if the dataset is still open in `DatasetRegistry`.
2. **Immutability of Binding**: Duplicate registrations for identical CID hashes revert with `RecordAlreadyExists`.
3. **Multi-Replica Redundancy**: Supports registering multiple independent storage backends (e.g., both IPFS and Arweave) for the same dataset identifier.

---

## 3. End-to-End Workflow and Expiry Simulation

1. **Publication**:
   - Canonicalizes research records into an RFC 8785 length-prefixed stream.
   - Compresses and encodes into 128 KiB EIP-4844 blobs (`FE31` packing).
   - Stores the exact canonical stream in the content-addressed store, deriving its CIDv1 identifier (`bafkreialof237plkudhqjdmmtzn7diwfcmbfgh6m5e3iog6lqtmlsgobfq`).
2. **Consensus Expiry Simulation**:
   - Deletes all cached blob sidecars from the local consensus cache (`data/journal/blob_cache/`).
   - Simulates the post-18.2-day state where Ethereum consensus clients return 404/410 for blob queries.
3. **Post-Expiry Reconstruction & Verification**:
   - Queries the dataset *exclusively* from the Content-Addressed Store by CID.
   - Reconstructs canonical records from raw bytes.
   - Verifies:
     - Canonical SHA-256 digest matches manifest ($100\%$).
     - Keccak-256 `contentHash` matches Ethereum state ($100\%$).
     - Record-level Merkle root matches on-chain commitment ($100\%$).

---

## 4. Empirical Performance Metrics

Data source: `benchmarks/journal-extension/archival/results.json`.

| Pipeline Stage | Operation | Latency (ms) | Verified Invariant |
|---|---|---|---|
| Step 1 | Canonicalization (RFC 8785) | 4.004 ms | Deterministic serialization |
| Step 2 | EIP-4844 Blob Encoding | 13.278 ms | Header formatting, FE31 packing |
| Step 3 | Archival Ingestion (CAS Put) | 0.837 ms | CIDv1 multihash derivation |
| Step 4 | Consensus Blob Purge | Instantaneous | 1 blob evicted from cache |
| Step 5 | Archival Retrieval (CAS Get) | 0.282 ms | Exact byte stream retrieved |
| Step 6 | Post-Expiry Cryptographic Verification | 7.633 ms | SHA-256, Content Hash, Merkle root |

---

## 5. Trust Assumptions and Residual Risks

1. **Storage Provider Persistence**:
   - The archival bridge does not magically keep IPFS nodes online. Durability requires active pinning contracts (e.g., Filecoin deals, Crust, pinata) or institutional repository replication.
2. **Cryptographic Integrity is Trustless**:
   - Even if an archival gateway is malicious or compromised, it *cannot* forge valid data: any modification of archival bytes will cause the SHA-256, Content Hash, or Merkle root checks to fail immediately during client-side verification.
