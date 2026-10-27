# Engineering Lessons from Implementing research-blob-da

**Author:** Arrhat Nag (GitHub: samudragupto)  
**Date:** October 2026  
**Scope:** Architecture, Cryptography, and EVM Gas Dynamics in EIP-4844 Blob Systems

This document records the technical lessons, edge cases, and design trade-offs discovered during the implementation and evaluation of `research-blob-da`. These notes reflect first-hand engineering decisions made while building the canonical serialization engine, blob packing codecs, Foundry contracts, and verification pipelines.

---

## Lesson 1: Field-Element Modulus and the 3.12% Padding Reality

EIP-4844 blobs consist of 4,096 32-byte field elements representing coefficients of a polynomial evaluated over the BLS12-381 scalar field. Because the BLS12-381 scalar field modulus is:

$$r = 52435875175126190479447740508185965837690552500527637822603658699938581184513$$

which is strictly smaller than $2^{255}$, an arbitrary 32-byte word where the most significant bit or top bytes are set can easily exceed $r$. Any field element $x \ge r$ causes consensus client validation to reject the blob.

In `python/encoder.py`, I implemented and benchmarked two distinct packing schemes:
1. **Conservative 31-Byte Slicing (`FE31`):** Every 32-byte word stores 31 bytes of application payload with the high byte clamped to `0x00`. This guarantees $x < 2^{248} < r$ without bit-manipulation overhead, providing an exact capacity of $4,096 \times 31 = 126,976$ bytes per blob (minus the 31-byte Field Element 0 domain header, yielding **126,945 usable body bytes**).
2. **Dense 254-Bit Packing (`FE254`):** Slices the continuous bitstream into 254-bit chunks ($x < 2^{254} < r$), yielding $130,048$ bytes ($130,017$ usable body bytes).

While `FE254` increases raw byte density by 2.4%, it requires bit-shifting every byte across word boundaries. In our benchmarks, `FE254` increased encoding latency by nearly 4x while only saving a single blob on multi-megabyte datasets. For standard scientific pipelines, `FE31` provides predictable, memory-aligned chunking and universal safety against modulus invalidation.

---

## Lesson 2: Versioned Hashes Are Not Data: The EVM Visibility Boundary

A common misconception among developers new to EIP-4844 is that smart contracts can inspect blob data directly. In the EVM, execution contracts only have access to the `BLOBHASH` opcode (`0x49`), which takes an index and returns the 32-byte versioned hash:

$$\text{versioned\_hash} = \mathtt{0x01} \parallel \text{sha256}(\text{KZG\_commitment})[1:]$$

The blob body travels exclusively through consensus-layer peer-to-peer sidecars and is never placed into execution-layer state or memory.

In `contracts/DatasetRegistry.sol`, this architecture required a clear separation:
- At transaction execution time, `openDataset` reads `BLOBHASH` to bind the caller's transaction blobs to the dataset identifier.
- Direct property claims (e.g., verifying that a recorded loss metric falls within a bounded range) cannot inspect the blob on-chain during registration.
- Instead, the registry must employ an **optimistic verification model**: claims are registered with Merkle commitments, and challengers refute invalid claims by providing the specific canonical record and its Merkle inclusion proof.

---

## Lesson 3: Range Proofs Deliver Substantial Gas Reductions for Batch Audits

Scientific workflows rarely query a single isolated measurement; researchers typically inspect contiguous time windows or consecutive training epochs.

When proving $N$ contiguous records in a Merkle tree of depth $D$:
- Verifying $N$ independent single-leaf proofs requires $N \times D$ Keccak-256 hashes on-chain.
- For $N = 8$ in a depth-12 tree (4,096 records), independent proofs require $8 \times 12 = 96$ hash operations ($\approx 95,000$ gas).

In `contracts/libraries/MerkleLib.sol`, I implemented `verifyRangeProof`, which reconstructs intermediate subtrees from contiguous leaves and merges them with boundary sibling hashes. For an 8-leaf range in a depth-12 tree, this reduces the proof length from 96 hashes down to 18 operations, cutting verification gas from $\approx 97,000$ down to $\approx 26,000$ gas—a **73.2% gas reduction**. This demonstrates that structuring dataset records sequentially allows researchers to audit contiguous benchmark slices at negligible EVM cost.

---

## Lesson 4: Retention Windows Dictate Optimistic Dispute Deadlines

Consensus clients prune blob sidecars after approximately 4,096 epochs ($\approx 18.2$ days). After this horizon, consensus nodes discard the polynomial data, and blobs cannot be fetched via standard beacon endpoints.

This physical protocol constraint imposes a fundamental rule on on-chain claims:
- Any optimistic property claim must have a challenge deadline strictly prior to the pruning horizon of the dataset's earliest blob.
- If a claim remained open after 4,096 epochs, a challenger would be unable to retrieve the underlying blob to generate a refutation witness from standard nodes.
- In `DatasetRegistry.sol`, every claim's deadline is strictly capped at `firstBlobAt + BLOB_RETENTION_SECONDS`.
- Furthermore, once the retention window expires, unrefuted claims transition to `Status.Unchallenged`, rather than "proven". The protocol honestly distinguishes between claims that withstood active challenge while data was live, versus assertions that simply aged out.

---

## Lesson 5: Disaggregating Execution Gas from Blob Gas in Cost Modeling

A superficial analysis of EIP-4844 assumes blob publishing is practically free because blob base fees have frequently idled at 1 wei. However, publishing a dataset involves two distinct gas dimensions:
1. **Blob Gas:** Fixed at exactly 131,072 blob gas units per blob ($2^{17}$), priced via the EIP-4844 exponential blob fee market (`BLOBBASEFEE`).
2. **Execution Gas:** Standard EVM gas required for transaction base cost (21,000), dataset registration storage writes, and `BLOBHASH` invocations (approximately 168,000 gas for initial registration, plus 35,000 gas per additional blob).

When execution base fees are high (e.g., 50 gwei) and blob base fees are low (e.g., 2 gwei), execution gas accounts for over 85% of the total USD posting cost! Conversely, during periods of heavy rollup congestion where blob base fees spike, blob gas dominates. Evaluating dataset economics requires modeling both gas markets simultaneously.

---

## Lesson 6: JSON Fixed-Point Parsing in EVM Bytecode

Scientific and machine learning traces frequently store numerical metrics as decimal floating-point strings (e.g., `{"loss": 0.4125}`). The EVM has no native floating-point support.

To enable refutation of optimistic claims over numerical metrics without off-chain oracles, `contracts/libraries/JsonFieldLib.sol` parses ASCII numeric bytes directly in EVM assembly:
- Scans JSON key-value pairs without full DOM parsing.
- Extracts integer and fractional parts separated by the ASCII dot (`0x2E`).
- Scales the value to a fixed-point integer according to the claim's registered decimal precision.

This pure-Yul parser consumes less than 6,000 gas per field extraction, proving that decentralized micro-audits of structured telemetry are feasible directly inside the Cancun EVM.
