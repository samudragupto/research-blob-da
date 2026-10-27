"""
Position-binding binary Merkle tree and property commitments for research datasets.

Domain Separation:
- Leaf: keccak256(0x00 || keccak256(record_bytes))
- Node: keccak256(0x01 || left_child || right_child)
- Empty padding: bytes32(0)

Strictly mirrors `contracts/libraries/MerkleLib.sol`.
"""

import json
from math import ceil, log2

from Crypto.Hash import keccak

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
ZERO_BYTES32 = b"\x00" * 32


def keccak256(data: bytes) -> bytes:
    """Computes standard Ethereum keccak256 hash."""
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()


def hash_leaf(record_hash: bytes) -> bytes:
    """Computes leaf hash from a 32-byte record hash: keccak256(0x00 || record_hash)."""
    assert len(record_hash) == 32, "record_hash must be 32 bytes"
    return keccak256(LEAF_PREFIX + record_hash)


def hash_record(record_bytes: bytes) -> bytes:
    """Hashes arbitrary record bytes into a Merkle leaf."""
    rec_digest = keccak256(record_bytes)
    return hash_leaf(rec_digest)


def hash_node(left: bytes, right: bytes) -> bytes:
    """Computes parent node from two child hashes: keccak256(0x01 || left || right)."""
    assert len(left) == 32 and len(right) == 32, "children must be 32 bytes"
    return keccak256(NODE_PREFIX + left + right)


def depth_for(leaf_count: int) -> int:
    """Returns tree depth ceil(log2(leaf_count)) for leaf_count >= 1."""
    if leaf_count <= 0:
        raise ValueError("leaf_count must be > 0")
    if leaf_count == 1:
        return 0
    return ceil(log2(leaf_count))


class MerkleTree:
    """Position-binding binary Merkle tree over logical records."""

    def __init__(
        self, records: list[bytes] | None = None, leaves: list[bytes] | None = None
    ):
        if records is not None:
            self.leaves = [hash_record(r) for r in records]
        elif leaves is not None:
            self.leaves = list(leaves)
        else:
            raise ValueError("Must provide either records or leaves")

        self.leaf_count = len(self.leaves)
        if self.leaf_count == 0:
            raise ValueError("Cannot construct Merkle tree with 0 leaves")

        self.depth = depth_for(self.leaf_count)
        self.padded_size = 1 << self.depth
        self.levels: list[list[bytes]] = []
        self._build_tree()

    def _build_tree(self) -> None:
        """Constructs tree layers from leaves up to the root."""
        # Layer 0: pad to next power of 2 with ZERO_BYTES32
        current = list(self.leaves)
        while len(current) < self.padded_size:
            current.append(ZERO_BYTES32)
        self.levels.append(current)

        while len(current) > 1:
            next_level: list[bytes] = []
            for i in range(0, len(current), 2):
                next_level.append(hash_node(current[i], current[i + 1]))
            self.levels.append(next_level)
            current = next_level

    @property
    def root(self) -> bytes:
        """32-byte root hash."""
        return self.levels[-1][0]

    def get_proof(self, index: int) -> list[bytes]:
        """Generates single-leaf inclusion proof for record at `index`.

        Args:
            index: 0-indexed position.

        Returns:
            List of sibling hashes from leaf level up to the root.
        """
        if index < 0 or index >= self.leaf_count:
            raise IndexError(
                f"Index {index} out of bounds for {self.leaf_count} leaves"
            )

        proof: list[bytes] = []
        idx = index
        for d in range(self.depth):
            sibling_idx = idx + 1 if (idx % 2 == 0) else idx - 1
            proof.append(self.levels[d][sibling_idx])
            idx //= 2
        return proof

    def get_range_proof(self, start: int, length: int) -> list[bytes]:
        """Generates contiguous range proof for records [start, start + length).

        Returns boundary siblings matching MerkleLib.verifyRange.
        """
        if length <= 0 or start < 0 or start + length > self.leaf_count:
            raise ValueError("Invalid range specification")

        proof: list[bytes] = []
        lo = start
        hi = start + length - 1

        for d in range(self.depth):
            nlo = lo >> 1
            nhi = hi >> 1
            width = nhi - nlo + 1
            for i in range(width):
                l_idx = (nlo + i) << 1
                if l_idx < lo:
                    proof.append(self.levels[d][l_idx])
                if l_idx + 1 > hi:
                    proof.append(self.levels[d][l_idx + 1])
            lo = nlo
            hi = nhi

        return proof


def verify_proof(
    root: bytes, leaf_count: int, index: int, leaf: bytes, proof: list[bytes]
) -> bool:
    """Verifies single-leaf inclusion proof."""
    if leaf_count <= 0 or index < 0 or index >= leaf_count:
        return False
    d = depth_for(leaf_count)
    if len(proof) != d:
        return False
    h = leaf
    idx = index
    for sibling in proof:
        if idx % 2 == 0:
            h = hash_node(h, sibling)
        else:
            h = hash_node(sibling, h)
        idx //= 2
    return h == root


def verify_range_proof(
    root: bytes, leaf_count: int, start: int, leaves: list[bytes], proof: list[bytes]
) -> bool:
    """Verifies contiguous range proof."""
    n = len(leaves)
    if n == 0 or leaf_count <= 0 or start < 0 or n > leaf_count - start:
        return False
    d = depth_for(leaf_count)
    curr_leaves = list(leaves)
    lo = start
    hi = start + n - 1
    p_idx = 0

    for _ in range(d):
        nlo = lo >> 1
        nhi = hi >> 1
        width = nhi - nlo + 1
        next_leaves = [ZERO_BYTES32] * width

        for i in range(width):
            l = (nlo + i) << 1
            if l < lo:
                if p_idx >= len(proof):
                    return False
                left = proof[p_idx]
                p_idx += 1
            else:
                left = curr_leaves[l - lo]

            if l + 1 > hi:
                if p_idx >= len(proof):
                    return False
                right = proof[p_idx]
                p_idx += 1
            else:
                right = curr_leaves[l + 1 - lo]

            next_leaves[i] = hash_node(left, right)

        curr_leaves = next_leaves
        lo = nlo
        hi = nhi

    return p_idx == len(proof) and curr_leaves[0] == root


def summarize_property(
    records: list[bytes], key: str, decimals: int
) -> tuple[int, int, int, int]:
    """Scans canonical JSON records and extracts (min, max, sum, count) scaled by 10^decimals.

    Returns:
        (min_val, max_val, sum_val, count) as fixed-point integers.
    """
    scale = 10**decimals
    vals: list[int] = []

    for i, r in enumerate(records):
        data = json.loads(r.decode("utf-8"))
        if key not in data:
            raise ValueError(f"Key '{key}' missing in record {i}")
        val = data[key]
        if not isinstance(val, (int, float)):
            raise TypeError(f"Value for '{key}' in record {i} is not numeric: {val}")
        # Scale to fixed point
        fixed_val = round(float(val) * scale)
        vals.append(fixed_val)

    return min(vals), max(vals), sum(vals), len(vals)


def find_violating_record(
    records: list[bytes], key: str, decimals: int, min_val: int, max_val: int
) -> int | None:
    """Finds index of the first record violating [min_val, max_val] for on-chain refutation."""
    scale = 10**decimals
    for i, r in enumerate(records):
        try:
            data = json.loads(r.decode("utf-8"))
            if key not in data:
                return i  # Missing key is a violation
            val = data[key]
            if not isinstance(val, (int, float)):
                return i
            fixed_val = round(float(val) * scale)
            if fixed_val < min_val or fixed_val > max_val:
                return i
        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
        ):
            return i
    return None
