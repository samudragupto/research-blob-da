// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AnchorRegistry} from "../contracts/baselines/AnchorRegistry.sol";
import {CalldataSink} from "../contracts/baselines/CalldataSink.sol";
import {SstoreArchive} from "../contracts/baselines/SstoreArchive.sol";
import {Test} from "forge-std/Test.sol";

contract BaselinesTest is Test {
    CalldataSink private calldataSink;
    SstoreArchive private sstoreArchive;
    AnchorRegistry private anchorRegistry;

    function setUp() public {
        calldataSink = new CalldataSink();
        sstoreArchive = new SstoreArchive();
        anchorRegistry = new AnchorRegistry();
    }

    // -------------------------------------------------------------------------
    // CalldataSink Tests
    // -------------------------------------------------------------------------

    function test_calldataSink_post() public {
        bytes32 datasetId = keccak256("calldata-test-dataset");
        bytes memory chunk = new bytes(1024);
        for (uint256 i = 0; i < 1024; i++) {
            chunk[i] = bytes1(uint8(i % 256));
        }

        vm.expectEmit(true, true, false, true);
        emit CalldataSink.ChunkPosted(datasetId, address(this), 0, keccak256(chunk), 1024);
        calldataSink.post(datasetId, 0, chunk);
    }

    // -------------------------------------------------------------------------
    // SstoreArchive Tests
    // -------------------------------------------------------------------------

    function test_sstoreArchive_store_and_read() public {
        bytes32 datasetId = keccak256("sstore-test-dataset");
        bytes memory chunk = hex"0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20";
        assertEq(chunk.length, 32);

        sstoreArchive.store(datasetId, chunk);

        assertEq(sstoreArchive.wordCount(datasetId), 1);
        assertEq(sstoreArchive.byteLength(datasetId), 32);
        assertEq(sstoreArchive.wordAt(datasetId, 0), bytes32(chunk));

        // Append second chunk
        bytes memory chunk2 = hex"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        sstoreArchive.store(datasetId, chunk2);

        assertEq(sstoreArchive.wordCount(datasetId), 2);
        assertEq(sstoreArchive.byteLength(datasetId), 64);
        assertEq(sstoreArchive.wordAt(datasetId, 1), bytes32(chunk2));
    }

    function test_sstoreArchive_partial_word_padding() public {
        bytes32 datasetId = keccak256("sstore-partial-test");
        // 10 bytes: remaining 22 bytes in the slot must be zeros
        bytes memory chunk = hex"11223344556677889900";
        sstoreArchive.store(datasetId, chunk);

        assertEq(sstoreArchive.wordCount(datasetId), 1);
        assertEq(sstoreArchive.byteLength(datasetId), 10);

        bytes32 stored = sstoreArchive.wordAt(datasetId, 0);
        bytes32 expected = bytes32(hex"1122334455667788990000000000000000000000000000000000000000000000");
        assertEq(stored, expected);

        // Appending to an unaligned dataset must revert
        vm.expectRevert(abi.encodeWithSelector(SstoreArchive.WordsAlreadyWritten.selector, datasetId, 1));
        sstoreArchive.store(datasetId, hex"ff");
    }

    // -------------------------------------------------------------------------
    // AnchorRegistry Tests
    // -------------------------------------------------------------------------

    function test_anchorRegistry_ipfs_and_cloud() public {
        bytes32 datasetId = keccak256("anchor-dataset-1");
        bytes32 digest = keccak256("canonical-dataset-payload");
        bytes memory locator = "ipfs://bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi";

        vm.expectEmit(true, true, false, true);
        emit AnchorRegistry.Anchored(datasetId, address(this), digest, locator);
        anchorRegistry.anchor(datasetId, digest, locator);

        (bytes32 storedDigest, address owner, uint64 ts) = anchorRegistry.anchors(datasetId);
        assertEq(storedDigest, digest);
        assertEq(owner, address(this));
        assertEq(ts, block.timestamp);

        // Duplicate anchor reverts
        vm.expectRevert(abi.encodeWithSelector(AnchorRegistry.AnchorExists.selector, datasetId));
        anchorRegistry.anchor(datasetId, digest, locator);
    }
}
