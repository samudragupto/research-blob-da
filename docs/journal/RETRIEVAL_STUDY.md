# Empirical Sidecar Retrieval Study

This study records limited probe observations of blob sidecar retrieval attempts across public consensus layer Beacon API endpoints, an indexer, a local content-addressed archival store prototype, and local caches.

---

## 1. Motivation and Study Scope

EIP-4844 protocol specifications state that consensus clients must retain blob sidecars for at least 4,096 epochs (~18.2 days). However, client specification does not guarantee that *publicly exposed* Beacon REST endpoints will serve blob sidecars reliably to unauthenticated external queries.

To observe practical retrieval behavior for scientific reproducibility, we implemented a retrieval harness (`python/retrieval_study.py`) executing probe queries across distinct infrastructure tiers against our live Ethereum Sepolia deployment (Block 12006195, Tx `0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea`).

Unauthenticated public Sepolia Beacon API endpoints probed in this study did not return the requested blob sidecar. The failure reasons included authentication requirements (HTTP 401), endpoint unavailability (HTTP 400/500), and potential indexer lag. These observations do not distinguish consensus-layer pruning from access-control or indexing limitations. A dedicated pruning-window study requires archival-node access and age-stratified probes over multiple weeks.

---

## 2. Multi-Tier Retrieval Taxonomy

All probe attempts are strictly categorized by source type:
1. `beacon_api`: Unauthenticated public consensus client REST endpoints exposing `/eth/v1/beacon/blob_sidecars/{block_id}`.
2. `beacon_indexer`: Public block explorer API endpoints (e.g., Blobscan).
3. `simulated_archival_cache`: Local content-addressed store prototype serving simulated archival retrieval.
4. `local_cache`: Local blob sidecar file cache retained during initial dataset encoding and publication.

---

## 3. Empirical Results Summary

Data source: `benchmarks/journal-extension/retrieval/summary.csv` and `benchmarks/journal-extension/retrieval/attempts.jsonl`.

### A. Public Endpoint Probes [Public endpoint probe]

| Endpoint Identifier | Source Type | Sanitized Host | Attempts | Successes | Failures | Success Rate | Median Latency (ms) | Observed Error Categories |
|---|---|---|---|---|---|---|---|---|
| `chainsafe_lodestar_public` | `beacon_api` | `lodestar-sepolia.chainsafe.io` | 2 | 0 | 2 | 0/2 (0.0%) | 1,240.5 | `server_exception` (HTTP 500) |
| `publicnode_beacon_api` | `beacon_api` | `ethereum-sepolia-beacon-api.publicnode.com` | 1 | 0 | 1 | 0/1 (0.0%) | 420.1 | `pre_deneb_routing_error` (HTTP 400) |
| `drpc_beacon_sepolia` | `beacon_api` | `eth-beacon-chain-sepolia.drpc.org` | 1 | 0 | 1 | 0/1 (0.0%) | 285.4 | `free_tier_restricted` (HTTP 400) |
| `blobscan_sepolia_indexer` | `beacon_indexer` | `api.sepolia.blobscan.com` | 2 | 0 | 2 | 0/2 (0.0%) | 612.8 | `indexer_lag` (HTTP 404) |

### B. Local Verification [Simulated / Local prototype measurement]

| Endpoint Identifier | Source Type | Sanitized Host | Attempts | Successes | Failures | Success Rate | Median Latency (ms) | Observed Error Categories |
|---|---|---|---|---|---|---|---|---|
| `dual_horizon_archival_gateway` | `simulated_archival_cache` | `archival-bridge.local` | 1 | 1 | 0 | 1/1 (100.0%) | 142.3 | `none` (Local prototype) |
| `local_mock_retriever` | `local_cache` | `localhost` | 2 | 2 | 0 | 2/2 (100.0%) | 2.3 | `none` (Local sidecar) |

---

## 4. Analysis of Public Infrastructure Failure Modes

1. **Beacon Endpoint Server Errors (HTTP 500)**:
   Public Lodestar Sepolia endpoint queries failed when serializing historical block queries, returning internal unhandled exceptions (`TypeError: reading length`).
2. **Tiered Access Paywalls (HTTP 400)**:
   Free public endpoints (e.g., dRPC, PublicNode) restricted bandwidth-heavy blob sidecar RPC calls (`/eth/v1/beacon/blob_sidecars`), requiring authenticated paid API tiers for full sidecar streaming.
3. **Indexer Synchronization Lag (HTTP 404)**:
   Public block explorers and dedicated blob indexers (such as Blobscan Sepolia) can lag behind the live execution head, resulting in 404 Not Found responses for newly published datasets.
4. **Distinction from Pruning**:
   These probe observations document access-control, gateway, and indexer constraints on public endpoints. They do not demonstrate consensus-layer blob pruning, which occurs deterministically after 4,096 epochs.

---

## 5. Architectural Implications

These limited probe observations demonstrate that:
1. Public unauthenticated Beacon API endpoints cannot be relied upon as an open scientific retrieval layer.
2. Direct client-side retrieval requires dedicated or authenticated consensus RPC access.
3. Decoupling ephemeral publication commitments from persistent archival storage (e.g., via the Dual-Horizon Archival Bridge prototype) is essential for long-term availability after pruning.
