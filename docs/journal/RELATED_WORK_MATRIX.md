# Related Work Matrix and Comparative Taxonomy

This document categorizes foundational and contemporary research related to `research-blob-da`, analyzing each work's consensus model, temporal horizon, verification mechanisms, and functional boundaries.

---

## 1. Comparative Taxonomy

| Citation / Project | Domain & Focus | Consensus Anchor | Availability Horizon | Verification Model | Distinction from research-blob-da |
|---|---|---|---|---|---|
| **EIP-4844** (Buterin et al., 2022) | Core Ethereum Protocol | Ethereum L1 PoS | Temporary ($\approx 18.2$ days) | KZG Commitments & `BLOBHASH` opcode | Defined primitive for L2 rollups; does not address scientific framing or dual-horizon archival. |
| **PeerDAS / EIP-7594** (Feist et al., 2023) | P2P DA Sampling | Ethereum L1 PoS | Temporary | 1D KZG Data Availability Sampling | Protocol scaling upgrade for consensus clients; orthogonal to application payload structuring. |
| **EIP-7623** (Piet et al., 2024) | Calldata Gas Pricing | Ethereum L1 PoS | Permanent/Historical | Execution Gas Floor ($40$ gas/token) | Modifies calldata economics; increases relative cost advantage of blobs. |
| **Celestia** (Al-Bassam et al., 2019) | Modular DA Layer | Tendermint / Cosmos | Permanent / Node-dependent | 2D Reed-Solomon + Namespaced Merkle Trees | Separate sovereign network requiring cross-chain bridging; not native to Ethereum L1. |
| **EigenDA** (Sreeram et al., 2023) | Restaked DA Service | EigenLayer Restakers | Contract-defined | KZG commitments over dispersal nodes | Relies on off-chain quorum of Ethereum restakers rather than native L1 consensus validators. |
| **Avail** (Prabal et al., 2023) | Modular DA Chain | Polkadot / Substrate | Node-dependent | Kate commitments + erasure coding | Separate L1 blockchain requiring separate tokenomics and relay bridges. |
| **IPFS** (Benet, 2014) | P2P Content Addressing | None (DHT / Bitswap) | Volatile / Pin-dependent | Multihash / CID verification | No consensus availability guarantee; used in our system as a durable Horizon-2 backend. |
| **Filecoin** (Protocol Labs, 2017) | Contract Storage Network | Expected Consensus (PoRep/PoSt) | Deal-dependent (180-540 days) | Cryptographic storage proofs | Commercial procurement market with sector sealing latencies; complementary to instant blob publication. |
| **Arweave** (Williams et al., 2019) | Permanent Storage | Proof of Access (SPoRA) | Permanent (~200 yr endowment) | Blockweave hash chain | Independent blockchain with upfront endowment model; complementary to Ethereum L1 anchoring. |
| **FAIR Principles** (Wilkinson et al., 2016) | Scientific Data Governance | Institutional Repositories | Multi-year institutional | DOI / Metadata registries | Conceptual framework; lacks automated cryptographic verification or consensus publication. |
| **RFC 8785 (JCS)** (Rundblad et al., 2020) | JSON Canonicalization | IETF Standard | N/A (Standard) | Deterministic UTF-16 byte sorting | Foundational standard utilized in `research-blob-da` to guarantee bitwise serialization reproducibility. |
| **Zstandard (RFC 8878)** (Collet & Kucherawy, 2021) | High-Ratio Compression | IETF Standard | N/A (Standard) | Finite State Entropy (FSE) | Modern compression codec evaluated across levels 1-19 for structured scientific payloads. |

---

## 2. Key Differentiation of research-blob-da

1. **Non-Rollup Application Model**: While >99% of blob research investigates L2 transaction batch settlement, `research-blob-da` evaluates blobs as an ephemeral publication and peer-review layer for structured scientific datasets.
2. **Hybrid Three-Tiered Commitments**:
   - Blob Versioned Hash (consensus validity)
   - Canonical Content Hash (whole-dataset bitwise integrity)
   - Record-Level Merkle Root (sub-record random access and dispute games)
3. **The Dual-Horizon Archival Bridge**: First implementation demonstrating how transient consensus blobs ($\le 18.2\text{ days}$) can be automatically bound to external content-addressed storage (IPFS/Filecoin/CAS) while preserving full EVM verification after consensus pruning.
