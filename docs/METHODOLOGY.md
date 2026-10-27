# Experimental Methodology and Measurement Framework

**Author:** Arrhat Nag (GitHub: samudragupto)  
**Project:** research-blob-da (v0.1.0)  
**Date:** October 2026  

This document outlines the formal experimental methodology, hardware specifications, dataset provenance and synthesis parameters, gas measurement models, and statistical validation criteria utilized in the evaluation of **research-blob-da**.

---

## 1. Experimental Environment and System Specifications

All benchmarks, cryptographic operations, serialization pipelines, and EVM simulations were executed directly on the host evaluation hardware with the following verified system specifications:

- **Host Machine:** Lenovo LOQ 15APH8 (Model 82XT).
- **Host Processor:** AMD Ryzen 7 7840HS w/ Radeon 780M Graphics (8 Physical Cores, 16 Logical Processors, Zen 4 Phoenix architecture, 3.80 GHz Base Clock, Boost up to 5.10 GHz, 16 MB L3 Cache, TSMC 4nm FinFET).
- **Dedicated Graphics:** NVIDIA GeForce RTX 4060 Laptop GPU (8 GB GDDR6, 128-bit bus, Ada Lovelace architecture).
- **System Memory:** 16 GB DDR5-5600 MT/s Dual-Channel DRAM (2 x 8 GB Micron Technology).
- **Host Operating System:** Microsoft Windows 11 Home Single Language (64-bit, Build 26200).
- **Execution Runtime:** Python 3.13.11 64-bit with optimized C-extensions (`zstandard` 0.23.0, `pycryptodome` 3.21.0).
- **Ethereum Virtual Machine Framework:** Foundry `forge` version 1.5.1-stable (`cancun` EVM target, `via_ir = true`, optimizer enabled with 200 runs).

*Note on Execution Timings:* All benchmark timing figures are environment-dependent. While relative compression ratios and on-chain gas counts are deterministic and architecture-invariant, absolute latencies will vary with CPU clock speeds, thermal throttling, and background operating system scheduling. All experiments can be reproduced on any standard workstation by running `python python/experiments.py`.

---

## 2. Dataset Provenance, Synthesis, and Provenance

To balance experimental control against real-world external validity, the benchmark suite evaluates four synthetic domain datasets and one real public dataset harvested from an open academic index.

### 2.1 Machine Learning Training Trace (`data/ml_training_trace.json`)
- **Category:** Synthetic Benchmark.
- **Record Count:** 10,000 discrete step records.
- **Schema:** `{"epoch": int, "step": int, "loss": float, "val_loss": float, "lr": float, "grad_norm": float, "accuracy": float}`.
- **Statistical Model:** Loss is modeled as an exponential decay curve with additive Gaussian noise ($\mu = 0, \sigma = 0.05$) bounded below by $0.15$. Learning rate implements cosine annealing. Gradient norms follow a log-normal distribution with stochastic spikes simulating transformer pretraining dynamics.

### 2.2 Climate Station Telemetry (`data/climate_sensor_timeseries.csv`)
- **Category:** Synthetic Benchmark.
- **Record Count:** 20,000 tabular rows.
- **Schema:** `timestamp,station_id,temperature_c,relative_humidity_pct,pressure_hpa,wind_speed_ms,solar_radiation_wm2`.
- **Statistical Model:** Ambient temperatures exhibit diurnal sinusoidal cycles with an added random walk. Atmospheric pressure and humidity maintain inverse correlations adhering to barometric meteorological formulas.

### 2.3 Genomics Variant Callset Benchmark (`data/genomics_variant_benchmark.json`)
- **Category:** Synthetic Benchmark.
- **Record Count:** 8,000 variant records.
- **Schema:** `{"chrom": str, "pos": int, "ref": str, "alt": str, "qual": float, "filter": str, "depth": int, "allele_freq": float, "impact_score": float}`.
- **Statistical Model:** Variant positions are distributed across human chromosomes 1–22. Transition/transversion ratios are calibrated to empirical biological rates ($Ti/Tv \approx 2.1$). Allele frequencies follow a neutral Wright-Fisher frequency spectrum ($1/f$).

### 2.4 Academic Paper Metadata (`data/academic_paper_metadata.json`)
- **Category:** Synthetic Benchmark.
- **Record Count:** 5,000 bibliographic JSON records.
- **Schema:** `{"doi": str, "title": str, "authors": list[str], "year": int, "venue": str, "citations": int, "abstract": str}`.
- **Statistical Model:** Author team sizes follow a Poisson distribution ($\lambda = 3.5$). Citation counts follow a Pareto distribution with exponent $\alpha = 1.3$, reflecting heavy-tailed academic citation distributions.

### 2.5 Real Academic Metadata: OpenAlex Scholarly Works (`data/real_academic_openalex.json`)
- **Category:** Real Public Dataset.
- **Source:** OpenAlex REST API (`https://api.openalex.org/works`).
- **Retrieval Method:** Deterministic query via `python/fetch_real_data.py`: `filter=publication_year:2023,is_oa:true&sort=cited_by_count:desc&per-page=100` across 5 paginated requests.
- **Record Count:** 500 discrete academic work records.
- **Raw Byte Size:** 264,057 bytes.
- **Cryptographic Integrity:** SHA-256 Checksum: `af65584227c707d3c16f7841a233070808ab1ed070f10f32e841082889a8c544`.
- **Terms & License:** Creative Commons CC0 Public Domain Dedication (OpenAlex terms for metadata).
- **Comparison Note:** Unlike synthetic metadata with uniform structure, real academic metadata exhibits heterogeneous title lengths, diverse author transliterations, varied Unicode characters, and real-world citation distributions. This introduces realistic entropy, resulting in a measured compression ratio of $4.13\text{x}$ (compared to $11.13\text{x}$ on synthetic metadata). A committed fixture is retained in `data/` so CI and offline test suites never depend on external network availability.

### 2.6 Source File Bytes Versus Canonical Payload Bytes

We define and distinguish five quantities across the pipeline:
1. **Source file bytes:** The exact number of bytes of the committed source file on disk. For OpenAlex (`data/real_academic_openalex.json`), this is 264,057 bytes (257.9 KiB). For synthetic datasets generated dynamically in memory, `source_file_bytes` is defined as the byte count of the serialized generated JSON or CSV string before canonical record extraction.
2. **Canonical payload bytes:** The exact number of bytes of the deterministic canonical byte sequence that is passed to Zstandard compression and blob encoding. The pipeline parses the input records, extracts the documented schema fields, canonicalizes them according to RFC 8785 (JSON Canonicalization Scheme), and frames them with delimiter bytes. For OpenAlex, this canonical payload is 212,517 bytes (207.5 KiB).
3. **Compressed bytes:** The exact number of bytes resulting from Zstandard level 3 compression of the canonical payload. For OpenAlex, this is 51,479 bytes (50.3 KiB).
4. **Encoded bytes:** The exact number of bytes after 31-byte field element packing (`FE31`), including field element framing and the 31-byte FE0 header.
5. **Blobs used:** The number of EIP-4844 blobs required to store the encoded payload ($\lceil \text{Compressed Bytes} / 126,945 \rceil$). For OpenAlex, this is 1 blob.

**Compression Ratio Definition:**
The compression ratio reported in Table B and throughout this repository is strictly defined as:
$$\text{Compression Ratio} = \frac{\text{Canonical Payload Bytes}}{\text{Compressed Bytes}}$$
For OpenAlex, this is $212,517 / 51,479 = 4.13\text{x}$. Compression ratio, blob count, and calldata cost are calculated from the canonical payload bytes that are actually compressed and posted, rather than the unparsed source file with formatting whitespace and wrapper fields.

---

## 3. Gas Cost and Economic Valuation Models

### 3.1 Gas Accounting Parameters
The economic evaluation employs standard Cancun network parameters and current market averages:

$$\text{ETH Price} = \$3,000.00\text{ USD}$$
$$\text{Standard Execution Base Fee } (P_{\text{base}}) = 15.0\text{ gwei} = 1.5 \times 10^{-8}\text{ ETH}$$
$$\text{Blob Base Fee } (P_{\text{blob}}) = 2.0\text{ gwei} = 2.0 \times 10^{-9}\text{ ETH}$$

### 3.2 Usable Blob Capacity and Encoding Formula

EIP-4844 blobs carry 4,096 32-byte field elements. Because the BLS12-381 scalar field modulus is:

$$r = 52435875175126190479447740508185965837690552500527637822603658699938581184513 < 2^{255}$$

arbitrary byte chunks must be packed to guarantee $x < r$. 

Under our conservative 31-byte field element packing (`FE31`), each 32-byte word stores 31 bytes with the most significant byte set to `0x00`. Field Element 0 stores a 31-byte domain-separated header (`RBDA` magic, codec, layout, indices, and content hash tag).
Therefore, the usable body payload capacity per blob is strictly:

$$\text{Usable Bytes Per Blob} = (4096 \times 31) - 31 = 126,976 - 31 = \mathbf{126,945\text{ bytes}}$$

The required blob count $K$ for a payload of size $S$ is:

$$K = \left\lceil \frac{S}{126,945} \right\rceil$$

### 3.3 Primitive Valuation Formulas

1. **EIP-4844 Blob Cost:**
   Each blob consumes exactly 131,072 blob gas (governed by EIP-4844 fixed parameter `GAS_PER_BLOB = 2^17`). In addition, the registration transaction requires execution gas: 21,000 base transaction gas, plus contract state writes for the dataset manifest and versioned hashes ($168,000$ gas for the initial blob, plus $35,000$ gas per additional blob):
   $$\text{Gas}_{\text{exec}}(K) = 168,000 + (K - 1) \times 35,000$$
   $$\text{Cost}_{\text{blob}}(K) = \left[ \text{Gas}_{\text{exec}}(K) \times P_{\text{base}} + (K \times 131,072) \times P_{\text{blob}} \right] \times \text{Price}_{\text{ETH}} \times 10^{-9}$$

2. **Standard Calldata Cost:**
   Calldata meters zero bytes at 4 gas and non-zero bytes at 16 gas. Across empirical compressed payloads, non-zero bytes represent approximately 99.6% of the byte stream:
   $$\text{Gas}_{\text{calldata}}(S) = 21,000 + S \times 16\text{ gas}$$
   $$\text{Cost}_{\text{calldata}}(S) = \text{Gas}_{\text{calldata}}(S) \times P_{\text{base}} \times \text{Price}_{\text{ETH}} \times 10^{-9}$$

3. **Theoretical SSTORE Extrapolation (Not Executable as a Single Transaction):**
   Storing $S$ bytes requires $\lceil S / 32 \rceil$ 32-byte storage slots. In EVM state, allocating an uninitialized slot (`SSTORE` from zero to non-zero) costs 20,000 gas, plus 2,100 gas for cold account/slot access:
   $$\text{Gas}_{\text{sstore}}(S) = 21,000 + \left\lceil \frac{S}{32} \right\rceil \times 22,100\text{ gas}$$
   $$\text{Cost}_{\text{sstore}}(S) = \text{Gas}_{\text{sstore}}(S) \times P_{\text{base}} \times \text{Price}_{\text{ETH}} \times 10^{-9}$$
   *Multi-Block Impracticality:* At the standard 30,000,000 Ethereum block gas limit, publishing a 1.0 MiB payload requires $\lceil 724,193,800 / 30,000,000 \rceil = \mathbf{25\text{ full blocks}}$, proving that SSTORE is purely a theoretical cost reference point, not a practical data-posting mechanism.

4. **Post-Pectra Calldata Floor Sensitivity (Official EIP-7623):**
   EIP-7623, activated with Pectra, defines an execution-layer calldata floor that raises the effective gas cost of data-heavy transactions whose execution gas is small relative to their calldata size ([official specification](https://eips.ethereum.org/EIPS/eip-7623)). Under official EIP-7623 specifications:
   $$\text{Tokens} = (\text{Zero Bytes} \times 1) + (\text{Non-Zero Bytes} \times 4)$$
   $$\text{Standard Calldata Gas} = 4 \times \text{Tokens}$$
   $$\text{Floor Gas} = 21{,}000 + 10 \times \text{Tokens}$$
   $$\text{Gas Used} = 21{,}000 + \max(\text{Standard Calldata Gas} + \text{Execution Gas}, 10 \times \text{Tokens})$$
   For data-availability payloads where $\text{Execution Gas}$ is minimal, the floor applies. For non-zero bytes (compressed data), the effective floor is $40\text{ gas per byte}$ (plus 21,000 base). For zero bytes, it is $10\text{ gas per byte}$. Because the measured compressed payload is over 99.6% non-zero bytes, its effective EIP-7623 floor is approximately 39.88 gas per byte.

5. **Fee Sensitivity and Break-Even Blob Fee:**
   The economic break-even blob base fee ($P_{\text{blob}}^{\text{break-even}}$) where blob posting cost equals standard calldata cost is derived by setting $\text{Cost}_{\text{blob}} = \text{Cost}_{\text{calldata}}$:
   $$P_{\text{blob}}^{\text{break-even}} = \frac{21,000 + 16 \times S - \text{Gas}_{\text{exec}}}{K \times 131,072} \times P_{\text{base}}$$
   For a 1.0 MiB payload ($S = 1,048,576$, $K = 9$, $\text{Gas}_{\text{exec}} = 448,000$), the coefficient is $\approx 13.86$. At $P_{\text{base}} = 15\text{ gwei}$, the break-even blob fee is **207.9 gwei**.

6. **Cloud and Decentralized Archival Baselines:**
   - **AWS S3 Standard Storage:** $\$0.023\text{ per GB per month} \implies \$0.000276\text{ per MiB per year}$ plus $\$0.005$ per 1,000 PUT requests.
   - **IPFS Pinning Service:** Fixed tier pin rate of $\$2.19\text{ USD per GB per year}$.

---

## 4. Benchmark Measurement Protocol and Statistical Validation

1. **Timer Precision:** Execution latencies were measured using Python's `time.perf_counter_ns()`, offering sub-microsecond resolution.
2. **Warm-up Iterations:** To eliminate CPU frequency scaling artifacts, OS page fault latency, and bytecode compilation variance, each benchmark loop was preceded by 3 untimed warm-up executions.
3. **Repetition and Confidence Intervals:** Benchmark suites were executed across $N = 5$ independent iterations per condition. Reported metrics represent the sample mean ($\mu$) and sample standard deviation ($\sigma$):
   $$\mu = \frac{1}{N} \sum_{i=1}^N x_i, \quad \sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (x_i - \mu)^2}$$
4. **Foundry EVM Tracing:** On-chain gas consumption was measured through direct Foundry execution traces (`vm.pauseGasMetering` and `vm.resumeGasMetering` were applied around test harness assertions to isolate target contract operations).
5. **Invariant Testing:** The smart contract suite was validated via property-based invariant fuzzing over 256 test sequences, each executing 64 consecutive randomized function calls (16,384 total state transitions), with zero discards and zero invariant violations.
