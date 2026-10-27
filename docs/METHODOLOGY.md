# Experimental Methodology and Measurement Framework

This document outlines the formal experimental methodology, hardware specifications, dataset synthesis parameters, gas measurement models, and statistical criteria utilized in the evaluation of **research-blob-da**.

---

## 1. Experimental Environment and System Specifications

All benchmarks, cryptographic operations, serialization pipelines, and EVM simulations were executed on a dedicated research workstation with the following specifications:

- **Host Processor:** AMD Ryzen 9 7950X 16-Core Processor @ 4.50 GHz (Boost up to 5.70 GHz), 32 execution threads, 64 MB L3 Cache.
- **System Memory:** 64 GB DDR5-5600 MT/s Dual-Channel ECC DRAM.
- **Storage Subsystem:** 2 TB NVMe PCIe 4.0 SSD (Sequential Read: 7,000 MB/s, Sequential Write: 5,000 MB/s).
- **Host Operating System:** Microsoft Windows 11 Enterprise (x86_64, Build 22631).
- **Execution Runtime:** Python 3.13.11 64-bit with optimized C-extensions (`zstandard` 0.23.0, `pycryptodome` 3.21.0, `ckzg` 2.0.1).
- **Ethereum Virtual Machine Framework:** Foundry `forge` version 1.5.1-stable (`cancun` EVM target, `via_ir = true`, optimizer enabled with 200 runs).

---

## 2. Dataset Synthesis and Statistical Properties

To ensure rigorous benchmarking across diverse scientific disciplines without relying on proprietary or non-distributable data, four representative synthetic datasets were constructed using deterministic pseudo-random generators (`seed = 42`):

### 2.1 Machine Learning Training Trace (`data/ml_training_trace.json`)
- **Record Count:** 10,000 discrete step records.
- **Schema:** `{"epoch": int, "step": int, "loss": float, "val_loss": float, "lr": float, "grad_norm": float, "accuracy": float}`.
- **Statistical Model:** Loss is modeled as an exponential decay curve with additive Gaussian noise ($\mu = 0, \sigma = 0.05$) bounded below by $0.15$. Learning rate implements cosine annealing. Gradient norms follow a log-normal distribution with occasional gradient spikes to simulate realistic transformer training dynamics.

### 2.2 Climate Station Telemetry (`data/climate_sensor_timeseries.csv`)
- **Record Count:** 20,000 tabular rows.
- **Schema:** `timestamp,station_id,temperature_c,relative_humidity_pct,pressure_hpa,wind_speed_ms,solar_radiation_wm2`.
- **Statistical Model:** Ambient temperatures exhibit diurnal sinusoidal cycles with an added random walk. Atmospheric pressure and humidity maintain inverse correlations adhering to barometric meteorological formulas.

### 2.3 Genomics Variant Callset Benchmark (`data/genomics_variant_benchmark.json`)
- **Record Count:** 8,000 variant records.
- **Schema:** `{"chrom": str, "pos": int, "ref": str, "alt": str, "qual": float, "filter": str, "depth": int, "allele_freq": float, "impact_score": float}`.
- **Statistical Model:** Positions distributed across human chromosomes 1–22. Transition/transversion ratios calibrated to empirical biological rates ($Ti/Tv \approx 2.1$). Allele frequencies follow a neutral Wright-Fisher frequency spectrum ($1/f$).

### 2.4 Academic Paper Metadata (`data/academic_paper_metadata.json`)
- **Record Count:** 5,000 bibliographic JSON records.
- **Schema:** `{"doi": str, "title": str, "authors": list[str], "year": int, "venue": str, "citations": int, "abstract": str}`.
- **Statistical Model:** Author team sizes follow a Poisson distribution ($\lambda = 3.5$). Citation counts follow a Pareto distribution with exponent $\alpha = 1.3$, reflecting heavy-tailed academic citation patterns.

---

## 3. Gas Cost and Economic Valuation Models

### 3.1 Gas Accounting Parameters
The economic evaluation employs standard Cancun network parameters and current market averages:

$$\text{ETH Price} = \$3,000.00\text{ USD}$$
$$\text{Standard Execution Base Fee } (P_{\text{base}}) = 15.0\text{ gwei} = 1.5 \times 10^{-8}\text{ ETH}$$
$$\text{Blob Base Fee } (P_{\text{blob}}) = 2.0\text{ gwei} = 2.0 \times 10^{-9}\text{ ETH}$$

### 3.2 Primitive Valuation Formulas

1. **EIP-4844 Blob Cost:**
   Each blob consumes exactly 131,072 blob gas (governed by EIP-4844 fixed parameter `GAS_PER_BLOB = 2^17`). The marginal blob cost for $k$ blobs is:
   $$\text{Cost}_{\text{blob}} = k \times 131,072 \times P_{\text{blob}} \times \text{ETH\_USD}$$
   Plus the base transaction execution gas ($21,000\text{ gas} \times P_{\text{base}}$).

2. **Standard Calldata Cost:**
   Calldata meters zero bytes at 4 gas and non-zero bytes at 16 gas. Across empirical compressed payloads, non-zero bytes represent approximately 99.6% of the byte stream:
   $$\text{Gas}_{\text{calldata}}(S) = S \times (0.996 \times 16 + 0.004 \times 4) \approx S \times 15.952\text{ gas}$$
   $$\text{Cost}_{\text{calldata}} = (\text{Gas}_{\text{calldata}} + 21,000) \times P_{\text{base}} \times \text{ETH\_USD}$$

3. **EIP-7623 Calldata Floor Cost:**
   EIP-7623 proposes an execution floor of 32 gas per token byte for transactions whose calldata exceeds the standard gas-to-calldata ratio:
   $$\text{Gas}_{\text{calldata\_7623}}(S) = S \times 32\text{ gas}$$
   $$\text{Cost}_{\text{calldata\_7623}} = (\text{Gas}_{\text{calldata\_7623}} + 21,000) \times P_{\text{base}} \times \text{ETH\_USD}$$

4. **SSTORE Permanent Contract State:**
   Storing $S$ bytes requires $\lceil S / 32 \rceil$ storage slots. Each cold storage slot allocation (`SSTORE` from zero to non-zero) incurs 20,000 gas, plus 2,100 gas for cold account access:
   $$\text{Gas}_{\text{sstore}}(S) = \left\lceil \frac{S}{32} \right\rceil \times 20,000\text{ gas}$$
   $$\text{Cost}_{\text{sstore}} = \text{Gas}_{\text{sstore}}(S) \times P_{\text{base}} \times \text{ETH\_USD}$$

5. **Cloud and Decentralized Baselines:**
   - **AWS S3 Standard Storage:** $\$0.023\text{ per GB per month} \implies \$0.000276\text{ per MiB per year}$.
   - **IPFS Pinning Service:** Fixed tier pin rate of $\$2.19\text{ USD per GB per year}$.

---

## 4. Benchmark Measurement Protocol and Statistical Validation

1. **Timer Precision:** Execution latencies were measured using Python's `time.perf_counter_ns()`, offering nanosecond resolution.
2. **Warm-up Iterations:** To eliminate CPU frequency scaling artifacts, OS page fault latency, and JIT/bytecode compilation variance, each benchmark loop was preceded by 3 untimed warm-up executions.
3. **Repetition and Confidence Intervals:** Benchmark suites were executed across $N = 10$ independent iterations per condition. Reported metrics represent the sample mean ($\mu$) and sample standard deviation ($\sigma$):
   $$\mu = \frac{1}{N} \sum_{i=1}^N x_i, \quad \sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (x_i - \mu)^2}$$
4. **Foundry EVM Tracing:** On-chain gas consumption was measured through direct Foundry execution traces (`vm.pauseGasMetering` and `vm.resumeGasMetering` were applied around test harness assertions to isolate target contract operations).
5. **Invariant Testing:** The smart contract suite was validated via property-based invariant fuzzing over 256 test sequences, each executing 64 consecutive randomized function calls (16,384 total state transitions), with zero discards and zero invariant violations.
