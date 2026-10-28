# Research Questions and Testable Hypotheses

This document formalizes the scientific foundation of `research-blob-da`, defining six central research questions (RQ1–RQ6), testable null and alternative hypotheses, operational metrics, and the experimental evaluations designed to address them.

---

## Central Research Question

> **Can Ethereum blobs serve as a temporary, verifiable publication layer for reproducible research artifacts, and what additional infrastructure is required to convert temporary data availability into durable scientific preservation?**

---

## RQ1: Feasibility

### Question
Can structured scientific research artifacts be deterministically encoded, committed, published, reconstructed, and verified through EIP-4844 blobs without loss of integrity?

### Hypotheses
- **$H_{1,0}$ (Null)**: An end-to-end pipeline cannot deterministically reconstruct canonical scientific records from raw blob sidecars without bit-level divergence or loss of cryptographic verifiability against EVM-anchored commitments.
- **$H_{1,1}$ (Alternative)**: An end-to-end pipeline implementing RFC 8785 canonical serialization, field element modulus packing (`FE31`), and binary Keccak-256 Merkle trees deterministically reconstructs scientific records with 100% bitwise parity and verifies against on-chain blob versioned hashes (`BLOBHASH`) and Merkle roots.

### Metrics
- Bitwise reconstruction parity (exact SHA-256 match between original canonical payload and decoded payload).
- On-chain `BLOBHASH` opcode consistency matching KZG commitments.
- On-chain Merkle inclusion proof verification success rate ($100\%$).
- On-chain fraud refutation dispute game execution fidelity.

### Evaluation Method
- Local reconstruction unit tests (`tests/test_encoder_decoder.py`, `tests/test_commitments.py`).
- Fuzz and stateful invariant testing in Foundry (`test/Invariants.t.sol`, `test/JsonFieldLib.t.sol`).
- Empirical testnet verification on Sepolia deployment (`0x238dE56E52A3F6C6708952052e6a20E5102b4d5b`).

---

## RQ2: Economics

### Question
Under what execution-fee, blob-fee, compression, and dataset-size conditions are blobs cheaper than standard calldata for temporary publication?

### Hypotheses
- **$H_{2,0}$ (Null)**: Due to transaction execution overhead and blob quantization waste, blobs do not offer a statistically or economically significant cost reduction compared to standard EVM calldata across realistic payload sizes.
- **$H_{2,1}$ (Alternative)**: Blobs provide a statistically and economically significant cost reduction (exceeding $10\times$ for payloads $> 100\text{ KiB}$) over standard calldata across prevailing execution fee regimes ($\ge 10\text{ gwei}$) whenever the blob base fee remains below an analytically defined break-even threshold ($B^*$).

### Metrics
- Total transaction cost in USD (at $3,000 USD/ETH) across gas regimes.
- Break-even blob base fee ($B^*$) in gwei:
  $$B^* = \frac{G_{\text{call}} \cdot E - G_{\text{exec}} \cdot E}{N_{\text{blobs}} \cdot 131,072}$$
- Cost reduction ratio: $\text{Cost}_{\text{calldata}} / \text{Cost}_{\text{blob}}$.
- Packing efficiency and quantization overhead ($1 - \text{UsableBytes}/\text{AllocatedBlobBytes}$).

### Evaluation Method
- Analytical parameter sweep across 1 to 50 MiB, execution base fees (5 to 100 gwei), and blob base fees (1 to 500 gwei).
- Multi-dataset cost comparison across real OpenAlex records, climate sensor observations, ML training logs, synthetic scaling payloads, and incompressible controls.
- Sensitivity analysis under EIP-7623 execution gas floor scenarios.

---

## RQ3: Performance and Scalability

### Question
How do dataset type, payload size, compression level, framing strategy, and packing strategy affect preparation latency, throughput, memory consumption, packing efficiency, and verification latency?

### Hypotheses
- **$H_{3,0}$ (Null)**: Preparation and verification latencies scale superlinearly with dataset size, rendering client-side preparation of multi-megabyte research artifacts computationally impractical on standard commodity hardware.
- **$H_{3,1}$ (Alternative)**: Preparation and verification latencies scale linearly ($O(N)$) with canonical payload size, maintaining encoding throughput $> 20\text{ MiB/s}$ and sub-second verification latency on commodity workstations.

### Metrics
- Preparation latency (canonicalization, compression, `FE31` packing, KZG commitment generation).
- Client memory consumption (peak resident set size).
- Reconstruction latency and throughput ($\text{MiB/s}$).
- Smart contract verification gas costs (Merkle inclusion proof, record checkpointing).

### Evaluation Method
- Local benchmark matrix evaluating payload sizes: $100\text{ KiB}$, $1\text{ MiB}$, $5\text{ MiB}$, $20\text{ MiB}$, and $50\text{ MiB}$.
- Compression ablation: uncompressed, zstd level 1, level 3, level 9, level 19.
- Modulus-safe packing ablation: `FE31` (31 bytes per 32-byte field element) versus bit-packing (`FE254b`).
- Commitment ablation: Canonical content hash only vs. Content hash + Merkle tree vs. Property claims.

---

## RQ4: Availability Window and Retrieval Infrastructure

### Question
How reliably can blob sidecars be retrieved from public consensus endpoints across time within the standard availability window, and what failure modes characterize public consensus infrastructure?

### Hypotheses
- **$H_{4,0}$ (Null)**: Public consensus layer Beacon API endpoints offer high-reliability ($> 99\%$) blob sidecar retrieval without rate limiting, authentication, or query drops throughout the minimum 4,096-epoch ($\approx 18\text{ days}$) availability window.
- **$H_{4,1}$ (Alternative)**: Public consensus endpoints exhibit significant retrieval instability, rate-limiting, and frequent sidecar query failures, demonstrating that reliable data retrieval requires dedicated RPC access or secondary archival gateways.

### Metrics
- Endpoint-specific retrieval success rate: $S = N_{\text{success}} / N_{\text{attempts}}$.
- Retrieval latency distribution (median, p95, p99).
- Success rate as a function of age since block inclusion (0h, 1h, 24h, 7d, 18d).
- Error taxonomy: HTTP 404 (pruned/absent), HTTP 429 (rate-limited), HTTP 504 (timeout), connection reset, corrupt sidecar.

### Evaluation Method
- Multi-provider retrieval harness querying configured public Beacon API endpoints, archival providers, and local caches.
- Nonce/timestamp-scheduled retrieval logging into machine-readable JSONL records.

---

## RQ5: Durability and Dual-Horizon Archival Bridge

### Question
Can an external archival bridge preserve exact research bytes beyond the transient blob availability window while retaining cryptographic verifiability against Ethereum-anchored commitments?

### Hypotheses
- **$H_{5,0}$ (Null)**: An archival bridge cannot bind external durable storage providers (e.g., IPFS/Filecoin/local content-addressed archives) to Ethereum blob commitments without introducing trusted third parties or breaking cryptographic provenance.
- **$H_{5,1}$ (Alternative)**: A content-addressed archival bridge linking canonical payload SHA-256 and Merkle roots to durable CIDs enables bit-for-bit dataset reconstruction and EVM-verifiable integrity proofs after blobs have been pruned from consensus nodes.

### Metrics
- Post-expiry reconstruction fidelity (bitwise match to original canonical payload).
- Archival upload latency, retrieval latency, and verification latency.
- Smart contract gas overhead for registering and verifying archival content identifiers (`ResearchArchiveRegistry.sol`).

### Evaluation Method
- Implementation and testing of `python/archival_bridge.py` and `contracts/ResearchArchiveRegistry.sol`.
- Simulated blob expiry test: purge local blob sidecar cache, retrieve exclusively from content-addressed archival store, and verify all cryptographic assertions.

---

## RQ6: Security and Tamper Resistance

### Question
How effectively does the multi-tiered commitment system detect modified, omitted, reordered, partially published, falsely described, or unavailable research records?

### Hypotheses
- **$H_{6,0}$ (Null)**: Adversarial mutations of research records (e.g., bit flips, record deletion, reordering, fraudulent statistical claims) can evade detection by the on-chain registry or off-chain reconstruction pipeline.
- **$H_{6,1}$ (Alternative)**: The combination of blob versioned hashes, canonical payload SHA-256, record-level Merkle proofs, and optimistic dispute games detects $100\%$ of record corruptions, omissions, reorderings, and false property claims.

### Metrics
- Adversarial detection rate across defined attack scenarios ($100\%$).
- False positive rate ($0\%$).
- Gas cost and proof size for on-chain fraud refutations.

### Evaluation Method
- Systematic adversarial test suite executing 15 threat scenarios (`benchmarks/journal-extension/security/results.json`, `tests/test_adversarial.py`).
- Foundry dispute game simulation tests (`test/DatasetRegistry.t.sol`).
