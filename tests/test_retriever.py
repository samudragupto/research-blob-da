"""
Unit tests for EIP-4844 blob sidecar retriever and pruning simulation.
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from python.encoder import BYTES_PER_BLOB, compute_kzg_versioned_hash
from python.retriever import (
    BeaconNodeRetriever,
    BlobPrunedError,
    LocalMockRetriever,
)


def test_local_retriever_store_and_retrieve(tmp_path):
    retriever = LocalMockRetriever(cache_dir=str(tmp_path))
    blob = os.urandom(BYTES_PER_BLOB)
    vh = compute_kzg_versioned_hash(blob)

    retriever.store_blob(vh, blob)
    retrieved = retriever.retrieve_blob(vh)
    assert retrieved == blob


def test_local_retriever_missing_blob(tmp_path):
    retriever = LocalMockRetriever(cache_dir=str(tmp_path))
    vh = b"\x01" + b"\x00" * 31
    with pytest.raises(KeyError, match="not found"):
        retriever.retrieve_blob(vh)


def test_local_retriever_pruning_expiration(tmp_path):
    retriever = LocalMockRetriever(cache_dir=str(tmp_path))
    blob = os.urandom(BYTES_PER_BLOB)
    vh = compute_kzg_versioned_hash(blob)

    # Store with historical timestamp (e.g., 20 days ago)
    twenty_days_ago = time.time() - (20 * 86400)
    retriever.store_blob(vh, blob, timestamp=twenty_days_ago)

    # Max age of 18.2 days (~1,572,480 seconds)
    max_age = 18.2 * 86400
    with pytest.raises(BlobPrunedError, match="has expired"):
        retriever.retrieve_blob(vh, max_age_seconds=max_age)

    # Without max_age_seconds, retrieval succeeds from disk/memory
    assert retriever.retrieve_blob(vh, max_age_seconds=None) == blob


def test_local_retriever_retrieve_all(tmp_path):
    retriever = LocalMockRetriever(cache_dir=str(tmp_path))
    blobs = [os.urandom(BYTES_PER_BLOB) for _ in range(3)]
    vhs = [compute_kzg_versioned_hash(b) for b in blobs]

    for vh, b in zip(vhs, blobs):
        retriever.store_blob(vh, b)

    retrieved = retriever.retrieve_all(vhs)
    assert retrieved == blobs


def test_beacon_node_retriever_success():
    retriever = BeaconNodeRetriever("http://localhost:5052")
    dummy_sidecar = {
        "index": "0",
        "blob": "0x" + ("00" * BYTES_PER_BLOB),
        "kzg_commitment": "0x" + ("11" * 48),
        "kzg_proof": "0x" + ("22" * 48),
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [dummy_sidecar]}

    with patch("requests.get", return_value=mock_resp):
        sidecars = retriever.get_blob_sidecars("head")
        assert len(sidecars) == 1
        assert sidecars[0]["index"] == "0"


def test_beacon_node_retriever_pruned_404():
    retriever = BeaconNodeRetriever("http://localhost:5052")
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with (
        patch("requests.get", return_value=mock_resp),
        pytest.raises(BlobPrunedError, match="pruned"),
    ):
        retriever.get_blob_sidecars("100000")


def test_beacon_node_retriever_error_500():
    retriever = BeaconNodeRetriever("http://localhost:5052")
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = requests.HTTPError("Server error")

    with (
        patch("requests.get", return_value=mock_resp),
        pytest.raises(RuntimeError, match="Beacon node query failed"),
    ):
        retriever.get_blob_sidecars("head")
