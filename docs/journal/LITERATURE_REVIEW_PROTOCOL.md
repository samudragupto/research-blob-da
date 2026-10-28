# Systematic Literature Review Protocol

This protocol defines the systematic search, filtering, evaluation, and categorization methodology for related work in `research-blob-da`.

---

## 1. Objectives and Scope

The review evaluates research at the intersection of:
1. **Ethereum Protocol & Data Availability**: EIP-4844, PeerDAS (EIP-7594), EIP-7623, EIP-7691, multi-dimensional gas markets, and polynomial commitments.
2. **Dedicated Modular Data-Availability Networks**: Celestia, EigenDA, Avail.
3. **Decentralized Storage & Content-Addressed Systems**: IPFS, Filecoin, Arweave.
4. **Reproducible Scientific Computing & Artifact Provenance**: FAIR data principles, on-chain scientific registries, verifiable machine learning training traces, and cryptographic dataset versioning.

---

## 2. Search Methodology and Databases

- **Databases Queried**: IEEE Xplore, ACM Digital Library, Google Scholar, arXiv, Europe PMC, OpenAlex, and Ethereum Improvement Proposals (EIPs) Repository.
- **Search Date**: October 2026.
- **Representative Query Strings**:
  - `("EIP-4844" OR "blobs" OR "proto-danksharding") AND ("data availability" OR "storage")`
  - `("data availability" OR "modular blockchain") AND ("scientific data" OR "reproducibility" OR "provenance")`
  - `("KZG commitments" OR "polynomial commitments") AND ("dataset verification" OR "blockchain")`
  - `("decentralized science" OR "DeSci") AND ("data availability" OR "archival")`

---

## 3. Inclusion and Exclusion Criteria

### 3.1 Inclusion Criteria
1. Primary protocol specifications and peer-reviewed conference/journal papers.
2. Formally accepted Ethereum Improvement Proposals (EIPs) and consensus specs.
3. Foundational cryptography papers (e.g., KZG polynomial commitments).
4. Standards tracks (IETF RFCs for JSON canonicalization and Zstandard).
5. Work providing concrete empirical evaluations or architectural designs of DA layers.

### 3.2 Exclusion Criteria
1. Unsubstantiated marketing blog posts or anonymous forum comments without verifiable specifications.
2. Speculative cryptocurrency trading analyses.
3. Outdated pre-Cancun proposals superseded by the live Deneb hard fork.

---

## 4. Novelty Positioning and Scope Delineation

Existing EIP-4844 research focuses almost exclusively on **Layer-2 Rollups** (e.g., Optimism, Arbitrum, Base, Starknet), evaluating how blob gas markets compress transaction settlement costs for financial rollups.

**The specific novelty of `research-blob-da` is:**
> To our knowledge, this is one of the first reproducible evaluations of EIP-4844 blobs as a temporary publication layer for structured scientific and machine-learning research artifacts, combined with a dual-horizon content-addressed archival bridge for long-term preservation.

Prior works that narrowed this claim:
- Rollup cost studies (e.g. L2Beat, Dune Analytics) focus solely on transaction batches rather than structured scientific schemas.
- Decentralized science (DeSci) projects previously relied on IPFS or Arweave without consensus-enforced L1 publication or EVM dispute games.
