"""
EIP-4844 Blob Retriever and Sidecar Handler.

Provides dual retrieval paths:
1. `LocalMockRetriever`: High-speed local cache for reproducible experiments, unit tests, and offline demonstrations.
   Supports simulating the ~18.2-day consensus client pruning window.
2. `BeaconNodeRetriever`: Production consensus client REST API client for Ethereum testnets (Sepolia, Holesky) and Mainnet:
   Calls `/eth/v1/beacon/blob_sidecars/{block_id}` and matches versioned hashes against commitments.

Pruning awareness:
Clearly detects and reports when blobs have expired past the 4096-epoch retention boundary.
"""

import hashlib
import os
import time
from typing import Any

import requests

from .encoder import BYTES_PER_BLOB


class BlobPrunedError(Exception):
    """Raised when consensus clients have pruned blob sidecars past the ~18.2-day retention window."""


class LocalMockRetriever:
    """Local blob sidecar storage simulation for benchmarks and tests."""

    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = cache_dir or os.path.join("data", "blob_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_store: dict[str, tuple[bytes, float]] = {}

    def store_blob(
        self, versioned_hash: bytes, blob_bytes: bytes, timestamp: float | None = None
    ) -> None:
        """Stores a blob in memory and on disk keyed by versioned hash."""
        assert len(blob_bytes) == BYTES_PER_BLOB
        ts = timestamp if timestamp is not None else time.time()
        vh_hex = versioned_hash.hex()
        self.memory_store[vh_hex] = (blob_bytes, ts)

        filepath = os.path.join(self.cache_dir, f"{vh_hex}.blob")
        with open(filepath, "wb") as f:
            f.write(blob_bytes)

    def retrieve_blob(
        self, versioned_hash: bytes, max_age_seconds: float | None = None
    ) -> bytes:
        """Retrieves blob bytes by versioned hash, enforcing retention window if specified."""
        vh_hex = versioned_hash.hex()
        ts = 0.0
        blob_bytes: bytes | None = None

        if vh_hex in self.memory_store:
            blob_bytes, ts = self.memory_store[vh_hex]
        else:
            filepath = os.path.join(self.cache_dir, f"{vh_hex}.blob")
            if os.path.exists(filepath):
                ts = os.path.getmtime(filepath)
                with open(filepath, "rb") as f:
                    blob_bytes = f.read()

        if blob_bytes is None:
            raise KeyError(f"Blob with versioned hash 0x{vh_hex} not found")

        if max_age_seconds is not None:
            age = time.time() - ts
            if age > max_age_seconds:
                raise BlobPrunedError(
                    f"Blob 0x{vh_hex} has expired (age {age:.1f}s > max {max_age_seconds:.1f}s)"
                )

        return blob_bytes

    def retrieve_all(
        self, versioned_hashes: list[bytes], max_age_seconds: float | None = None
    ) -> list[bytes]:
        """Retrieves an ordered list of blobs."""
        return [
            self.retrieve_blob(vh, max_age_seconds=max_age_seconds)
            for vh in versioned_hashes
        ]


class BeaconNodeRetriever:
    """Consensus client REST API client for retrieving live blob sidecars."""

    def __init__(self, beacon_rpc_url: str):
        self.beacon_rpc_url = beacon_rpc_url.rstrip("/")

    def get_blob_sidecars(self, block_id: str) -> list[dict[str, Any]]:
        """Queries /eth/v1/beacon/blob_sidecars/{block_id}.

        Args:
            block_id: Block root, slot number, or 'head' / 'finalized'.

        Returns:
            List of blob sidecar objects from consensus API.
        """
        endpoint = f"{self.beacon_rpc_url}/eth/v1/beacon/blob_sidecars/{block_id}"
        headers = {"Accept": "application/json"}
        try:
            resp = requests.get(endpoint, headers=headers, timeout=30)
            if resp.status_code == 404:
                raise BlobPrunedError(
                    f"Block or blobs for '{block_id}' not found or pruned from consensus client"
                )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Beacon node query failed: {e}") from e

    def retrieve_blobs_by_versioned_hashes(
        self, block_id: str, expected_versioned_hashes: list[bytes]
    ) -> list[bytes]:
        """Fetches sidecars from block and matches against expected versioned hashes."""
        sidecars = self.get_blob_sidecars(block_id)
        if not sidecars:
            raise BlobPrunedError(f"No blob sidecars returned for block {block_id}")

        retrieved: dict[bytes, bytes] = {}
        for sc in sidecars:
            kzg_commitment_hex = sc["kzg_commitment"]
            kzg_commitment = bytes.fromhex(kzg_commitment_hex.removeprefix("0x"))
            # Compute versioned hash: 0x01 || sha256(commitment)[1:]
            vh = b"\x01" + hashlib.sha256(kzg_commitment).digest()[1:]

            blob_hex = sc["blob"]
            blob_bytes = bytes.fromhex(blob_hex.removeprefix("0x"))
            retrieved[vh] = blob_bytes

        result: list[bytes] = []
        for target_vh in expected_versioned_hashes:
            if target_vh not in retrieved:
                raise KeyError(
                    f"Expected versioned hash 0x{target_vh.hex()} not found in block {block_id}"
                )
            result.append(retrieved[target_vh])

        return result
