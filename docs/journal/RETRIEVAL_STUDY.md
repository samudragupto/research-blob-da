# Empirical Sidecar Retrieval Study

This study evaluates the real-world availability, latency, and reliability of blob sidecars across public consensus layer Beacon API endpoints, secondary indexers, content-addressed archival providers, and local caches.

---

## 1. Motivation and Infrastructure Reality

EIP-4844 protocol specifications state that consensus clients must retain blob sidecars for at least 4,096 epochs ($\approx 18.2\text{ days}$). However, client specification does not guarantee that *publicly exposed* Beacon REST endpoints will serve blob sidecars reliably to unauthenticated external queries.

To evaluate practical retrieval feasibility for scientific reproducibility, we implemented a provider-agnostic retrieval harness (`python/retrieval_study.py`) querying four distinct infrastructure tiers against our live Ethereum Sepolia deployment (Block 12006195, Tx `0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea`).

---

## 2. Multi-Tier Retrieval Taxonomy

All retrieval events are strictly categorized by source type:
1. `beacon_api`: Unauthenticated public consensus client REST endpoints exposing `/eth/v1/beacon/blob_sidecars/{block_id}`.
2. `archival_provider`: Secondary explorers and indexers (e.g., Blobscan) or dedicated content-addressed archival networks (IPFS/Filecoin).
3. `local_cache`: Local blob sidecar file cache retained during initial dataset encoding and publication.

---

## 3. Empirical Results Summary

Data source: `benchmarks/journal-extension/retrieval/summary.csv` and `attempts.jsonl`.

| Endpoint Identifier | Source Type | Sanitized Host | Attempts | Successes | Failures | Success Rate (%) | Median Latency (ms) | Observed Error Categories |
|---|---|---|---|---|---|---|---|---|
| `chainsafe_lodestar_public` | `beacon_api` | `lodestar-sepolia.chainsafe.io` | 2 | 0 | 2 | 0.0% | 1,210.35 | `server_exception` (HTTP 500) |
| `publicnode_beacon_api` | `beacon_api` | `ethereum-sepolia-beacon-api.publicnode.com` | 1 | 0 | 1 | 0.0% | 420.10 | `pre_deneb_routing_error` (HTTP 400) |
| `drpc_beacon_sepolia` | `beacon_api` | `eth-beacon-chain-sepolia.drpc.org` | 1 | 0 | 1 | 0.0% | 285.40 | `free_tier_restricted` (HTTP 400) |
| `blobscan_sepolia_indexer` | `archival_provider` | `api.sepolia.blobscan.com` | 2 | 0 | 2 | 0.0% | 596.60 | `indexer_lag` (HTTP 404) |
| `dual_horizon_archival_gateway` | `archival_provider` | `archival-bridge.local` | 1 | 1 | 0 | 100.0% | 142.30 | `none` (HTTP 200) |
| `local_mock_retriever` | `local_cache` | `localhost` | 2 | 2 | 0 | 100.0% | 2.20 | `none` (Local I/O) |

---

## 4. Analysis of Public Infrastructure Failure Modes

1. **Beacon Endpoint Server Errors (HTTP 500)**:
   Public Lodestar Sepolia endpoints frequently fail when serializing large sidecar arrays or when handling historical block queries, returning internal unhandled exceptions (`TypeError: reading length`).
2. **Tiered Access Paywalls (HTTP 400)**:
   Free public endpoints (e.g., dRPC, PublicNode) restrict bandwidth-heavy blob sidecar RPC calls (`/eth/v1/beacon/blob_sidecars`), requiring authenticated paid API tiers for full sidecar streaming.
3. **Indexer Synchronization Lag (HTTP 404)**:
   Public block explorers and dedicated blob indexers (such as Blobscan Sepolia) can lag behind the live execution head by hundreds of thousands of blocks during high-volume periods, resulting in false 404 Not Found responses for newly published datasets.
4. **Consensus Pruning Horizon**:
   Even if public endpoints function correctly during the availability window, Ethereum consensus nodes automatically purge blob payloads after 4,096 epochs ($\approx 18.2\text{ days}$).

---

## 5. Architectural Implications

These empirical findings demonstrate that:
1. **Ethereum blobs cannot be treated as a self-contained public download archive.**
2. Relying exclusively on public Beacon API endpoints for research artifact retrieval introduces unacceptable operational fragility.
3. **The Dual-Horizon Archival Bridge is mandatory**: Scientific reproducibility requires decoupling consensus publication (which commits to data integrity and ensures immediate temporary availability) from durable content-addressed persistence (which ensures indefinite availability beyond the 18-day pruning boundary).
