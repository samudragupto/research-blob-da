// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title MerkleLib
/// @author research-blob-da
/// @notice Position-binding binary Merkle tree used to commit to the logical records of a research dataset
///         that is physically carried in EIP-4844 blobs.
/// @dev Research rationale. A blob versioned hash commits to 128 KiB of opaque field elements through a KZG
///      commitment. It says nothing about the *logical* structure of the data (rows, trace events, log lines),
///      and once the blob is pruned (~18 days) the versioned hash alone cannot be used to check any statement
///      about an individual record. This library provides the complementary, layout-independent commitment:
///
///      - Leaves are domain-separated: `leaf = keccak256(0x00 || keccak256(record))`.
///      - Internal nodes are domain-separated: `node = keccak256(0x01 || left || right)`.
///        The two prefixes rule out second-preimage attacks in which an internal node is presented as a leaf.
///      - The tree is ordered by record index (pairs are *not* sorted), so a proof also proves the position
///        of a record. Citing "row 1 337 of dataset X" is a meaningful, verifiable statement.
///      - The leaf layer is padded to the next power of two with `bytes32(0)`; padded internal nodes are
///        `Z[k+1] = node(Z[k], Z[k])`. The leaf count is stored next to the root on-chain, and every
///        verification checks `index < leafCount` and `proof.length == depth(leafCount)`. Without the stored
///        leaf count, padding would make the committed record count ambiguous.
///
///      The off-chain reference implementation lives in `python/commitments.py` and is tested for
///      byte-for-byte agreement with this library (see `test/vectors/merkle_vectors.json`).
library MerkleLib {
    /// @notice Thrown when a tree with zero leaves is used.
    error EmptyTree();

    /// @dev Domain-separation prefix for leaves.
    bytes1 internal constant LEAF_PREFIX = 0x00;
    /// @dev Domain-separation prefix for internal nodes.
    bytes1 internal constant NODE_PREFIX = 0x01;

    /// @notice Hashes raw record bytes into a leaf.
    /// @param record Canonical record bytes (for tabular data: canonical JSON of one row).
    /// @return leaf The domain-separated leaf hash.
    function hashRecord(bytes memory record) internal pure returns (bytes32 leaf) {
        return hashLeaf(keccak256(record));
    }

    /// @notice Hashes a precomputed record hash into a leaf.
    /// @dev Accepting the record hash (instead of the record) lets light clients prove inclusion of a record
    ///      whose bytes are too large to pass as calldata.
    /// @param recordHash `keccak256(record)`.
    /// @return leaf `keccak256(0x00 || recordHash)`.
    function hashLeaf(bytes32 recordHash) internal pure returns (bytes32 leaf) {
        assembly ("memory-safe") {
            mstore(0x01, recordHash)
            mstore8(0x00, 0x00)
            leaf := keccak256(0x00, 0x21)
        }
    }

    /// @notice Hashes two children into their parent.
    /// @dev Uses memory past the free-memory pointer as scratch space without advancing it, which the
    ///      Solidity documentation defines as memory-safe. 65 bytes do not fit into the 64-byte scratch area.
    /// @param left Left child.
    /// @param right Right child.
    /// @return node `keccak256(0x01 || left || right)`.
    function hashNode(bytes32 left, bytes32 right) internal pure returns (bytes32 node) {
        assembly ("memory-safe") {
            let ptr := mload(0x40)
            mstore8(ptr, 0x01)
            mstore(add(ptr, 0x01), left)
            mstore(add(ptr, 0x21), right)
            node := keccak256(ptr, 0x41)
        }
    }

    /// @notice Depth of a padded tree with `leafCount` leaves, i.e. `ceil(log2(leafCount))`.
    /// @param leafCount Number of real leaves. Must be non-zero.
    /// @return depth Number of sibling hashes in an inclusion proof.
    function depthFor(uint256 leafCount) internal pure returns (uint256 depth) {
        if (leafCount == 0) revert EmptyTree();
        uint256 n = leafCount - 1;
        while (n != 0) {
            n >>= 1;
            unchecked {
                ++depth;
            }
        }
    }

    /// @notice Verifies a single-leaf inclusion proof (calldata version).
    function verify(bytes32 root, uint256 leafCount, uint256 index, bytes32 leaf, bytes32[] calldata proof)
        internal
        pure
        returns (bool)
    {
        if (leafCount == 0 || index >= leafCount) return false;
        uint256 depth = depthFor(leafCount);
        if (proof.length != depth) return false;
        bytes32 h = leaf;
        for (uint256 i; i < depth;) {
            h = (index & 1 == 0) ? hashNode(h, proof[i]) : hashNode(proof[i], h);
            index >>= 1;
            unchecked {
                ++i;
            }
        }
        return h == root;
    }

    /// @notice Verifies a single-leaf inclusion proof (memory version).
    function verifyMemory(
        bytes32 root,
        uint256 leafCount,
        uint256 index,
        bytes32 leaf,
        bytes32[] memory proof
    ) internal pure returns (bool) {
        if (leafCount == 0 || index >= leafCount) return false;
        uint256 depth = depthFor(leafCount);
        if (proof.length != depth) return false;
        bytes32 h = leaf;
        for (uint256 i; i < depth;) {
            h = (index & 1 == 0) ? hashNode(h, proof[i]) : hashNode(proof[i], h);
            index >>= 1;
            unchecked {
                ++i;
            }
        }
        return h == root;
    }

    /// @notice Verifies that a contiguous run of leaves `[start, start + leaves.length)` is committed (calldata).
    function verifyRange(
        bytes32 root,
        uint256 leafCount,
        uint256 start,
        bytes32[] memory leaves,
        bytes32[] calldata proof
    ) internal pure returns (bool) {
        uint256 n = leaves.length;
        if (n == 0 || leafCount == 0 || start >= leafCount || n > leafCount - start) return false;
        uint256 depth = depthFor(leafCount);
        uint256 lo = start;
        uint256 hi = start + n - 1;
        uint256 p;
        for (uint256 d; d < depth;) {
            uint256 nlo = lo >> 1;
            uint256 nhi = hi >> 1;
            uint256 width = nhi - nlo + 1;
            for (uint256 i; i < width;) {
                uint256 l = (nlo + i) << 1;
                bytes32 left;
                bytes32 right;
                if (l < lo) {
                    if (p >= proof.length) return false;
                    left = proof[p];
                    unchecked {
                        ++p;
                    }
                } else {
                    left = leaves[l - lo];
                }
                if (l + 1 > hi) {
                    if (p >= proof.length) return false;
                    right = proof[p];
                    unchecked {
                        ++p;
                    }
                } else {
                    right = leaves[l + 1 - lo];
                }
                leaves[i] = hashNode(left, right);
                unchecked {
                    ++i;
                }
            }
            lo = nlo;
            hi = nhi;
            unchecked {
                ++d;
            }
        }
        return p == proof.length && leaves[0] == root;
    }

    /// @notice Verifies that a contiguous run of leaves `[start, start + leaves.length)` is committed (memory).
    function verifyRangeMemory(
        bytes32 root,
        uint256 leafCount,
        uint256 start,
        bytes32[] memory leaves,
        bytes32[] memory proof
    ) internal pure returns (bool) {
        uint256 n = leaves.length;
        if (n == 0 || leafCount == 0 || start >= leafCount || n > leafCount - start) return false;
        uint256 depth = depthFor(leafCount);
        uint256 lo = start;
        uint256 hi = start + n - 1;
        uint256 p;
        for (uint256 d; d < depth;) {
            uint256 nlo = lo >> 1;
            uint256 nhi = hi >> 1;
            uint256 width = nhi - nlo + 1;
            for (uint256 i; i < width;) {
                uint256 l = (nlo + i) << 1;
                bytes32 left;
                bytes32 right;
                if (l < lo) {
                    if (p >= proof.length) return false;
                    left = proof[p];
                    unchecked {
                        ++p;
                    }
                } else {
                    left = leaves[l - lo];
                }
                if (l + 1 > hi) {
                    if (p >= proof.length) return false;
                    right = proof[p];
                    unchecked {
                        ++p;
                    }
                } else {
                    right = leaves[l + 1 - lo];
                }
                leaves[i] = hashNode(left, right);
                unchecked {
                    ++i;
                }
            }
            lo = nlo;
            hi = nhi;
            unchecked {
                ++d;
            }
        }
        return p == proof.length && leaves[0] == root;
    }
}

