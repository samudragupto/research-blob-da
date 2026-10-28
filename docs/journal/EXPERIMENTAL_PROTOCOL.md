# Journal Experimental Protocol

This document establishes the experimental protocol for all local, network, retrieval, and archival evaluations conducted in the `research-blob-da` journal extension.

---

## 1. Experimental Variables

### 1.1 Independent Variables
1. **Dataset Class**:
   - Real Scholarly Works (OpenAlex API metadata, JSON).
   - Real Climate / Environmental Sensor Observations (NOAA Global Surface Summary of the Day / Urban air quality, CSV/JSON).
   - Real Machine Learning Training Traces (loss, gradient norms, step metrics, JSONL).
   - Deterministic Synthetic Structured Scaling Payloads (controlled schema, JSON).
   - Incompressible Binary Negative Control (high-entropy PRNG pseudo-random bytes).
2. **Canonical Payload Size**:
   - $100\text{ KiB}$ ($102,400\text{ bytes}$)
   - $1\text{ MiB}$ ($1,048,576\text{ bytes}$)
   - $5\text{ MiB}$ ($5,242,880\text{ bytes}$)
   - $20\text{ MiB}$ ($20,971,520\text{ bytes}$)
   - $50\text{ MiB}$ ($52,428,800\text{ bytes}$, multi-transaction dataset)
3. **Compression Algorithm & Level**:
   - Uncompressed (raw canonical payload)
   - Zstandard (RFC 8878): Level 1 (fastest), Level 3 (default balanced), Level 9 (high compression), Level 19 (ultra compression)
4. **Modulus-Safe Field Element Packing Strategy**:
   - `FE31`: 31 usable data bytes per 32-byte BLS12-381 field element (top byte $0\text{x}00$, guaranteed $< p$, $3.125\%$ overhead).
   - `FE254b`: Bit-packed 254-bit packing (31.75 bytes equivalent per field element, top 2 bits $0\text{b}00$, $0.781\%$ overhead).
5. **Commitment Architecture**:
   - Canonical Content Hash only (SHA-256).
   - Content Hash + Binary Keccak-256 Merkle Tree over records.
   - Full Metadata + Property Claims (range commitments, summary statistics).
6. **Network & Fee Regimes**:
   - Execution base fee: $5, 15, 30, 50, 100\text{ gwei}$.
   - Blob base fee: $1, 2, 10, 50, 100, 200, 500\text{ gwei}$.
   - ETH/USD price: $\$2,000, \$3,000, \$4,000\text{ USD/ETH}$.
   - Calldata cost models: Pre-Pectra ($16\text{ gas/byte}$) and Post-Pectra EIP-7623 ($40\text{ gas/byte}$ tokens floor).

### 1.2 Dependent Variables
- **Preparation Latency**: Canonicalization time, compression time, field packing time, KZG commitment generation time ($\text{ms}$).
- **Throughput**: End-to-end preparation and reconstruction throughput ($\text{MiB/s}$).
- **Memory Footprint**: Peak resident set size (RSS in $\text{MiB}$).
- **Packing Efficiency**: Usable payload bytes divided by total allocated blob bytes ($\%$).
- **Blob Count**: Number of 128 KiB EIP-4844 blobs required ($N_{\text{blobs}} = \lceil \text{PackedBytes} / 131,072 \rceil$).
- **Verification Latency & Gas**: Gas consumption for contract entrypoints (`openDataset`, `appendExternalBlobs`, `finalizeDataset`, `verifyRecord`).
- **Network Metrics**: Time-to-inclusion ($\text{seconds}$), blob gas used, execution gas used, effective gas price.
- **Retrieval Metrics**: Sidecar retrieval latency ($\text{ms}$), retrieval success rate ($\%$), HTTP status codes.
- **Archival Bridge Metrics**: Storage upload latency, durable CID retrieval latency, cross-layer verification latency ($\text{ms}$).

---

## 2. Dataset Selection and Ingestion Protocol

### 2.1 Inclusion Criteria
1. Datasets must be licensed under open, permissive licenses (CC0, CC-BY, MIT, or public domain) permitting redistribution of benchmarking derivatives.
2. Datasets must have authoritative, verifiable provenance (primary API endpoint, official repository, or archival DOI).
3. Payloads must represent realistic scientific or engineering structures (nested JSON objects, tabular measurements, floating-point metrics).
4. Deterministic synthetic datasets must be reproducible from a fixed seed (`42`).

### 2.2 Exclusion Criteria
1. Proprietary, sensitive, personally identifiable, or unverified data sources.
2. Dynamic endpoints that return non-deterministic timestamps or unversioned records without freezing a canonical fixture.
3. Live network dependencies during automated CI test execution.

---

## 3. Execution Environment and Isolation

### 3.1 Hardware and OS Rigor
- Operating system: Windows 11 Enterprise / Ubuntu LTS in CI.
- System metrics captured automatically prior to benchmark runs into `benchmarks/journal-extension/manifests/environment.json`.
- Warm-up policy: Each timing benchmark executes $2$ unrecorded warm-up iterations to prime disk caches, file system buffers, and JIT/Python bytecode caches before recorded iterations.
- Run counts:
  - Local micro-benchmarks and timing: $N = 10$ recorded runs per cell.
  - Large-payload ($20\text{ MiB}, 50\text{ MiB}$) benchmarks: $N = 5$ recorded runs to prevent thermal throttling.
  - Testnet submissions (if approved and funded): Target $N \ge 30$ transactions across distinct time intervals.

### 3.2 Cache State Management
- **Warm-Cache Condition**: Datasets pre-loaded in memory; evaluates pure algorithmic and cryptographic latency.
- **Cold-Cache Condition**: Datasets read from disk storage on each iteration with OS buffer flushing where supported; evaluates real-world pipeline ingestion.

---

## 4. Testnet Experimentation Protocol and Safeguards

### 4.1 Safety Controls
Testnet transactions on Sepolia (`11155111`) are governed by strict safety rules:
1. `JOURNAL_NETWORK_EXPERIMENTS_APPROVED=true` must be explicitly configured in the execution environment.
2. Safe defaults are strictly enforced:
   ```bash
   JOURNAL_NETWORK_EXPERIMENTS_APPROVED=false
   JOURNAL_MAX_TRANSACTIONS=0
   JOURNAL_MAX_TOTAL_TESTNET_ETH=0
   JOURNAL_MAX_FEE_PER_TRANSACTION_ETH=0
   ```
3. A dry-run execution must print a non-secret transaction summary before sending.
4. If approval or funding is unavailable, the test harness produces a pending-experiment manifest (`benchmarks/journal-extension/network/pending_experiments.json`). **No transaction hashes or measurements are ever fabricated.**

---

## 5. Experiment Classification

- **Confirmatory Experiments**:
  - Verification of bitwise reconstruction parity ($100\%$).
  - Analytical break-even blob fee calculation across fee regimes.
  - Adversarial detection rate ($100\%$) across 15 threat scenarios.
  - Archival bridge bitwise verification post simulated blob expiry.
- **Exploratory Experiments**:
  - Public consensus endpoint retrieval reliability across varying sidecar ages.
  - Memory scaling curves for ultra-large payloads ($50\text{ MiB}$).
  - Comparative compression ratio across diverse real-world scientific schemas.
