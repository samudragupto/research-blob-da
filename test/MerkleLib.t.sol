// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {MerkleLib} from "../contracts/libraries/MerkleLib.sol";
import {Test} from "forge-std/Test.sol";

contract MerkleLibTest is Test {
    function test_hash_domain_separation() public pure {
        bytes32 raw = keccak256("test-record");
        bytes32 leaf = MerkleLib.hashLeaf(raw);
        // Leaf prefix is 0x00
        bytes32 expectedLeaf = keccak256(abi.encodePacked(bytes1(0x00), raw));
        assertEq(leaf, expectedLeaf);

        bytes32 left = keccak256("left");
        bytes32 right = keccak256("right");
        bytes32 node = MerkleLib.hashNode(left, right);
        // Node prefix is 0x01
        bytes32 expectedNode = keccak256(abi.encodePacked(bytes1(0x01), left, right));
        assertEq(node, expectedNode);

        // Ensure leaf and node hashes never collide for identical 32-byte content
        bytes32 leafFromZero = MerkleLib.hashLeaf(bytes32(0));
        bytes32 nodeFromZeros = MerkleLib.hashNode(bytes32(0), bytes32(0));
        assertTrue(leafFromZero != nodeFromZeros);
    }

    function test_depthFor() public pure {
        assertEq(MerkleLib.depthFor(1), 0);
        assertEq(MerkleLib.depthFor(2), 1);
        assertEq(MerkleLib.depthFor(3), 2);
        assertEq(MerkleLib.depthFor(4), 2);
        assertEq(MerkleLib.depthFor(5), 3);
        assertEq(MerkleLib.depthFor(8), 3);
        assertEq(MerkleLib.depthFor(9), 4);
        assertEq(MerkleLib.depthFor(1024), 10);
        assertEq(MerkleLib.depthFor(1025), 11);
    }

    function depthForExternal(uint256 n) external pure returns (uint256) {
        return MerkleLib.depthFor(n);
    }

    function test_empty_tree_reverts() public {
        vm.expectRevert(MerkleLib.EmptyTree.selector);
        this.depthForExternal(0);
    }

    function test_manual_two_leaves() public pure {
        bytes memory r0 = '{"val":10}';
        bytes memory r1 = '{"val":20}';
        bytes32 l0 = MerkleLib.hashRecord(r0);
        bytes32 l1 = MerkleLib.hashRecord(r1);
        bytes32 root = MerkleLib.hashNode(l0, l1);

        bytes32[] memory proof0 = new bytes32[](1);
        proof0[0] = l1;
        assertTrue(MerkleLib.verifyMemory(root, 2, 0, l0, proof0));

        bytes32[] memory proof1 = new bytes32[](1);
        proof1[0] = l0;
        assertTrue(MerkleLib.verifyMemory(root, 2, 1, l1, proof1));

        // Wrong index
        assertFalse(MerkleLib.verifyMemory(root, 2, 1, l0, proof0));
        // Wrong proof
        proof0[0] = bytes32(uint256(12_345));
        assertFalse(MerkleLib.verifyMemory(root, 2, 0, l0, proof0));
        // Out of bounds index
        assertFalse(MerkleLib.verifyMemory(root, 2, 2, l0, proof0));
    }

    function test_fuzz_merkle_tree_inclusion(uint8 countSeed, uint8 indexSeed) public pure {
        uint256 n = (uint256(countSeed) % 31) + 1; // 1 to 31 leaves
        uint256 targetIdx = uint256(indexSeed) % n;

        // Build leaves
        bytes32[] memory leaves = new bytes32[](n);
        for (uint256 i = 0; i < n; i++) {
            leaves[i] = MerkleLib.hashRecord(abi.encodePacked("record-", i));
        }

        uint256 depth = MerkleLib.depthFor(n);
        uint256 paddedSize = 1 << depth;
        bytes32[] memory currentLevel = new bytes32[](paddedSize);
        for (uint256 i = 0; i < paddedSize; i++) {
            currentLevel[i] = i < n ? leaves[i] : bytes32(0);
        }

        bytes32[] memory proof = new bytes32[](depth);
        uint256 idx = targetIdx;

        for (uint256 d = 0; d < depth; d++) {
            uint256 sibling = (idx % 2 == 0) ? idx + 1 : idx - 1;
            proof[d] = currentLevel[sibling];

            uint256 nextSize = currentLevel.length / 2;
            bytes32[] memory nextLevel = new bytes32[](nextSize);
            for (uint256 i = 0; i < nextSize; i++) {
                nextLevel[i] = MerkleLib.hashNode(currentLevel[2 * i], currentLevel[2 * i + 1]);
            }
            currentLevel = nextLevel;
            idx /= 2;
        }

        bytes32 root = currentLevel[0];

        // Valid proof check
        assertTrue(MerkleLib.verifyMemory(root, n, targetIdx, leaves[targetIdx], proof));

        // Invalid: tampered leaf
        assertFalse(MerkleLib.verifyMemory(root, n, targetIdx, keccak256("tampered"), proof));

        // Invalid: index out of bounds
        assertFalse(MerkleLib.verifyMemory(root, n, n, leaves[targetIdx], proof));
    }

    function test_range_proof_verification() public pure {
        // Build 4-leaf tree
        uint256 n = 4;
        bytes32[] memory leaves = new bytes32[](n);
        for (uint256 i = 0; i < n; i++) {
            leaves[i] = MerkleLib.hashRecord(abi.encodePacked("range-leaf-", i));
        }
        bytes32 n01 = MerkleLib.hashNode(leaves[0], leaves[1]);
        bytes32 n23 = MerkleLib.hashNode(leaves[2], leaves[3]);
        bytes32 root = MerkleLib.hashNode(n01, n23);

        // Prove range [1, 2] (length 2)
        // At level 0: lo=1 (odd -> needs left sibling leaves[0]), hi=2 (even -> needs right sibling leaves[3])
        // Next level: lo=0, hi=1 (covers full root, no boundary needed)
        bytes32[] memory rangeLeaves = new bytes32[](2);
        rangeLeaves[0] = leaves[1];
        rangeLeaves[1] = leaves[2];

        bytes32[] memory proof = new bytes32[](2);
        proof[0] = leaves[0];
        proof[1] = leaves[3];

        assertTrue(MerkleLib.verifyRangeMemory(root, n, 1, rangeLeaves, proof));

        // Tampered leaf in range
        rangeLeaves[0] = keccak256("bad");
        assertFalse(MerkleLib.verifyRangeMemory(root, n, 1, rangeLeaves, proof));
    }
}
