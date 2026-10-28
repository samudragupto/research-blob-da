# Threats to Validity

This document outlines the potential threats to construct, internal, external, and conclusion validity in the `research-blob-da` empirical evaluation, along with specific mitigation strategies implemented.

---

## 1. Construct Validity

### Threat 1.1: Equating KZG Commitment Verification with Long-Term Data Availability
- **Risk**: An observer could conflate cryptographic proof that blob data matches an on-chain versioned hash (`BLOBHASH`) with a guarantee that the underlying data will remain retrievable indefinitely.
- **Mitigation**: The manuscript explicitly documents that KZG commitments prove commitment consistency, *not* perpetual availability. Blobs are defined as a temporary publication layer (consensus pruned after $\approx 18\text{ days}$), necessitating external archival layers (e.g., content-addressed storage) for durable scientific preservation.

### Threat 1.2: Conflating Local-Cache Reconstruction with Public Network Retrieval
- **Risk**: Verifying that a local blob sidecar reconstructs a dataset could be misinterpreted as proving that public consensus endpoints successfully delivered the sidecar over the network.
- **Mitigation**: The evaluation strictly distinguishes three retrieval source types: `beacon_api`, `archival_provider`, and `local_cache`. Local reconstruction is reported solely as proof of decoding and commitment correctness.

### Threat 1.3: Simplified Baseline Cost Comparisons
- **Risk**: Comparing raw USD costs of blobs, calldata, SSTORE, IPFS, and cloud storage without accounting for differing durability, consensus anchoring, and availability guarantees introduces misleading cost-per-byte rankings.
- **Mitigation**: We implement a guarantee-aware evaluation framework (`docs/journal/GUARANTEE_AWARE_BASELINES.md`) that documents availability period, consensus verification, permanence, retrieval guarantees, and typical payer for each baseline.

---

## 2. Internal Validity

### Threat 2.1: Cache State Distortion (Cold vs. Warm Cache)
- **Risk**: File system page caching and JIT compilation could artificially depress latency measurements or introduce high variance.
- **Mitigation**: All local timing benchmarks enforce a strict 2-iteration warm-up protocol. Where cold-cache results are reported, file buffers are systematically flushed and isolated.

### Threat 2.2: Operating System and Background Interference
- **Risk**: Background processes, CPU thermal throttling, and garbage collection pauses can skew tail latencies.
- **Mitigation**: Automated environment capture logs hardware characteristics, CPU model, core counts, and system memory. Experiments execute across multiple trials ($N=10$) with non-parametric bootstrap confidence intervals and median/IQR reporting rather than reliance solely on the arithmetic mean.

### Threat 2.3: Small-Sample Distortion of Extreme Percentiles
- **Risk**: Calculating 99th percentile ($p_{99}$) from sample sizes $< 100$ leads to statistically unsound estimates.
- **Mitigation**: $p_{99}$ is reported only when $N \ge 100$; smaller sample sizes restrict reporting to median, IQR, and $p_{95}$ with explicit sample size disclosures.

---

## 3. External Validity

### Threat 3.1: Testnet vs. Mainnet Market Dynamics
- **Risk**: Sepolia testnet execution and blob gas markets operate with different validator distributions, block proposal latencies, and fee congestion compared to Ethereum mainnet.
- **Mitigation**: Network experiments capture actual execution gas and blob gas units used, which are identical between Sepolia and Mainnet. Economic costs are modelled analytically across a wide spectrum of mainnet gas prices ($5$ to $100\text{ gwei}$) and blob fees ($1$ to $500\text{ gwei}$) rather than relying solely on testnet fee environments.

### Threat 3.2: Generalizability Across Diverse Scientific Data Modalities
- **Risk**: Compression ratios and packing throughput observed on JSON metadata may not represent binary sensor data, dense numerical tensors, or images.
- **Mitigation**: The benchmark corpus expands across five distinct dataset classes: scholarly metadata (OpenAlex JSON), climate/environmental sensor observations (tabular/CSV), ML training logs (JSONL), synthetic scaling payloads, and an incompressible binary negative control.

### Threat 3.3: Future Protocol Upgrades (Pectra, PeerDAS, Blob Parameter Changes)
- **Risk**: Upcoming Ethereum hard forks (Pectra, PeerDAS / EIP-7594, EIP-7623, EIP-7691) will modify blob count limits, target capacities, and calldata gas floors.
- **Mitigation**: We model Cancun baseline parameters ($3$ target, $6$ max blobs per block) alongside Pectra modifications ($6$ target, $9$ max blobs; EIP-7623 calldata floor of $40\text{ gas/token}$), explicitly documenting the validity boundaries of each regime.

---

## 4. Reliability and Reproducibility

- **Fixed Seeds**: All deterministic generation and bootstrap procedures use seed `42`.
- **Pinned Dependencies**: Python requirements and Foundry versions are pinned.
- **Immutability of Historical Evidence**: v0.1.0 frozen benchmarks remain immutable; all journal extensions are isolated in versioned directories.
