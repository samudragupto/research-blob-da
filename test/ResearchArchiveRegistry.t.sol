// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DatasetRegistry} from "../contracts/DatasetRegistry.sol";
import {ResearchArchiveRegistry} from "../contracts/ResearchArchiveRegistry.sol";
import {IDatasetRegistry} from "../contracts/interfaces/IDatasetRegistry.sol";
import {Test} from "forge-std/Test.sol";

contract ResearchArchiveRegistryTest is Test {
    DatasetRegistry public registry;
    ResearchArchiveRegistry public archiveRegistry;

    address public author = address(0xA11CE);
    address public archiver = address(0xB0B);

    bytes32 public constant TEST_SALT = bytes32(uint256(1));
    bytes32 public datasetId;

    function setUp() public {
        registry = new DatasetRegistry(86_400); // 1 day challenge period
        archiveRegistry = new ResearchArchiveRegistry(address(registry));

        // Open and finalize a dataset on DatasetRegistry
        bytes32[] memory txBlobs = new bytes32[](1);
        txBlobs[0] = bytes32(uint256(0x01) << 248 | (uint256(keccak256("blob1")) >> 8));
        vm.blobhashes(txBlobs);

        IDatasetRegistry.DatasetParams memory params = IDatasetRegistry.DatasetParams({
            recordsRoot: bytes32(uint256(0x5678)),
            contentHash: bytes32(uint256(0x1234)),
            metadataHash: bytes32(uint256(0x9abc)),
            rawSize: 100_000,
            encodedSize: 50_000,
            recordCount: 100,
            codec: 1,
            layout: 0,
            packing: 0
        });

        vm.prank(author);
        datasetId = registry.openDataset(TEST_SALT, params, 1, true);
    }

    function test_registerArchivalRecord_success() public {
        vm.startPrank(archiver);
        bytes32 cidHash = keccak256("ipfs://bafybeic5m36q...");
        bytes32 payloadSha256 = sha256("CANONICAL_PAYLOAD_BYTES");

        archiveRegistry.registerArchivalRecord(
            datasetId, ResearchArchiveRegistry.StorageProvider.IPFS, cidHash, payloadSha256
        );
        vm.stopPrank();

        assertEq(archiveRegistry.archiveCount(datasetId), 1);
        assertTrue(archiveRegistry.verifyArchivalBinding(datasetId, cidHash));

        ResearchArchiveRegistry.ArchivalRecord memory rec =
            archiveRegistry.getPrimaryArchivalRecord(datasetId);
        assertEq(uint8(rec.provider), uint8(ResearchArchiveRegistry.StorageProvider.IPFS));
        assertEq(rec.archiver, archiver);
        assertEq(rec.archivalCidHash, cidHash);
        assertEq(rec.payloadSha256, payloadSha256);
    }

    function test_registerArchivalRecord_reverts_if_not_finalized() public {
        // Open an unfinalized dataset
        vm.startPrank(author);
        IDatasetRegistry.DatasetParams memory params = IDatasetRegistry.DatasetParams({
            recordsRoot: bytes32(uint256(0x8888)),
            contentHash: bytes32(uint256(0x9999)),
            metadataHash: bytes32(uint256(0x7777)),
            rawSize: 50_000,
            encodedSize: 25_000,
            recordCount: 50,
            codec: 1,
            layout: 0,
            packing: 0
        });
        bytes32 unfinalizedId = registry.openDataset(bytes32(uint256(2)), params, 0, false);
        vm.stopPrank();

        vm.startPrank(archiver);
        bytes32 cidHash = keccak256("ipfs://bafybeic...");
        bytes32 payloadSha256 = sha256("DATA");

        vm.expectRevert(
            abi.encodeWithSelector(ResearchArchiveRegistry.DatasetNotFinalized.selector, unfinalizedId)
        );
        archiveRegistry.registerArchivalRecord(
            unfinalizedId, ResearchArchiveRegistry.StorageProvider.IPFS, cidHash, payloadSha256
        );
        vm.stopPrank();
    }

    function test_registerArchivalRecord_reverts_duplicate_cid() public {
        vm.startPrank(archiver);
        bytes32 cidHash = keccak256("ipfs://duplicate_cid");
        bytes32 payloadSha256 = sha256("DATA");

        archiveRegistry.registerArchivalRecord(
            datasetId, ResearchArchiveRegistry.StorageProvider.IPFS, cidHash, payloadSha256
        );

        vm.expectRevert(
            abi.encodeWithSelector(ResearchArchiveRegistry.RecordAlreadyExists.selector, datasetId, cidHash)
        );
        archiveRegistry.registerArchivalRecord(
            datasetId, ResearchArchiveRegistry.StorageProvider.IPFS, cidHash, payloadSha256
        );
        vm.stopPrank();
    }

    function test_registerArchivalRecord_reverts_invalid_cid() public {
        bytes32 payload = sha256("DATA");
        vm.prank(archiver);
        vm.expectRevert(ResearchArchiveRegistry.InvalidCidHash.selector);
        archiveRegistry.registerArchivalRecord(
            datasetId, ResearchArchiveRegistry.StorageProvider.IPFS, bytes32(0), payload
        );
    }

    function test_multiple_storage_replicas() public {
        vm.startPrank(archiver);
        bytes32 ipfsCid = keccak256("ipfs://bafy1");
        bytes32 arweaveCid = keccak256("arweave://tx_id_1");

        archiveRegistry.registerArchivalRecord(
            datasetId, ResearchArchiveRegistry.StorageProvider.IPFS, ipfsCid, sha256("PAYLOAD")
        );
        archiveRegistry.registerArchivalRecord(
            datasetId, ResearchArchiveRegistry.StorageProvider.Arweave, arweaveCid, sha256("PAYLOAD")
        );
        vm.stopPrank();

        assertEq(archiveRegistry.archiveCount(datasetId), 2);
        assertTrue(archiveRegistry.verifyArchivalBinding(datasetId, ipfsCid));
        assertTrue(archiveRegistry.verifyArchivalBinding(datasetId, arweaveCid));
    }
}
