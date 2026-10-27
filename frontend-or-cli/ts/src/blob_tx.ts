/**
 * blob_tx.ts: Broadcasts EIP-4844 Type-3 blob transactions to Ethereum testnets (Sepolia/Holesky).
 *
 * Utilizes `viem` to construct, sign, and broadcast blob transactions containing
 * research dataset sidecars and invoking `DatasetRegistry.openDataset` or `appendExternalBlobs`.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import {
  createWalletClient,
  createPublicClient,
  http,
  parseGwei,
  type Hex,
  toHex,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { sepolia } from "viem/chains";

// ABI definition for DatasetRegistry functions interacting with blobs
export const DATASET_REGISTRY_ABI = [
  {
    type: "function",
    name: "openDataset",
    inputs: [
      { name: "salt", type: "bytes32" },
      {
        name: "params",
        type: "tuple",
        components: [
          { name: "recordsRoot", type: "bytes32" },
          { name: "contentHash", type: "bytes32" },
          { name: "metadataHash", type: "bytes32" },
          { name: "rawSize", type: "uint64" },
          { name: "encodedSize", type: "uint64" },
          { name: "recordCount", type: "uint32" },
          { name: "codec", type: "uint8" },
          { name: "layout", type: "uint8" },
          { name: "packing", type: "uint8" },
        ],
      },
      { name: "numTxBlobs", type: "uint256" },
      { name: "finalize_", type: "bool" },
    ],
    outputs: [{ name: "datasetId", type: "bytes32" }],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "appendBlobs",
    inputs: [
      { name: "datasetId", type: "bytes32" },
      { name: "numTxBlobs", type: "uint256" },
      { name: "finalize_", type: "bool" },
    ],
    outputs: [],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "appendExternalBlobs",
    inputs: [
      { name: "datasetId", type: "bytes32" },
      { name: "versionedHashes", type: "bytes32[]" },
      { name: "finalize_", type: "bool" },
    ],
    outputs: [],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "getDataset",
    inputs: [{ name: "datasetId", type: "bytes32" }],
    outputs: [
      {
        name: "",
        type: "tuple",
        components: [
          { name: "researcher", type: "address" },
          { name: "createdAt", type: "uint40" },
          { name: "blobCount", type: "uint32" },
          { name: "externalBlobCount", type: "uint24" },
          { name: "recordsRoot", type: "bytes32" },
          { name: "contentHash", type: "bytes32" },
          { name: "metadataHash", type: "bytes32" },
          { name: "rawSize", type: "uint64" },
          { name: "encodedSize", type: "uint64" },
          { name: "recordCount", type: "uint32" },
          { name: "codec", type: "uint8" },
          { name: "layout", type: "uint8" },
          { name: "packing", type: "uint8" },
          { name: "status", type: "uint8" },
          { name: "firstBlobAt", type: "uint40" },
        ],
      },
    ],
    stateMutability: "view",
  },
] as const;

export interface PostBlobDatasetConfig {
  rpcUrl: string;
  privateKey: Hex;
  registryAddress: Hex;
  manifestPath: string;
  blobsDir: string;
  maxBlobFeeGwei?: number;
}

/**
 * Posts an EIP-4844 transaction carrying research dataset blobs to Ethereum Sepolia.
 */
export async function postBlobDataset(config: PostBlobDatasetConfig): Promise<Hex> {
  const account = privateKeyToAccount(config.privateKey);

  const publicClient = createPublicClient({
    chain: sepolia,
    transport: http(config.rpcUrl),
  });

  const walletClient = createWalletClient({
    account,
    chain: sepolia,
    transport: http(config.rpcUrl),
  });

  // 1. Read manifest and verify blob files
  const manifestRaw = fs.readFileSync(config.manifestPath, "utf-8");
  const manifest = JSON.parse(manifestRaw);

  const blobCount: number = manifest.blob_count;
  if (blobCount > 6) {
    throw new Error(
      `Dataset requires ${blobCount} blobs, but maximum per Ethereum transaction is 6 (Cancun target 3, max 6)`
    );
  }

  const rawBlobs: Uint8Array[] = [];
  for (let i = 0; i < blobCount; i++) {
    const blobPath = path.join(config.blobsDir, `blob_${i}.bin`);
    if (!fs.existsSync(blobPath)) {
      throw new Error(`Missing blob sidecar file: ${blobPath}`);
    }
    const buf = fs.readFileSync(blobPath);
    if (buf.length !== 131072) {
      throw new Error(`Blob ${i} has invalid size ${buf.length} != 131072`);
    }
    rawBlobs.push(new Uint8Array(buf));
  }

  console.log(`[INFO] Preparing Type-3 blob transaction for dataset`);
  console.log(`  Records Root: ${manifest.records_root}`);
  console.log(`  Content Hash: ${manifest.content_hash}`);
  console.log(`  Blob Count:   ${blobCount}`);

  // 2. Format dataset parameters conforming to IDatasetRegistry.DatasetParams
  const salt = ("0x" + Buffer.from("rbda-dataset-salt").toString("hex").padEnd(64, "0")) as Hex;
  const metadataStr = JSON.stringify(manifest.metadata || {});
  const metadataHash = ("0x" + Buffer.from(metadataStr).toString("hex").slice(0, 64).padEnd(64, "0")) as Hex;

  const datasetParams = {
    recordsRoot: manifest.records_root as Hex,
    contentHash: manifest.content_hash as Hex,
    metadataHash,
    rawSize: BigInt(manifest.raw_size || 0),
    encodedSize: BigInt(manifest.encoded_size || 0),
    recordCount: Number(manifest.record_count || 0),
    codec: Number(manifest.codec ?? 1),
    layout: Number(manifest.layout ?? 0),
    packing: Number(manifest.packing ?? 0),
  };

  // 3. Send transaction with blobs attached
  const maxFeePerBlobGas = parseGwei(String(config.maxBlobFeeGwei ?? 15));

  const hash = await walletClient.writeContract({
    address: config.registryAddress,
    abi: DATASET_REGISTRY_ABI,
    functionName: "openDataset",
    args: [salt, datasetParams, BigInt(blobCount), true],
    blobs: rawBlobs,
    maxFeePerBlobGas,
  });

  console.log(`[SUCCESS] Transaction broadcast with hash: ${hash}`);
  console.log(`[INFO] Waiting for block confirmation...`);

  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  console.log(`[SUCCESS] Confirmed in block ${receipt.blockNumber}`);
  console.log(`  Gas used:      ${receipt.gasUsed.toString()}`);
  console.log(`  Blob gas used: ${receipt.blobGasUsed ? receipt.blobGasUsed.toString() : "N/A"}`);

  return hash;
}

// Standalone execution entrypoint
if (require.main === module) {
  const rpcUrl = process.env.SEPOLIA_RPC_URL || "http://localhost:8545";
  const privateKey = (process.env.PRIVATE_KEY || "0x" + "11".repeat(32)) as Hex;
  const registryAddress = (process.env.REGISTRY_ADDRESS || "0x" + "00".repeat(20)) as Hex;
  const manifestPath = process.argv[2] || "data/encoded/manifest.json";
  const blobsDir = process.argv[3] || "data/encoded";

  postBlobDataset({
    rpcUrl,
    privateKey,
    registryAddress,
    manifestPath,
    blobsDir,
  }).catch((err) => {
    console.error(`[ERROR] Failed to post blob dataset:`, err);
    process.exit(1);
  });
}
