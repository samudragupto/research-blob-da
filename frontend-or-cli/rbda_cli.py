#!/usr/bin/env python3
"""
rbda_cli.py: Command-line interface for research-blob-da.

Provides end-to-end tooling for researchers to encode, commit, retrieve, verify,
and optimistically claim/refute properties of datasets anchored on EIP-4844 blobs.
"""

import argparse
import csv
import json
import os
import sys
from typing import Any

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass

from python.canonical import (
    compute_content_hash,
    deserialize_record_stream,
    serialize_record_stream,
)
from python.commitments import (
    MerkleTree,
    find_violating_record,
    summarize_property,
)
from python.decoder import decode_dataset
from python.encoder import (
    BYTES_PER_BLOB,
    encode_dataset,
)
from python.retriever import BeaconNodeRetriever, LocalMockRetriever


def load_records_from_file(filepath: str) -> list[dict[str, Any]]:
    """Loads records from JSON, JSONL, or CSV file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric strings where appropriate
                parsed_row: dict[str, Any] = {}
                for k, v in row.items():
                    try:
                        parsed_row[k] = float(v) if "." in v else int(v)
                    except ValueError:
                        parsed_row[k] = v
                records.append(parsed_row)
        return records
    elif ext == ".jsonl":
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    else:  # Assume .json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise TypeError(
                    f"Unsupported JSON format: expected list or object, got {type(data)}"
                )


def cmd_encode(args: argparse.Namespace) -> None:
    """Encodes a dataset into EIP-4844 blob files and generates a manifest."""
    records = load_records_from_file(args.input)
    codec = 1 if args.codec == "zstd" else 0
    packing = 1 if args.packing == "fe254" else 0

    print(f"[INFO] Loaded {len(records)} records from {args.input}")
    print(
        f"[INFO] Encoding with codec={args.codec}, packing={args.packing}, zstd_level={args.zstd_level}..."
    )

    encoded = encode_dataset(
        records=records,
        codec=codec,
        packing=packing,
        zstd_level=args.zstd_level,
    )

    os.makedirs(args.out_dir, exist_ok=True)

    # Save individual 128 KiB blob binary files
    for idx, blob in enumerate(encoded.blobs):
        blob_path = os.path.join(args.out_dir, f"blob_{idx}.bin")
        with open(blob_path, "wb") as f:
            f.write(blob)

    # Write manifest
    manifest = encoded.to_manifest()
    manifest_path = os.path.join(args.out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Cache blobs in LocalMockRetriever if requested
    if args.cache:
        retriever = LocalMockRetriever()
        for vh, b in zip(encoded.versioned_hashes, encoded.blobs):
            retriever.store_blob(vh, b)
        print(f"[INFO] Cached {len(encoded.blobs)} blobs in local sidecar cache.")

    print("[SUCCESS] Encoding complete.")
    print(f"  Blobs produced:      {len(encoded.blobs)}")
    print(f"  Raw payload size:    {encoded.raw_size} bytes")
    print(f"  Compressed size:     {encoded.encoded_size} bytes")
    print(f"  Compression ratio:   {encoded.compression_ratio:.2f}x")
    print(f"  Records Merkle Root: 0x{encoded.records_root.hex()}")
    print(f"  Content Hash:        0x{encoded.content_hash.hex()}")
    print(f"  Manifest written:    {manifest_path}")


def cmd_commit(args: argparse.Namespace) -> None:
    """Generates cryptographic commitments and EVM calldata parameters."""
    records = load_records_from_file(args.input)
    raw_stream = serialize_record_stream(records)
    canonical_records = deserialize_record_stream(raw_stream)
    content_hash = compute_content_hash(raw_stream)
    tree = MerkleTree(records=canonical_records)

    print("[COMMITMENTS]")
    print(f"  Record count:         {len(records)}")
    print(f"  Canonical stream len: {len(raw_stream)} bytes")
    print(f"  Content Hash:         0x{content_hash.hex()}")
    print(f"  Records Merkle Root:  0x{tree.root.hex()}")
    print(f"  Merkle Tree Depth:    {tree.depth}")
    print("\n[EVM CALLDATA HELPER]")
    print(f"  recordsRoot: bytes32 = 0x{tree.root.hex()}")
    print(f"  contentHash: bytes32 = 0x{content_hash.hex()}")
    print(f"  totalRecords: uint32 = {len(records)}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verifies blob sidecars against a manifest."""
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    blob_count = manifest["blob_count"]
    expected_root = bytes.fromhex(manifest["records_root"][2:])
    expected_content_hash = bytes.fromhex(manifest["content_hash"][2:])

    blobs: list[bytes] = []
    for idx in range(blob_count):
        blob_path = os.path.join(args.blobs_dir, f"blob_{idx}.bin")
        if not os.path.exists(blob_path):
            raise FileNotFoundError(f"Missing required blob file: {blob_path}")
        with open(blob_path, "rb") as f:
            blob_bytes = f.read()
        assert (
            len(blob_bytes) == BYTES_PER_BLOB
        ), f"Invalid blob size: {len(blob_bytes)}"
        blobs.append(blob_bytes)

    print(f"[INFO] Loaded {len(blobs)} blobs from {args.blobs_dir}")
    print(
        "[INFO] Verifying field-element headers, unpacking stream, and checking commitments..."
    )

    decoded = decode_dataset(
        blobs=blobs,
        expected_content_hash=expected_content_hash,
        expected_records_root=expected_root,
    )

    print("[SUCCESS] All cryptographic verifications passed:")
    print(f"  Reconstructed records: {decoded.record_count}")
    print(f"  Raw payload size:      {decoded.raw_size} bytes")
    print(f"  Records Merkle Root:   0x{decoded.records_root.hex()} (MATCH)")
    print(f"  Content Hash:          0x{decoded.content_hash.hex()} (MATCH)")


def cmd_retrieve(args: argparse.Namespace) -> None:
    """Retrieves blob sidecars from local cache or consensus client, reassembles and saves dataset."""
    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    vhs = [bytes.fromhex(vh[2:]) for vh in manifest["blob_versioned_hashes"]]
    expected_root = bytes.fromhex(manifest["records_root"][2:])
    expected_content_hash = bytes.fromhex(manifest["content_hash"][2:])

    if args.source == "local":
        retriever = LocalMockRetriever(cache_dir=args.cache_dir)
        print(f"[INFO] Retrieving {len(vhs)} blobs from local sidecar cache...")
        blobs = retriever.retrieve_all(vhs, max_age_seconds=args.max_age)
    elif args.source == "beacon":
        if not args.beacon_url:
            raise ValueError("--beacon-url is required when source=beacon")
        b_retriever = BeaconNodeRetriever(beacon_rpc_url=args.beacon_url)
        print(
            f"[INFO] Querying beacon node at {args.beacon_url} for block {args.block_id}..."
        )
        sidecars = b_retriever.get_blob_sidecars(args.block_id)
        blobs = [bytes.fromhex(sc["blob"][2:]) for sc in sidecars]
    else:
        raise ValueError(f"Unknown retrieval source: {args.source}")

    decoded = decode_dataset(
        blobs=blobs,
        expected_content_hash=expected_content_hash,
        expected_records_root=expected_root,
    )

    records = [json.loads(r.decode("utf-8")) for r in decoded.records]
    os.makedirs(os.path.dirname(os.path.abspath(args.out_file)), exist_ok=True)
    with open(args.out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"[SUCCESS] Reconstructed dataset saved to {args.out_file}")
    print(f"  Total records: {len(records)}")
    print(f"  Payload size:  {decoded.raw_size} bytes")


def cmd_claim(args: argparse.Namespace) -> None:
    """Inspects dataset and prepares an on-chain property claim."""
    records_raw = load_records_from_file(args.input)
    raw_stream = serialize_record_stream(records_raw)
    canonical_records = deserialize_record_stream(raw_stream)

    min_v, max_v, sum_v, count = summarize_property(
        records=canonical_records,
        key=args.key,
        decimals=args.scale,
    )

    print(f"[PROPERTY SUMMARY: '{args.key}']")
    print(f"  Record count:     {count}")
    print(f"  Scale exponent:   10^{args.scale}")
    print(f"  Min value (scaled): {min_v} ({min_v / (10 ** args.scale)})")
    print(f"  Max value (scaled): {max_v} ({max_v / (10 ** args.scale)})")
    print(
        f"  Mean (scaled):      {sum_v / count:.2f} ({(sum_v / count) / (10 ** args.scale):.4f})"
    )
    print("\n[ON-CHAIN CLAIM PARAMETERS]")
    print(f"  datasetId:    bytes32 = {args.dataset_id}")
    print(f'  propertyKey:  string  = "{args.key}"')
    print(f"  scale:        uint8   = {args.scale}")
    print(f"  claimedMin:   int64   = {min_v}")
    print(f"  claimedMax:   int64   = {max_v}")
    print(f"  challengeDur: uint32  = {args.challenge_window} seconds")


def cmd_refute(args: argparse.Namespace) -> None:
    """Finds a violating record and generates an on-chain refutation proof."""
    records_raw = load_records_from_file(args.input)
    raw_stream = serialize_record_stream(records_raw)
    canonical_records = deserialize_record_stream(raw_stream)

    violating_idx = find_violating_record(
        records=canonical_records,
        key=args.key,
        decimals=args.scale,
        min_val=args.claimed_min,
        max_val=args.claimed_max,
    )

    if violating_idx is None:
        print(
            f"[INFO] No violation found. The claim [{args.claimed_min}, {args.claimed_max}] for '{args.key}' holds."
        )
        return

    violating_record = canonical_records[violating_idx]
    tree = MerkleTree(records=canonical_records)
    proof = tree.get_proof(violating_idx)

    print("[VIOLATION DETECTED]")
    print(f"  Violating record index: {violating_idx}")
    print(f"  Record content:         {violating_record.decode('utf-8')}")
    print(f"  Merkle Proof Siblings:  {len(proof)}")
    print("\n[REFUTATION CALLDATA PARAMETERS]")
    print(f"  datasetId:   bytes32   = {args.dataset_id}")
    print(f"  claimIndex:  uint256   = {args.claim_index}")
    print(f"  recordIndex: uint32    = {violating_idx}")
    print(f'  recordBytes: bytes     = hex"{violating_record.hex()}"')
    print(f'  proof:       bytes32[] = [{", ".join("0x" + p.hex() for p in proof)}]')


def main() -> None:
    parser = argparse.ArgumentParser(
        description="research-blob-da: Verifiable Research Data Availability on EIP-4844 Blobs"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Encode command
    p_encode = subparsers.add_parser(
        "encode", help="Encode dataset into EIP-4844 blobs"
    )
    p_encode.add_argument(
        "--input", "-i", required=True, help="Input CSV, JSON, or JSONL file"
    )
    p_encode.add_argument(
        "--out-dir",
        "-o",
        default="data/encoded",
        help="Output directory for blobs and manifest",
    )
    p_encode.add_argument(
        "--codec", choices=["zstd", "raw"], default="zstd", help="Compression codec"
    )
    p_encode.add_argument(
        "--packing",
        choices=["fe31", "fe254"],
        default="fe31",
        help="Field element packing mode",
    )
    p_encode.add_argument(
        "--zstd-level", type=int, default=3, help="Zstandard compression level (1-22)"
    )
    p_encode.add_argument(
        "--cache", action="store_true", help="Store blobs into local sidecar cache"
    )
    p_encode.set_defaults(func=cmd_encode)

    # Commit command
    p_commit = subparsers.add_parser(
        "commit", help="Compute canonical commitments and EVM calldata"
    )
    p_commit.add_argument("--input", "-i", required=True, help="Input dataset file")
    p_commit.set_defaults(func=cmd_commit)

    # Verify command
    p_verify = subparsers.add_parser(
        "verify", help="Verify blob sidecars against manifest"
    )
    p_verify.add_argument(
        "--manifest", "-m", required=True, help="Path to manifest.json"
    )
    p_verify.add_argument(
        "--blobs-dir", "-b", required=True, help="Directory containing blob_*.bin files"
    )
    p_verify.set_defaults(func=cmd_verify)

    # Retrieve command
    p_retrieve = subparsers.add_parser(
        "retrieve", help="Retrieve blob sidecars and reconstruct dataset"
    )
    p_retrieve.add_argument(
        "--manifest", "-m", required=True, help="Path to manifest.json"
    )
    p_retrieve.add_argument(
        "--out-file", "-o", required=True, help="Path to write reconstructed records"
    )
    p_retrieve.add_argument(
        "--source",
        choices=["local", "beacon"],
        default="local",
        help="Sidecar retrieval backend",
    )
    p_retrieve.add_argument(
        "--cache-dir", default=None, help="Directory of local blob cache"
    )
    p_retrieve.add_argument(
        "--beacon-url", default=None, help="Consensus client REST API URL"
    )
    p_retrieve.add_argument(
        "--block-id", default="head", help="Beacon block ID for sidecar lookup"
    )
    p_retrieve.add_argument(
        "--max-age",
        type=float,
        default=None,
        help="Maximum allowed sidecar age in seconds",
    )
    p_retrieve.set_defaults(func=cmd_retrieve)

    # Claim command
    p_claim = subparsers.add_parser(
        "claim", help="Summarize property and format on-chain claim"
    )
    p_claim.add_argument("--input", "-i", required=True, help="Input dataset file")
    p_claim.add_argument(
        "--dataset-id", default="0x" + "00" * 32, help="Hex dataset ID"
    )
    p_claim.add_argument(
        "--key", "-k", required=True, help="JSON property key to claim"
    )
    p_claim.add_argument(
        "--scale", "-s", type=int, default=2, help="Decimal scale exponent (10^scale)"
    )
    p_claim.add_argument(
        "--challenge-window",
        type=int,
        default=86400,
        help="Challenge window in seconds",
    )
    p_claim.set_defaults(func=cmd_claim)

    # Refute command
    p_refute = subparsers.add_parser(
        "refute", help="Find violating record and produce refutation proof"
    )
    p_refute.add_argument("--input", "-i", required=True, help="Input dataset file")
    p_refute.add_argument(
        "--dataset-id", default="0x" + "00" * 32, help="Hex dataset ID"
    )
    p_refute.add_argument(
        "--claim-index", type=int, default=0, help="Claim index on contract"
    )
    p_refute.add_argument("--key", "-k", required=True, help="JSON property key")
    p_refute.add_argument(
        "--scale", "-s", type=int, default=2, help="Decimal scale exponent"
    )
    p_refute.add_argument(
        "--claimed-min", type=int, required=True, help="Claimed min value (scaled)"
    )
    p_refute.add_argument(
        "--claimed-max", type=int, required=True, help="Claimed max value (scaled)"
    )
    p_refute.set_defaults(func=cmd_refute)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
