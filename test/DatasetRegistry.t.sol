// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DatasetRegistry} from "../contracts/DatasetRegistry.sol";
import {IDatasetRegistry} from "../contracts/interfaces/IDatasetRegistry.sol";
import {BlobLib} from "../contracts/libraries/BlobLib.sol";
import {MerkleLib} from "../contracts/libraries/MerkleLib.sol";
import {Test} from "forge-std/Test.sol";

contract DatasetRegistryTest is Test {
    DatasetRegistry private registry;
    address private researcher = address(0x1111);
    address private challenger = address(0x2222);
    address private attester = address(0x3333);

    uint64 private constant MIN_CHALLENGE_PERIOD = 1 days;

    function setUp() public {
        vm.warp(1_700_000_000); // Set predictable timestamp
        registry = new DatasetRegistry(MIN_CHALLENGE_PERIOD);
    }

    function _mockParams(bytes32 root, uint32 recordCount)
        private
        pure
        returns (IDatasetRegistry.DatasetParams memory)
    {
        return IDatasetRegistry.DatasetParams({
            recordsRoot: root,
            contentHash: keccak256("canonical-stream-bytes"),
            metadataHash: keccak256("manifest-json"),
            rawSize: 200_000,
            encodedSize: 110_000,
            recordCount: recordCount,
            codec: 1, // zstd
            layout: 0, // stream
            packing: 0 // 31 bytes/FE
        });
    }

    function _mockKzgVersionedHash(uint256 seed) private pure returns (bytes32) {
        bytes32 h = keccak256(abi.encodePacked("blob-kzg-seed", seed));
        // Set first byte to 0x01 (BlobLib.VERSIONED_HASH_VERSION_KZG)
        return (h & 0x00ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff)
            | bytes32(uint256(0x01) << 248);
    }

    // -------------------------------------------------------------------------
    // Dataset Registration Lifecycle
    // -------------------------------------------------------------------------

    function test_openDataset_with_blobs_and_finalize() public {
        bytes32 salt = keccak256("dataset-alpha");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);

        bytes32[] memory txBlobs = new bytes32[](2);
        txBlobs[0] = _mockKzgVersionedHash(1);
        txBlobs[1] = _mockKzgVersionedHash(2);
        vm.blobhashes(txBlobs);

        bytes32 root = keccak256("merkle-root-alpha");
        IDatasetRegistry.DatasetParams memory params = _mockParams(root, 100);

        vm.prank(researcher);
        vm.expectEmit(true, true, false, true);
        emit IDatasetRegistry.DatasetOpened(
            datasetId, researcher, root, params.contentHash, params.metadataHash, 100
        );
        bytes32 returnedId = registry.openDataset(salt, params, 2, true);

        assertEq(returnedId, datasetId);

        IDatasetRegistry.Dataset memory d = registry.getDataset(datasetId);
        assertEq(d.researcher, researcher);
        assertEq(uint256(d.status), uint256(IDatasetRegistry.Status.Finalized));
        assertEq(d.blobCount, 2);
        assertEq(d.recordCount, 100);
        assertEq(d.externalBlobCount, 0);
        assertEq(d.firstBlobAt, block.timestamp);

        bytes32[] memory registeredHashes = registry.blobHashes(datasetId);
        assertEq(registeredHashes.length, 2);
        assertEq(registeredHashes[0], txBlobs[0]);
        assertEq(registeredHashes[1], txBlobs[1]);
        assertEq(registry.blobHashAt(datasetId, 0), txBlobs[0]);
        assertEq(registry.blobHashAt(datasetId, 1), txBlobs[1]);

        assertTrue(registry.isWithinRetentionWindow(datasetId));
        assertEq(registry.availabilityDeadline(datasetId), block.timestamp + BlobLib.BLOB_RETENTION_SECONDS);
    }

    function test_multi_tx_append_and_finalize() public {
        bytes32 salt = keccak256("multi-tx-dataset");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);

        // Tx 1: open with 1 blob, do not finalize
        bytes32[] memory txBlobs1 = new bytes32[](1);
        txBlobs1[0] = _mockKzgVersionedHash(10);
        vm.blobhashes(txBlobs1);

        IDatasetRegistry.DatasetParams memory params = _mockParams(keccak256("root"), 50);
        vm.prank(researcher);
        registry.openDataset(salt, params, 1, false);

        IDatasetRegistry.Dataset memory d1 = registry.getDataset(datasetId);
        assertEq(uint256(d1.status), uint256(IDatasetRegistry.Status.Open));
        assertEq(d1.blobCount, 1);

        // Tx 2: append second blob and finalize
        bytes32[] memory txBlobs2 = new bytes32[](1);
        txBlobs2[0] = _mockKzgVersionedHash(20);
        vm.blobhashes(txBlobs2);

        vm.prank(researcher);
        registry.appendBlobs(datasetId, 1, true);

        IDatasetRegistry.Dataset memory d2 = registry.getDataset(datasetId);
        assertEq(uint256(d2.status), uint256(IDatasetRegistry.Status.Finalized));
        assertEq(d2.blobCount, 2);
    }

    function test_appendExternalBlobs() public {
        bytes32 salt = keccak256("external-blob-dataset");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);

        IDatasetRegistry.DatasetParams memory params = _mockParams(keccak256("root"), 20);
        vm.prank(researcher);
        registry.openDataset(salt, params, 0, false);

        bytes32[] memory extBlobs = new bytes32[](2);
        extBlobs[0] = _mockKzgVersionedHash(100);
        extBlobs[1] = _mockKzgVersionedHash(101);

        vm.prank(researcher);
        registry.appendExternalBlobs(datasetId, extBlobs, true);

        IDatasetRegistry.Dataset memory d = registry.getDataset(datasetId);
        assertEq(d.blobCount, 2);
        assertEq(d.externalBlobCount, 2);
        // External blobs disable retention-window claims
        assertFalse(registry.isWithinRetentionWindow(datasetId));
    }

    function test_openDataset_reverts_if_exists() public {
        bytes32 salt = keccak256("duplicate-salt");
        IDatasetRegistry.DatasetParams memory params = _mockParams(keccak256("root"), 10);

        vm.prank(researcher);
        registry.openDataset(salt, params, 0, false);

        bytes32 datasetId = registry.computeDatasetId(researcher, salt);
        vm.prank(researcher);
        vm.expectRevert(abi.encodeWithSelector(IDatasetRegistry.DatasetAlreadyExists.selector, datasetId));
        registry.openDataset(salt, params, 0, false);
    }

    function test_unauthorized_append_reverts() public {
        bytes32 salt = keccak256("auth-test");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);
        IDatasetRegistry.DatasetParams memory params = _mockParams(keccak256("root"), 10);

        vm.prank(researcher);
        registry.openDataset(salt, params, 0, false);

        address attacker = address(0x9999);
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(IDatasetRegistry.NotResearcher.selector, attacker));
        registry.appendBlobs(datasetId, 1, false);
    }

    // -------------------------------------------------------------------------
    // Property Claims and Refutations
    // -------------------------------------------------------------------------

    function test_property_claim_and_refutation_lifecycle() public {
        // Build 2-record dataset
        bytes memory r0 = '{"epoch":1,"loss":2.45}';
        bytes memory r1 = '{"epoch":2,"loss":8.90}'; // Violates loss <= 5.0
        bytes32 l0 = MerkleLib.hashRecord(r0);
        bytes32 l1 = MerkleLib.hashRecord(r1);
        bytes32 root = MerkleLib.hashNode(l0, l1);

        bytes32 salt = keccak256("claims-dataset");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);

        bytes32[] memory txBlobs = new bytes32[](1);
        txBlobs[0] = _mockKzgVersionedHash(500);
        vm.blobhashes(txBlobs);

        IDatasetRegistry.DatasetParams memory params = _mockParams(root, 2);
        vm.prank(researcher);
        registry.openDataset(salt, params, 1, true);

        // Researcher posts claim: loss is between 0.00 and 5.00 (decimals=2 -> min=0, max=500)
        vm.prank(researcher);
        uint256 claimIdx = registry.postClaim(datasetId, "loss", 2, 0, 500, 1000);
        assertEq(claimIdx, 0);
        assertEq(uint256(registry.claimStatus(datasetId, 0)), uint256(IDatasetRegistry.ClaimStatus.Pending));

        // Challenger tries to refute with record 0 (which has loss = 2.45 <= 5.00, NOT a violation)
        bytes32[] memory proof0 = new bytes32[](1);
        proof0[0] = l1;
        vm.prank(challenger);
        vm.expectRevert(IDatasetRegistry.NotAViolation.selector);
        registry.refuteClaim(datasetId, 0, 0, r0, proof0);

        // Challenger refutes with record 1 (loss = 8.90 > 5.00, valid refutation)
        bytes32[] memory proof1 = new bytes32[](1);
        proof1[0] = l0;
        vm.prank(challenger);
        vm.expectEmit(true, true, true, true);
        emit IDatasetRegistry.ClaimRefuted(datasetId, 0, challenger, 1);
        registry.refuteClaim(datasetId, 0, 1, r1, proof1);

        // Status is now Refuted
        assertEq(uint256(registry.claimStatus(datasetId, 0)), uint256(IDatasetRegistry.ClaimStatus.Refuted));

        // Attempting to refute again reverts
        vm.prank(challenger);
        vm.expectRevert(abi.encodeWithSelector(IDatasetRegistry.ClaimAlreadyRefuted.selector, 0));
        registry.refuteClaim(datasetId, 0, 1, r1, proof1);
    }

    function test_unchallenged_claim_after_deadline() public {
        bytes memory r0 = '{"epoch":1,"acc":95.5}';
        bytes32 root = MerkleLib.hashLeaf(keccak256(r0));

        bytes32 salt = keccak256("unchallenged-dataset");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);

        bytes32[] memory txBlobs = new bytes32[](1);
        txBlobs[0] = _mockKzgVersionedHash(600);
        vm.blobhashes(txBlobs);

        IDatasetRegistry.DatasetParams memory params = _mockParams(root, 1);
        vm.prank(researcher);
        registry.openDataset(salt, params, 1, true);

        vm.prank(researcher);
        registry.postClaim(datasetId, "acc", 1, 900, 1000, 955);

        // Warp past retention window
        vm.warp(block.timestamp + BlobLib.BLOB_RETENTION_SECONDS + 1);
        assertEq(
            uint256(registry.claimStatus(datasetId, 0)), uint256(IDatasetRegistry.ClaimStatus.Unchallenged)
        );
    }

    // -------------------------------------------------------------------------
    // Record Checkpointing and Verification
    // -------------------------------------------------------------------------

    function test_checkpointRecord_and_verifyRecord() public {
        bytes memory r0 = '{"row":1,"target":42}';
        bytes memory r1 = '{"row":2,"target":84}';
        bytes32 l0 = MerkleLib.hashRecord(r0);
        bytes32 l1 = MerkleLib.hashRecord(r1);
        bytes32 root = MerkleLib.hashNode(l0, l1);

        bytes32 salt = keccak256("checkpoint-dataset");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);

        bytes32[] memory txBlobs = new bytes32[](1);
        txBlobs[0] = _mockKzgVersionedHash(700);
        vm.blobhashes(txBlobs);

        IDatasetRegistry.DatasetParams memory params = _mockParams(root, 2);
        vm.prank(researcher);
        registry.openDataset(salt, params, 1, true);

        bytes32[] memory proof0 = new bytes32[](1);
        proof0[0] = l1;

        // View verification
        assertTrue(registry.verifyRecord(datasetId, 0, r0, proof0));
        assertTrue(registry.verifyRecordLeaf(datasetId, 0, l0, proof0));

        // State-changing checkpoint
        vm.expectEmit(true, true, false, true);
        emit IDatasetRegistry.RecordCheckpointed(datasetId, 0, l0, address(this));
        bytes32 returnedLeaf = registry.checkpointRecord(datasetId, 0, r0, proof0);
        assertEq(returnedLeaf, l0);
    }

    // -------------------------------------------------------------------------
    // Attestations
    // -------------------------------------------------------------------------

    function test_attestations() public {
        bytes32 salt = keccak256("attest-dataset");
        bytes32 datasetId = registry.computeDatasetId(researcher, salt);

        bytes32[] memory txBlobs = new bytes32[](1);
        txBlobs[0] = _mockKzgVersionedHash(800);
        vm.blobhashes(txBlobs);

        IDatasetRegistry.DatasetParams memory params = _mockParams(keccak256("root"), 5);
        vm.prank(researcher);
        registry.openDataset(salt, params, 1, true);

        bytes32 evidence = keccak256("retrieval-report-sha256");
        bytes32 kind = registry.ATTEST_RETRIEVED();
        vm.expectEmit(true, true, true, true);
        emit IDatasetRegistry.Attested(datasetId, attester, kind, evidence);
        vm.prank(attester);
        registry.attest(datasetId, kind, evidence);

        assertEq(registry.attestationCount(datasetId), 1);
    }
}
