# Ethereum Sepolia Deployment and Testnet Verification Guide

**Author:** Arrhat Nag (GitHub: samudragupto)  
**Project:** research-blob-da (v0.1.0)  
**Target Network:** Ethereum Sepolia (Chain ID: 11155111)

This document provides a step-by-step operational guide to deploy `DatasetRegistry`, post EIP-4844 Type-3 blob transactions carrying research datasets, retrieve blob sidecars via consensus clients, and reconstruct the dataset with cryptographic verification.

---

## 1. Prerequisites and Environment Setup

### 1.1 Account Funding
A funded Sepolia account is required to pay for execution gas and blob gas:
- Public faucets: [Sepolia PoW Faucet](https://sepolia-faucet.pk910.de/), [Alchemy Sepolia Faucet](https://www.alchemy.com/faucets/ethereum-sepolia), or [Infura Sepolia Faucet](https://www.infura.io/faucet/sepolia).
- Recommended minimum balance: 0.1 Sepolia ETH.

### 1.2 Configuration (.env)
Copy the example environment template and populate your local variables:
```bash
cp .env.example .env
```
Ensure the following variables are defined in `.env`:
- `SEPOLIA_RPC_URL`: JSON-RPC endpoint for Sepolia execution layer.
- `PRIVATE_KEY`: Hex-encoded 32-byte private key for the funded deployer account.
- `BEACON_API_URL`: Consensus layer REST API endpoint (e.g., `https://lodestar-sepolia.chainsafe.io`).
- `ETHERSCAN_API_KEY`: API key for automated contract verification on Etherscan.

---

## 2. Deploying the DatasetRegistry Contract

Deploy `DatasetRegistry` and baseline benchmark contracts using Foundry:

```bash
source .env
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  -vvvv
```

Foundry will output the deployed contract addresses:
- `DatasetRegistry`: `0x...`
- `CalldataSink`: `0x...`
- `SstoreArchive`: `0x...`
- `AnchorRegistry`: `0x...`

Export the deployed registry address:
```bash
export REGISTRY_ADDRESS="0x<DEPLOYED_REGISTRY_ADDRESS>"
```
Record these addresses in `deployments/sepolia_deployment.json` using the schema in `deployments/sepolia_deployment.example.json`.

---

## 3. Encoding a Dataset for EIP-4844 Posting

Select a dataset (e.g., the committed OpenAlex academic metadata) and encode it into canonical EIP-4844 blobs:

```bash
python frontend-or-cli/rbda_cli.py encode \
  --input data/real_academic_openalex.json \
  --output data/encoded_sepolia \
  --codec 1 \
  --packing 0
```

This outputs:
- `data/encoded_sepolia/manifest.json`: Cryptographic manifest containing `records_root`, `content_hash`, and blob metadata.
- `data/encoded_sepolia/blob_0.bin`: Exactly 131,072-byte binary blob sidecar with field element packing.

---

## 4. Submitting the EIP-4844 Type-3 Blob Transaction

Broadcast the Type-3 transaction carrying the blob sidecars and registering the dataset in `DatasetRegistry`:

### Option A: Using the TypeScript Broadcast Utility
```bash
npx tsx frontend-or-cli/ts/src/blob_tx.ts \
  data/encoded_sepolia/manifest.json \
  data/encoded_sepolia
```

### Option B: Using Foundry Script Simulation / Broadcast
```bash
REGISTRY_ADDRESS=$REGISTRY_ADDRESS \
forge script script/PostBlobDataset.s.sol:PostBlobDatasetScript \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  -vvvv
```

The broadcast output displays:
- Transaction Hash: `0x...`
- Block Number: `...`
- Gas Used and Blob Gas Used (131,072 blob gas per blob).
- Versioned Hash (0x01 prefix).

---

## 5. Critical: Blob Sidecar Retrieval Before Pruning

> [!WARNING]
> **Blob Retention Window:** Consensus clients only store blob sidecars for approximately 4096 epochs (18.2 days on Ethereum mainnet and Sepolia). After this horizon, blobs are permanently pruned from consensus nodes.
> Archival nodes, indexers, or data consumers MUST download sidecars within this retention window.

Immediately after block inclusion, retrieve the blob sidecar from the consensus layer beacon API:

```bash
# Query beacon block blob sidecars by block root or slot number
curl -s -X GET "${BEACON_API_URL}/eth/v1/beacon/blob_sidecars/${SLOT_OR_BLOCK_ID}" \
  -H "Accept: application/json" > data/retrieved_sidecar.json
```

Or retrieve using the Python client:
```bash
python -c "
from python.retriever import BeaconNodeRetriever
retriever = BeaconNodeRetriever(beacon_url='${BEACON_API_URL}')
blobs = retriever.retrieve_blob_sidecars('${BLOCK_ID}')
print(f'Successfully downloaded {len(blobs)} blob sidecars.')
"
```

---

## 6. Dataset Reconstruction and Verification

Reconstruct the original dataset from retrieved blob sidecars and verify full cryptographic integrity:

```bash
python frontend-or-cli/rbda_cli.py verify \
  --manifest data/encoded_sepolia/manifest.json \
  --blobs data/encoded_sepolia \
  --registry-address $REGISTRY_ADDRESS \
  --rpc-url $SEPOLIA_RPC_URL
```

Verification validates:
1. `content_hash`: Matches `keccak256(canonical_stream)` bit-for-bit.
2. `records_root`: Merkle tree recomputed over decoded records matches the on-chain root.
3. `versioned_hashes`: BLS KZG commitments match the on-chain hashes recorded by `BLOBHASH`.

---

## 7. Deployment and Retrieval Verification Status

- **Network:** Ethereum Sepolia (Chain ID: 11155111)
- **DatasetRegistry Contract:** [`0x238dE56E52A3F6C6708952052e6a20E5102b4d5b`](https://sepolia.etherscan.io/address/0x238dE56E52A3F6C6708952052e6a20E5102b4d5b)
- **Deployment Transaction:** [`0xa55af2b2a6ec29cc706bd8e5ebc166d6ae3130002c183f7ebdbb8186cc834751`](https://sepolia.etherscan.io/tx/0xa55af2b2a6ec29cc706bd8e5ebc166d6ae3130002c183f7ebdbb8186cc834751) (Block: 12006103)
- **Live EIP-4844 Blob Transaction:** [`0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea`](https://sepolia.etherscan.io/tx/0x9631459f3ee3c26a2113ec9e5d9aee06dc1107435f387596c95a5fd912c7f7ea) (Block: 12006195)
- **Dataset ID:** `0x4f7b50bd684170f2c427d8975ee6478fadbc46918b764f1e8a4915374bf9d29b`
- **KZG Versioned Hash:** `0x010e6c7880a790abbedd746b98b713b5780e8e662d9f57f31cc51671b01faf11`
- **Blob Gas Used:** 131,072
- **Records Root:** `0x6120e0c2e0712d0eca82b57aa8581dd02cbbb3bddf8136b7976aa63421544064`
- **Content Hash:** `0x46b91d8c2a4535a190e8f36f551cdb6f32512dbc1e5b802bb3320aca167ff686`
- **Retrieval Verification Outcome:**
  Retrieval verified on 2026-10-27 16:28:44 UTC from the local cache: the blob sidecar was retrieved, the dataset was reconstructed, and the reconstructed canonical-payload SHA-256 matched the manifest.
  *Consensus Gateway Disclosure:* Independent live consensus queries to public Sepolia beacon nodes (`lodestar-sepolia.chainsafe.io` and `ethereum-sepolia-beacon-api.publicnode.com`) returned 500 and 400 gateway errors, and the public Blobscan Sepolia indexer head was lagging at block 11,818,175 (~188k blocks behind live block 12,006,195). Reconstructed data was verified from local sidecar cache against on-chain versioned hash and manifest SHA-256, recorded in `deployments/sepolia_retrieval_verification.json`.
