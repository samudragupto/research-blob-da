# Generated Benchmark Tables: research-blob-da
All figures below are generated directly from executed code and committed datasets.
## Table A: Theoretical Uncompressed Cost Baseline
> [!NOTE]
> **Table A: Theoretical Uncompressed Cost Baseline.** Calldata cost is the standard calldata calculation (16 gas per non-zero byte and 4 gas per zero byte plus intrinsic and stated execution gas), before application of the EIP-7623 floor. This makes the reported blob savings factor conservative for data-heavy transactions under current post-Pectra rules, because the EIP-7623 floor can raise the effective calldata cost. See the Post-Pectra Calldata Floor Sensitivity subsection for the floor-adjusted analysis.
>
> **Assumptions:** Uncompressed raw data; usable payload per blob is strictly 126,945 bytes (4096 field elements * 31 bytes minus 31-byte FE0 header). Execution base fee: 15 gwei; blob base fee: 2 gwei; ETH price: $3,000 USD.
>
> **SSTORE Caution:** SSTORE figures represent a theoretical mathematical extrapolation (22,100 gas per 32-byte slot) and are **not executable as a single transaction**. At the 30M block gas limit, publishing 1.0 MiB via SSTORE would require at least 25 full Ethereum blocks.

| Dataset Size | Raw Bytes | Blobs Needed | Blob Cost (USD) | Standard Calldata Cost (USD, Pre-Floor) | Blob Savings vs Calldata | Theoretical SSTORE (USD)* | Min Blocks (SSTORE at 30M Gas) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0.125 MiB | 131,072 | 2 | $10.7079 | $95.32 | **8.9x** | $4,074.42 | 4 blocks |
| 1.0 MiB | 1,048,576 | 9 | $27.2379 | $755.92 | **27.8x** | $32,588.72 | 25 blocks |
| 5.0 MiB | 5,242,880 | 42 | $105.1651 | $3775.82 | **35.9x** | $162,939.83 | 121 blocks |
| 20.0 MiB | 20,971,520 | 166 | $397.9827 | $15100.44 | **37.9x** | $651,756.47 | 483 blocks |

---

## Table B: Measured Compressed Dataset Results
> [!NOTE]
> **Assumptions:** Canonical record serialization, Zstandard level 3 compression, and 31-byte field element packing (FE31). Blob counts, monetary costs, and compression ratios reflect canonical payload bytes actually compressed and posted. Calldata costs represent standard calldata before application of the EIP-7623 floor.

| Dataset Name | Type | Records | Canonical Payload Size | Compressed Size | Ratio | Blobs | Blob Cost (USD) | Standard Calldata (USD, Pre-Floor) | Savings | Encoding Time (Mean ± Std, N=10) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| ML Training Trace (JSON) | Synthetic Dataset | 10,000 | 1056.1 KiB | 174.9 KiB | 6.04x | **2** | $10.7079 | $129.91 | **12.1x** | 207.0 ms ± 3.7 ms |
| Climate Station Data (CSV/Tabular) | Synthetic Dataset | 20,000 | 3051.4 KiB | 403.1 KiB | 7.57x | **4** | $15.4307 | $298.14 | **19.3x** | 423.4 ms ± 11.3 ms |
| Genomics Variant Benchmark | Synthetic Dataset | 8,000 | 946.0 KiB | 163.0 KiB | 5.80x | **2** | $10.7079 | $121.14 | **11.3x** | 139.8 ms ± 0.7 ms |
| Academic Paper Metadata (JSON) | Synthetic Dataset | 5,000 | 825.4 KiB | 74.1 KiB | 11.13x | **1** | $8.3464 | $55.61 | **6.7x** | 100.9 ms ± 2.4 ms |
| OpenAlex Academic Works (JSON) | Real Dataset | 500 | 207.5 KiB | 50.3 KiB | 4.13x | **1** | $8.3464 | $38.01 | **4.6x** | 11.7 ms ± 0.2 ms |

> **Note on the OpenAlex row:** The committed source file is 264,057 bytes (257.9 KiB). The pipeline parses it, extracts the documented record fields, and deterministically canonicalizes the records before compression. The canonical payload actually compressed and encoded is 212,517 bytes (207.5 KiB). Compression ratio, blob count, and cost are therefore calculated from canonical payload bytes.

### Explanatory Note on Table A vs Table B Blob Counts
Reviewers comparing Table A and Table B will note that a **1.0 MiB theoretical uncompressed dataset requires 9 blobs**, whereas the **synthetic ML training trace (1,056 KiB canonical payload) requires only 2 blobs**.
This divergence is solely due to compression:
1. **Theoretical Uncompressed Baseline (Table A):** Assumes theoretical uncompressed data. With usable payload capacity of `126,945 bytes/blob` (4,096 elements * 31 bytes - 31 bytes header), posting 1,048,576 uncompressed bytes requires `ceil(1,048,576 / 126,945) = 9 blobs`.
2. **Measured Compressed Results (Table B):** The synthetic ML training trace contains recurring JSON keys and structured floating-point values that Zstandard compresses with a `6.04x` ratio, reducing 1,081,484 canonical payload bytes to `179,112 compressed bytes`. Chunking into 126,945-byte payload slots yields `ceil(179,112 / 126,945) = 2 blobs`.

---

## Table C: Blob Capacity and Inclusion Time Limits
> [!IMPORTANT]
> These figures represent theoretical lower bounds assuming exclusive blob block occupancy. In production, Ethereum blocks are shared with rollups and other blob market participants.

| Dataset Size | Case Type | Blobs | Protocol Era | Min Txs | Burst Blocks | Burst Time (12s) | Target Blocks | Target Time (12s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 128 KiB | Theoretical Uncompressed | 2 | Cancun (EIP-4844) | 1 | 1 | 12s | 1 | 12s |
| 128 KiB | Theoretical Uncompressed | 2 | Pectra (EIP-7691) | 1 | 1 | 12s | 1 | 12s |
| 128 KiB | Theoretical Uncompressed | 2 | PeerDAS (EIP-7594 Projection) | 1 | 1 | 12s | 1 | 12s |
| 1.0 MiB | Theoretical Uncompressed | 9 | Cancun (EIP-4844) | 2 | 2 | 24s | 3 | 36s |
| 1.0 MiB | Theoretical Uncompressed | 9 | Pectra (EIP-7691) | 1 | 1 | 12s | 2 | 24s |
| 1.0 MiB | Theoretical Uncompressed | 9 | PeerDAS (EIP-7594 Projection) | 1 | 1 | 12s | 1 | 12s |
| 5.0 MiB | Theoretical Uncompressed | 42 | Cancun (EIP-4844) | 7 | 7 | 84s | 14 | 168s |
| 5.0 MiB | Theoretical Uncompressed | 42 | Pectra (EIP-7691) | 5 | 5 | 60s | 7 | 84s |
| 5.0 MiB | Theoretical Uncompressed | 42 | PeerDAS (EIP-7594 Projection) | 1 | 1 | 12s | 2 | 24s |
| 20.0 MiB | Theoretical Uncompressed | 166 | Cancun (EIP-4844) | 28 | 28 | 336s | 56 | 672s |
| 20.0 MiB | Theoretical Uncompressed | 166 | Pectra (EIP-7691) | 19 | 19 | 228s | 28 | 336s |
| 20.0 MiB | Theoretical Uncompressed | 166 | PeerDAS (EIP-7594 Projection) | 3 | 3 | 36s | 6 | 72s |
| 1.0 MiB Raw (6x Zstd) | Measured Compressed | 2 | Cancun (EIP-4844) | 1 | 1 | 12s | 1 | 12s |
| 1.0 MiB Raw (6x Zstd) | Measured Compressed | 2 | Pectra (EIP-7691) | 1 | 1 | 12s | 1 | 12s |
| 1.0 MiB Raw (6x Zstd) | Measured Compressed | 2 | PeerDAS (EIP-7594 Projection) | 1 | 1 | 12s | 1 | 12s |

---

## Table D: Fee Sensitivity and Break-Even Analysis (1.0 MiB)
> [!NOTE]
> Break-even occurs where blob total cost equals calldata cost. At standard execution base fee `15 gwei`, the break-even blob base fee for 1.0 MiB is **207.9 gwei**.

| Base Fee (gwei) | Blob Fee (gwei) | Calldata Cost (USD) | Blob Cost (USD) | Savings Ratio | Blob Cost/MiB (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 15 | 1 | $755.92 | $23.70 | **31.90x** | $23.70 |
| 15 | 2 | $755.92 | $27.24 | **27.75x** | $27.24 |
| 15 | 10 | $755.92 | $55.55 | **13.61x** | $55.55 |
| 15 | 50 | $755.92 | $197.11 | **3.84x** | $197.11 |
| 15 | 100 | $755.92 | $374.05 | **2.02x** | $374.05 |
| 15 | 200 | $755.92 | $727.95 | **1.04x** | $727.95 |
| 50 | 1 | $2519.73 | $70.74 | **35.62x** | $70.74 |
| 50 | 2 | $2519.73 | $74.28 | **33.92x** | $74.28 |
| 50 | 10 | $2519.73 | $102.59 | **24.56x** | $102.59 |
| 50 | 50 | $2519.73 | $244.15 | **10.32x** | $244.15 |
| 50 | 100 | $2519.73 | $421.09 | **5.98x** | $421.09 |
| 50 | 200 | $2519.73 | $774.99 | **3.25x** | $774.99 |
