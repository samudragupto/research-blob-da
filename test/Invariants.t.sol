// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DatasetRegistry} from "../contracts/DatasetRegistry.sol";
import {IDatasetRegistry} from "../contracts/interfaces/IDatasetRegistry.sol";
import {BlobLib} from "../contracts/libraries/BlobLib.sol";
import {Test} from "forge-std/Test.sol";

contract RegistryHandler is Test {
    DatasetRegistry public immutable registry;

    bytes32[] public activeDatasetIds;
    mapping(bytes32 => bool) public isFinalized;
    mapping(bytes32 => uint32) public recordedBlobCounts;

    constructor(DatasetRegistry _registry) {
        registry = _registry;
    }

    function openRandomDataset(uint256 saltSeed, uint32 recordCount) external {
        if (recordCount == 0) recordCount = 1;
        bytes32 salt = bytes32(saltSeed);
        bytes32 datasetId = registry.computeDatasetId(address(this), salt);

        IDatasetRegistry.DatasetParams memory params = IDatasetRegistry.DatasetParams({
            recordsRoot: keccak256(abi.encodePacked("root", saltSeed)),
            contentHash: keccak256(abi.encodePacked("content", saltSeed)),
            metadataHash: keccak256("manifest"),
            rawSize: 10_000,
            encodedSize: 5000,
            recordCount: recordCount,
            codec: 0,
            layout: 0,
            packing: 0
        });

        try registry.openDataset(salt, params, 0, false) {
            activeDatasetIds.push(datasetId);
            recordedBlobCounts[datasetId] = 0;
        } catch {
            // Revert expected if duplicate
        }
    }

    function appendExternal(uint256 datasetIdx, uint8 count) external {
        if (activeDatasetIds.length == 0) return;
        bytes32 datasetId = activeDatasetIds[datasetIdx % activeDatasetIds.length];
        if (isFinalized[datasetId]) return;

        uint256 n = (uint256(count) % 4) + 1; // 1 to 4 blobs
        bytes32[] memory hashes = new bytes32[](n);
        for (uint256 i = 0; i < n; i++) {
            bytes32 h = keccak256(abi.encodePacked("kzg", datasetId, i));
            hashes[i] = (h & 0x00ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff)
                | bytes32(uint256(0x01) << 248);
        }

        try registry.appendExternalBlobs(datasetId, hashes, false) {
            recordedBlobCounts[datasetId] += uint32(n);
        } catch {}
    }

    function finalizeDataset(uint256 datasetIdx) external {
        if (activeDatasetIds.length == 0) return;
        bytes32 datasetId = activeDatasetIds[datasetIdx % activeDatasetIds.length];
        if (isFinalized[datasetId]) return;
        if (recordedBlobCounts[datasetId] == 0) return;

        try registry.finalize(datasetId) {
            isFinalized[datasetId] = true;
        } catch {}
    }

    function getActiveDatasetCount() external view returns (uint256) {
        return activeDatasetIds.length;
    }
}

contract InvariantTest is Test {
    DatasetRegistry private registry;
    RegistryHandler private handler;

    function setUp() public {
        registry = new DatasetRegistry(1 days);
        handler = new RegistryHandler(registry);
        targetContract(address(handler));
    }

    function invariant_dataset_integrity() public view {
        uint256 total = handler.getActiveDatasetCount();
        for (uint256 i = 0; i < total; i++) {
            bytes32 datasetId = handler.activeDatasetIds(i);
            IDatasetRegistry.Dataset memory d = registry.getDataset(datasetId);

            // Invariant 1: Total blobs >= external blobs
            assertGe(d.blobCount, uint32(d.externalBlobCount));

            // Invariant 2: If handler finalized it, on-chain status MUST be Finalized
            if (handler.isFinalized(datasetId)) {
                assertEq(uint256(d.status), uint256(IDatasetRegistry.Status.Finalized));
                assertGt(d.blobCount, 0);
            }

            // Invariant 3: Record count is strictly positive
            assertGt(d.recordCount, 0);

            // Invariant 4: If firstBlobAt > 0, retention deadline > firstBlobAt
            if (d.firstBlobAt > 0) {
                assertEq(
                    registry.availabilityDeadline(datasetId),
                    uint256(d.firstBlobAt) + BlobLib.BLOB_RETENTION_SECONDS
                );
            }
        }
    }
}
