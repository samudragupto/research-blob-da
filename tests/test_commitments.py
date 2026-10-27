"""
Unit and fuzz tests for Merkle commitments and property checks.
"""

from python.commitments import (
    MerkleTree,
    depth_for,
    find_violating_record,
    hash_leaf,
    hash_node,
    hash_record,
    summarize_property,
    verify_proof,
    verify_range_proof,
)


def test_domain_separation():
    r1 = b"record-data"
    hash_record(r1)

    # Empty node vs leaf
    leaf_zero = hash_leaf(b"\x00" * 32)
    node_zeros = hash_node(b"\x00" * 32, b"\x00" * 32)
    assert leaf_zero != node_zeros


def test_depth_for():
    assert depth_for(1) == 0
    assert depth_for(2) == 1
    assert depth_for(3) == 2
    assert depth_for(4) == 2
    assert depth_for(5) == 3
    assert depth_for(8) == 3
    assert depth_for(9) == 4
    assert depth_for(1024) == 10


def test_merkle_tree_inclusion_proofs():
    records = [f'{{"idx":{i}}}'.encode() for i in range(13)]
    tree = MerkleTree(records=records)
    root = tree.root

    for i in range(len(records)):
        leaf = hash_record(records[i])
        proof = tree.get_proof(i)
        assert verify_proof(root, len(records), i, leaf, proof)

        # Tampered leaf
        assert not verify_proof(root, len(records), i, hash_record(b"bad"), proof)
        # Wrong index
        assert not verify_proof(root, len(records), (i + 1) % len(records), leaf, proof)


def test_merkle_range_proofs():
    records = [f'{{"idx":{i}}}'.encode() for i in range(16)]
    tree = MerkleTree(records=records)
    root = tree.root

    # Range [3, 10) length 7
    start = 3
    length = 7
    range_leaves = [hash_record(records[i]) for i in range(start, start + length)]
    range_proof = tree.get_range_proof(start, length)

    assert verify_range_proof(root, len(records), start, range_leaves, range_proof)

    # Tampered leaf in range
    bad_leaves = list(range_leaves)
    bad_leaves[2] = hash_record(b"corrupted")
    assert not verify_range_proof(root, len(records), start, bad_leaves, range_proof)


def test_property_summarize_and_refutation():
    records = [
        b'{"step":1,"loss":2.45}',
        b'{"step":2,"loss":1.82}',
        b'{"step":3,"loss":4.95}',  # Max
        b'{"step":4,"loss":0.65}',  # Min
    ]
    # loss in [0.00, 5.00], scale 10^2
    min_v, max_v, _sum_v, count = summarize_property(records, "loss", 2)
    assert min_v == 65
    assert max_v == 495
    assert count == 4

    # Verify no violation for honest claim [0, 500]
    violation = find_violating_record(records, "loss", 2, 0, 500)
    assert violation is None

    # False claim: loss <= 3.00 (max=300). Record 2 (loss=4.95 -> 495) must be found as violation
    violating_idx = find_violating_record(records, "loss", 2, 0, 300)
    assert violating_idx == 2
