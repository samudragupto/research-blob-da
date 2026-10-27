# research-blob-da v0.1.0

**Release Tag:** `v0.1.0`  
**Release Title:** `research-blob-da v0.1.0: Verifiable Data Availability for Research Datasets via EIP-4844 Blobs`  
**Author:** Arrhat Nag (GitHub: [samudragupto](https://github.com/samudragupto))  
**Date:** October 2026 (Release Date: 2026-10-27 UTC)  

---

## Overview

`research-blob-da` is an empirical research prototype and evaluation framework demonstrating that Ethereum EIP-4844 blobs can serve as a cheap, decentralized, and verifiable data-availability primitive for scientific datasets, machine learning training traces, climate sensor series, and academic archives.

The prototype implements an end-to-end pipeline spanning deterministic canonical serialization (RFC 8785), modulus-safe field element modulus packing (`FE31`), binary Keccak-256 Merkle commitments, EVM contracts (`DatasetRegistry.sol`) anchoring blob versioned hashes via `BLOBHASH`, and optimistic dispute games with on-chain fraud refutations.

---

## Defensible Headline Findings

All empirical benchmarks were executed under documented baseline fee assumptions: **15 gwei execution base fee**, **2 gwei blob base fee**, and **$3,000 USD per ETH**.

1. **27.8x Theoretical Uncompressed Cost Reduction vs. Standard Calldata:**
   A 1.0 MiB uncompressed raw payload requires 9 blobs (based on 126,945 usable body bytes per blob), costing **$27.24 USD** in blobs versus **$755.92 USD** in standard calldata cost, 4 gas per zero byte and 16 gas per non-zero byte, before application of the EIP-7623 floor—a **27.8x cost reduction**.

2. **12.1x Measured Compressed Cost Reduction on an ML Training Trace:**
   On a synthetic ML training trace of 1,056.1 KiB (1,081,484 bytes), compression with Zstandard level 3 achieves a 6.04x reduction to 174.9 KiB (179,112 bytes). Packing this stream requires only 2 blobs, costing **$10.71 USD** in blobs versus **$129.91 USD** in standard calldata before application of the EIP-7623 floor—a **12.1x cost reduction**.

3. **Real Academic Dataset Empirical Demonstration (OpenAlex):**
   Evaluating a real scholarly dataset of 500 work records from the OpenAlex API (committed source file: 264,057 bytes / 257.9 KiB; canonical payload: 212,517 bytes / 207.5 KiB) achieves a 4.13x compression ratio down to 50.3 KiB. The compressed payload fits entirely within a single blob, costing **$8.35 USD** with a frozen encoding latency of **11.7 ms ± 0.2 ms (N=10)**.

4. **Break-Even Blob Base Fee:**
   At a 15 gwei execution base fee, the analytical break-even blob base fee for a 1.0 MiB payload is **207.9 gwei**. Blobs provide an economic advantage over calldata across all market regimes where the blob base fee remains below 207.9 gwei.

---

## Ethereum Sepolia Testnet Deployment

The complete smart contract suite and a live EIP-4844 Type-3 blob payload have been deployed and verified on the Ethereum Sepolia testnet:

- **Network:** Ethereum Sepolia (Chain ID: 11155111)
- **DatasetRegistry Contract:** [`0x238dE56E52A3F6C6708952052e6a20E5102b4d5b`](https://sepolia.etherscan.io/address/0x238dE56E52A3F6C6708952052e6a20E5102b4d5b#code) (Verified on Etherscan: compiler v0.8.24, EVM target cancun, 200 optimization runs)
- **Deployment Transaction:** [`0xa55af2b2a6ec29cc706bd8e5ebc166d6ae3130002c183f7ebdbb8186cc834751`](https://sepolia.etherscan.io/tx/0xa55af2b2a6ec29cc706bd8e5ebc166d6ae3130002c183f7ebdbb8186cc834751) (Block 12006103)
- **Live EIP-4844 Blob Transaction:** [`0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea`](https://sepolia.etherscan.io/tx/0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea) (Block 12006195)
- **Dataset ID:** `0x4f7b50bd684170f2c427d8975ee6478fadbc46918b764f1e8a4915374bf9d29b`
- **KZG Versioned Hash:** `0x010e6c7880a790abbedd746b98b713b5780e8e662d9f57f31cc51671b01faf11`
- **Deployment Record:** [deployments/sepolia_deployment.json](deployments/sepolia_deployment.json)

### Local Reconstruction and Verification
Retrieval verified on 2026-10-27 16:28:44 UTC from the local cache: the blob sidecar was retrieved, the dataset was reconstructed, and the reconstructed canonical-payload SHA-256 (`0b7175bfbd6aa0cf048d8c9e5bf1a2c51302531fcce936871bcb84d8b919c12c`) matched the manifest and bound to the versioned hash recorded on Sepolia. (Independent consensus retrieval from public Sepolia beacon nodes encountered upstream gateway errors 500/400, and the public Blobscan Sepolia indexer head was lagging at block 11,818,175, ~188k blocks behind live block 12,006,195; full disclosure in [deployments/sepolia_retrieval_verification.json](deployments/sepolia_retrieval_verification.json)).

---

## Reproduction Commands

To reproduce the test suites, formal verification, and empirical benchmarks:

```bash
# 1. Smart contract compilation and tests (31 passing tests)
forge test

# 2. Python test suite (43 passing tests)
pytest -v tests

# 3. Benchmark generation scripts (optional; reproduces CSV data and publication figures)
python python/experiments.py
python python/plot_results.py

# 4. Repository consistency audit (validates numbers and freeze record)
python python/check_consistency.py
```

*Note on Reproduction Hardware:* Re-running `python/experiments.py` on different hardware or operating systems will naturally produce hardware-dependent timing latencies (mean and standard deviation), while dataset sizes, compression ratios, blob counts, and monetary cost models remain strictly invariant and deterministic. The attached CSV files represent the authoritative frozen v0.1.0 generation rather than a newly executed run.

---

## Research Documentation

- Comprehensive Academic Paper: [docs/RESEARCH.md](docs/RESEARCH.md)
- Experimental Methodology and Gas Profiles: [docs/METHODOLOGY.md](docs/METHODOLOGY.md)
- Engineering Insights and Cryptographic Edge Cases: [docs/ENGINEERING_LESSONS.md](docs/ENGINEERING_LESSONS.md)
- Testnet Deployment and Verification Guide: [docs/SEPOLIA_DEPLOYMENT.md](docs/SEPOLIA_DEPLOYMENT.md)
- Authoritative Benchmark Freeze Record: [benchmarks/FROZEN_BENCHMARKS_v0.1.0.json](benchmarks/FROZEN_BENCHMARKS_v0.1.0.json)
- Two-Minute Demonstration Script: [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md)

---

## Fundamental Protocol Limitations

1. **Ephemeral Retention Horizon:** Blob sidecars are pruned by consensus layer clients after approximately 4,096 epochs (~18.2 days). Blobs guarantee temporary decentralized data availability, not permanent perpetual storage.
2. **Per-Block and Per-Transaction Limits:** Under current Cancun rules (max 6 blobs per transaction / block), compressed datasets exceeding 761 KiB require multi-transaction submissions.
3. **Retrieval Infrastructure Dependence:** Consumers and auditors must retrieve sidecars from consensus beacon nodes, local sidecar caches, or decentralized archival networks before the pruning window expires.
4. **Archival Layer Requirement:** Long-term durability requires an extended availability layer (such as IPFS/Filecoin pinning, BitTorrent swarms, or decentralized cold-storage providers) anchored to the on-chain versioned hash and Merkle root.
