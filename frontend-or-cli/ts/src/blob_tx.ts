/**
 * blob_tx.ts: Broadcasts EIP-4844 Type-3 blob transactions to Ethereum testnets (Sepolia/Holesky).
 *
 * Utilizes `viem` and `c-kzg` to construct, sign, and broadcast blob transactions containing
 * research dataset sidecars and invoking `DatasetRegistry.openDataset` or `appendExternalBlobs`.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import * as cKzg from "c-kzg";
import {
  createWalletClient,
  createPublicClient,
  defineKzg,
  decodeEventLog,
  encodeFunctionData,
  http,
  parseGwei,
  type Hex,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { sepolia } from "viem/chains";

// ABI definition for DatasetRegistry functions and events interacting with blobs
export const DATASET_REGISTRY_ABI = [
  {
    type: "event",
    name: "DatasetOpened",
    inputs: [
      { name: "datasetId", type: "bytes32", indexed: true },
      { name: "researcher", type: "address", indexed: true },
      { name: "recordsRoot", type: "bytes32", indexed: false },
      { name: "contentHash", type: "bytes32", indexed: false },
      { name: "metadataHash", type: "bytes32", indexed: false },
      { name: "recordCount", type: "uint32", indexed: false },
    ],
  },
  {
    type: "event",
    name: "BlobsAppended",
    inputs: [
      { name: "datasetId", type: "bytes32", indexed: true },
      { name: "firstIndex", type: "uint256", indexed: false },
      { name: "versionedHashes", type: "bytes32[]", indexed: false },
      { name: "bound", type: "bool", indexed: false },
    ],
  },
  {
    type: "event",
    name: "DatasetFinalized",
    inputs: [
      { name: "datasetId", type: "bytes32", indexed: true },
      { name: "blobCount", type: "uint256", indexed: false },
      { name: "recordCount", type: "uint256", indexed: false },
    ],
  },
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

let cachedKzg: ReturnType<typeof defineKzg> | null = null;
export function getKzg() {
  if (!cachedKzg) {
    try {
      cKzg.loadTrustedSetup(0);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (!msg.includes("already loaded")) {
        throw err;
      }
    }
    cachedKzg = defineKzg(cKzg);
  }
  return cachedKzg;
}

export function loadEnv(): void {
  const candidates = [
    path.resolve(process.cwd(), ".env"),
    path.resolve(__dirname, "../../.env"),
    path.resolve(__dirname, "../../../.env"),
  ];
  for (const envPath of candidates) {
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, "utf-8");
      for (const rawLine of content.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith("#")) continue;
        const eqIdx = line.indexOf("=");
        if (eqIdx !== -1) {
          const key = line.slice(0, eqIdx).trim();
          let val = line.slice(eqIdx + 1).trim();
          if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
            val = val.slice(1, -1);
          }
          if (!process.env[key]) {
            process.env[key] = val;
          }
        }
      }
      break;
    }
  }
}

export interface PostBlobDatasetConfig {
  rpcUrl: string;
  privateKey: Hex;
  registryAddress: Hex;
  manifestPath: string;
  blobsDir: string;
  maxBlobFeeGwei?: number;
  salt?: Hex;
}

export interface PostBlobResult {
  txHash: Hex;
  blockNumber: bigint;
  gasUsed: bigint;
  blobGasUsed: bigint;
  datasetId?: Hex;
  versionedHashes: Hex[];
}

/**
 * Posts an EIP-4844 transaction carrying research dataset blobs to Ethereum Sepolia.
 */
export async function postBlobDataset(config: PostBlobDatasetConfig): Promise<PostBlobResult> {
  const normalizedKey = config.privateKey.startsWith("0x")
    ? config.privateKey
    : (`0x${config.privateKey}` as Hex);
  const account = privateKeyToAccount(normalizedKey);

  // If connected to Reth node that rejects sidecars in eth_estimateGas, use reliable Geth endpoint
  const targetRpc = config.rpcUrl.includes("alchemy")
    ? "https://ethereum-sepolia-rpc.publicnode.com"
    : config.rpcUrl;

  const publicClient = createPublicClient({
    chain: sepolia,
    transport: http(targetRpc),
  });

  const walletClient = createWalletClient({
    account,
    chain: sepolia,
    transport: http(targetRpc),
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

  console.log(`[INFO] Broadcaster:   ${account.address}`);
  console.log(`[INFO] Registry:      ${config.registryAddress}`);
  console.log(`[INFO] Records Root:  ${manifest.records_root}`);
  console.log(`[INFO] Content Hash:  ${manifest.content_hash}`);
  console.log(`[INFO] Blob Count:    ${blobCount}`);
  console.log(`[INFO] Network RPC:   ${targetRpc}`);

  // 2. Format dataset parameters conforming to IDatasetRegistry.DatasetParams
  const salt =
    config.salt ||
    (("0x" + Buffer.from("rbda-openalex-sepolia-dataset").toString("hex").padEnd(64, "0")) as Hex);
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

  const data = encodeFunctionData({
    abi: DATASET_REGISTRY_ABI,
    functionName: "openDataset",
    args: [salt, datasetParams, BigInt(blobCount), true],
  });

  // 3. Initialize KZG and compute commitments
  const kzg = getKzg();
  const maxFeePerBlobGas = parseGwei(String(config.maxBlobFeeGwei ?? 25));
  const maxFeePerGas = parseGwei("35");
  const maxPriorityFeePerGas = parseGwei("2");

  console.log(`[INFO] Broadcasting EIP-4844 Type-3 transaction to Sepolia...`);

  const txHash = await walletClient.sendTransaction({
    to: config.registryAddress,
    data,
    blobs: rawBlobs,
    kzg,
    maxFeePerBlobGas,
    maxFeePerGas,
    maxPriorityFeePerGas,
    gas: 2_500_000n,
  });

  console.log(`[SUCCESS] Transaction broadcast with hash: ${txHash}`);
  console.log(`  Etherscan: https://sepolia.etherscan.io/tx/${txHash}`);
  console.log(`[INFO] Awaiting block confirmation on Sepolia...`);

  const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
  console.log(`[SUCCESS] Confirmed in block ${receipt.blockNumber}`);
  console.log(`  Status:        ${receipt.status}`);
  console.log(`  Gas used:      ${receipt.gasUsed.toString()}`);
  console.log(`  Blob gas used: ${receipt.blobGasUsed ? receipt.blobGasUsed.toString() : "0"}`);

  let datasetId: Hex | undefined;
  const versionedHashes: Hex[] = [];

  for (const log of receipt.logs) {
    try {
      const decoded = decodeEventLog({
        abi: DATASET_REGISTRY_ABI,
        data: log.data,
        topics: log.topics,
      });
      if (decoded.eventName === "DatasetOpened") {
        datasetId = decoded.args.datasetId;
        console.log(`  Dataset ID:    ${datasetId}`);
      } else if (decoded.eventName === "BlobsAppended") {
        versionedHashes.push(...(decoded.args.versionedHashes as Hex[]));
      }
    } catch {
      // Ignore other logs
    }
  }

  return {
    txHash,
    blockNumber: receipt.blockNumber,
    gasUsed: receipt.gasUsed,
    blobGasUsed: receipt.blobGasUsed || 0n,
    datasetId,
    versionedHashes,
  };
}

// Standalone execution entrypoint
if (require.main === module) {
  loadEnv();

  const rpcUrl = process.env.SEPOLIA_RPC_URL || "https://ethereum-sepolia-rpc.publicnode.com";
  const rawKey = process.env.PRIVATE_KEY || "0x" + "11".repeat(32);
  const privateKey = (rawKey.startsWith("0x") ? rawKey : `0x${rawKey}`) as Hex;
  const registryAddress = (process.env.REGISTRY_ADDRESS || "0x" + "00".repeat(20)) as Hex;
  const manifestPath = process.argv[2] || "data/encoded_sepolia/manifest.json";
  const blobsDir = process.argv[3] || "data/encoded_sepolia";
  const maxBlobFeeGwei = Number(process.env.MAX_BLOB_FEE_GWEI || 25);

  postBlobDataset({
    rpcUrl,
    privateKey,
    registryAddress,
    manifestPath,
    blobsDir,
    maxBlobFeeGwei,
  }).catch((err) => {
    console.error(`[ERROR] Failed to post blob dataset:`, err);
    process.exit(1);
  });
}
