"""
test_archival_bridge.py: Pytest Suite for Dual-Horizon Archival Bridge.

Validates:
1. Deterministic CIDv1 generation (multihash / base32).
2. Content-Addressed Store put and get operations.
3. Dual-horizon publication, expiry simulation, and post-expiry verification.
4. Cryptographic parity between reconstructed archival payload and on-chain commitments.
5. Detection of tampered archival bytes.
"""

import os

import pytest

from python.archival_bridge import (
    ContentAddressedStore,
    DualHorizonBridge,
    compute_cidv1_raw_sha256,
)


@pytest.fixture
def temp_bridge(tmp_path):
    cas_dir = tmp_path / "cas"
    blob_dir = tmp_path / "blobs"
    cas = ContentAddressedStore(str(cas_dir))
    bridge = DualHorizonBridge(cas_store=cas, blob_cache_dir=str(blob_dir))
    return bridge


def test_cidv1_generation():
    data = b"Hello Scientific Archival World!"
    cid = compute_cidv1_raw_sha256(data)
    assert cid.startswith("b")
    # Deterministic check
    assert cid == compute_cidv1_raw_sha256(data)


def test_content_addressed_store(tmp_path):
    cas = ContentAddressedStore(str(tmp_path / "cas"))
    payload = b"ARCHIVAL_DATA_PAYLOAD_TEST_123"
    cid = cas.put(payload)
    assert cas.has(cid)
    retrieved = cas.get(cid)
    assert retrieved == payload


def test_dual_horizon_lifecycle(temp_bridge):
    sample_records = [
        {"id": 1, "observation": "TEMP_23.4C", "station": "STATION_ALPHA"},
        {"id": 2, "observation": "TEMP_24.1C", "station": "STATION_BETA"},
    ]
    ds_id = "0xdeadbeef11223344"

    # 1. Publish
    pub_rec = temp_bridge.publish_dual_horizon(sample_records, ds_id)
    assert pub_rec["record_count"] == 2
    assert pub_rec["blob_count"] >= 1
    assert "archival_cid" in pub_rec

    # Verify blob files exist
    blob_files = [
        f for f in os.listdir(temp_bridge.blob_cache_dir) if f.startswith(ds_id)
    ]
    assert len(blob_files) == pub_rec["blob_count"]

    # 2. Simulate Blob Expiry
    purged = temp_bridge.simulate_blob_expiry(ds_id)
    assert purged == pub_rec["blob_count"]
    # Ensure blob cache is now empty for this dataset
    remaining = [
        f for f in os.listdir(temp_bridge.blob_cache_dir) if f.startswith(ds_id)
    ]
    assert len(remaining) == 0

    # 3. Reconstruct and Verify exclusively from CAS
    recon_res = temp_bridge.reconstruct_from_archive_and_verify(pub_rec)
    assert recon_res["status"] == "VERIFIED_POST_EXPIRY"
    assert recon_res["sha256_verified"] is True
    assert recon_res["content_hash_verified"] is True
    assert recon_res["records_root_verified"] is True


def test_tampered_archival_payload_detected(temp_bridge):
    sample_records = [{"id": 1, "value": "ORIGINAL_VALUE"}]
    ds_id = "0x99998888"

    pub_rec = temp_bridge.publish_dual_horizon(sample_records, ds_id)
    cid = pub_rec["archival_cid"]

    # Corrupt data in CAS
    cas_path = os.path.join(temp_bridge.cas.root_dir, cid)
    with open(cas_path, "wb") as f:
        f.write(b"CORRUPTED_BYTES_IN_ARCHIVE")

    # Verification must fail
    with pytest.raises(AssertionError):
        temp_bridge.reconstruct_from_archive_and_verify(pub_rec)
