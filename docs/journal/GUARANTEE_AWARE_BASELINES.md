# Guarantee-Aware Baseline Comparison

This document formalizes the multidimensional comparison between Ethereum EIP-4844 blobs and alternative storage architectures, replacing simplistic USD/byte rankings with a guarantee-aware evaluation framework.

---

## 1. The Fallacy of Naive Cost-Per-Byte Rankings

Prior decentralized storage comparisons often rank technologies solely by raw price per gigabyte. This introduces severe category errors by treating fundamentally disparate service models as equivalent:
- **EIP-4844 Blobs** provide consensus-enforced, immediate data availability guaranteed across all Ethereum validators for $\approx 18.2\text{ days}$. Blobs do *not* offer permanent archival.
- **Ethereum Calldata** commits transaction byte streams into full node block history indefinitely (subject to future EIP-4444 pruning), but incurs high execution gas.
- **Ethereum SSTORE** provides perpetual, synchronous, EVM-readable world state, but at prohibitive cost ($> \$2,900\text{ USD/MiB}$).
- **IPFS** provides peer-to-peer content addressing, but guarantees zero persistence without voluntary pinners or recurring pinning subscriptions.
- **Filecoin** provides cryptographic proofs of physical storage capacity via fixed-duration commercial contracts (180–540 days).
- **Arweave** uses an upfront mining fee endowment intended to fund permanent storage over multi-decade time horizons (~200 years).
- **Amazon S3** provides enterprise high-availability object storage backed by commercial SLAs, but lacks decentralized consensus verification and incurs ongoing subscription and egress costs.

---

## 2. Multi-Dimensional Guarantee Matrix

Data source: `benchmarks/journal-extension/manifests/storage_baselines.json` and `baseline_comparison.csv`.

| Storage System | Availability Period | Consensus Verification Model | Permanence Model | Retrieval Guarantee | Typical Payer | Cost per 1 MiB (USD) | Evidence Type |
|---|---|---|---|---|---|---|---|
| **EIP-4844 Blobs** | Temporary ($\ge 4,096$ epochs / $\approx 18.2$ days) | Direct L1 EVM cryptographic commitment (`BLOBHASH`, KZG) | Pruned by consensus clients; external archiver required | P2P gossip during window; public Beacon API or archival RPC | Dataset Publisher (one-time fee) | **$0.052** | Measured on Sepolia (`0x9631...7ea`) |
| **Ethereum Calldata** | Historical Chain Life (Full node history) | Merkle Patricia Trie receipt root in block header | Retained in archive/full nodes (subject to EIP-4444) | Standard JSON-RPC (`eth_getTransactionByHash`) | Dataset Publisher (one-time gas) | **$1.440** | Measured in smart contract benchmarks |
| **Ethereum SSTORE** | Perpetual EVM World State | Direct EVM opcode readability (`SLOAD`) and state root | Permanent state until explicitly overwritten | Synchronous contract execution; instant query | Dataset Publisher ($20,000$ gas/slot) | **$2,949.12** | Measured in `SstoreArchive.sol` |
| **IPFS** | Pin-Dependent | No native consensus; verified via CID multihash match | Volatile without pinning service or active seeders | Bitswap P2P routing / public HTTP gateways | Publisher or Pinner (monthly subscription) | **$0.00015** | Estimated from commercial pinning rates |
| **Filecoin** | Contract-Dependent ($180$ to $540$ days per deal) | Cryptographic Proof of Replication (PoRep) and Spacetime (PoSt) | Deal-dependent; terminated upon deal expiry | Storage provider retrieval contracts / Lassie / Saturn | Storage Client (FIL tokens + retrieval gas) | **$0.000002** | Estimated from network deal index |
| **Arweave** | Multi-Decade Endowment ($\approx 200$ years) | Proof of Access (PoA / SPoRA) on independent blockweave | Protocol-enforced endowment funding multi-decade storage | Direct weave gateway retrieval (`arweave.net`) | Dataset Publisher (one-time upfront AR fee) | **$0.005** | Estimated from network fee calculator |
| **Amazon S3** | Account-Dependent (99.99% SLA while paid) | None (Proprietary SLA; centralized corporate provider) | Deleted upon account termination or payment lapse | High-availability HTTPS REST API (guaranteed SLA) | Account Owner (recurring monthly + egress) | **$0.000023** | Published AWS US-East-1 pricing |

---

## 3. Graphical Comparison

The visual relationship between publication cost and underlying protocol guarantees is illustrated in `benchmarks/journal-extension/figures/guarantee_cost_matrix.png` and `guarantee_cost_matrix.pdf`.

---

## 4. Key Takeaways for Scientific Publishing

1. **Blobs are Economically Unmatched for Consensus Verification**:
   Blobs provide a **27.8x cost reduction** over standard calldata for publishing temporary verifiable datasets directly anchored to Ethereum consensus.
2. **Decoupled Architecture is Optimal**:
   Publishing temporary data to blobs while simultaneously registering content-addressed CIDs in external archival storage (e.g. IPFS/Filecoin) provides the exact dual guarantee needed for scientific artifacts: immediate consensus-backed validity at lowest cost, followed by durable multi-year preservation.
