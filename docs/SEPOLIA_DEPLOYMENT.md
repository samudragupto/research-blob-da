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

## 7. Deployment Status Policy

If live Sepolia credentials or testnet ETH are not available in the immediate environment, the repository maintains an honest disclosure policy:
- Do not fabricate testnet addresses or transaction hashes.
- Declare deployment status as: `Local simulation complete. Sepolia deployment script ready. Deployment pending a funded Sepolia account.`
- When funded, populate `deployments/sepolia_deployment.json` with the real transaction hashes and add verified Sepolia explorer links to `README.md`.
