// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DatasetRegistry} from "../contracts/DatasetRegistry.sol";
import {IDatasetRegistry} from "../contracts/interfaces/IDatasetRegistry.sol";
import {BlobLib} from "../contracts/libraries/BlobLib.sol";
import {MerkleLib} from "../contracts/libraries/MerkleLib.sol";
import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";

/// @title PostBlobDatasetScript
/// @notice Demonstrates packing research records, attaching blobs via Foundry cheatcodes / type-3 transactions,
///         registering the dataset on-chain, and posting an optimistic property claim.
contract PostBlobDatasetScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envOr(
            "PRIVATE_KEY", uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80)
        );
        address registryAddress = vm.envOr("REGISTRY_ADDRESS", address(0));

        vm.startBroadcast(deployerPrivateKey);

        DatasetRegistry registry;
        if (registryAddress == address(0)) {
            registry = new DatasetRegistry(1 days);
            console2.log("Deployed ephemeral DatasetRegistry at:", address(registry));
        } else {
            registry = DatasetRegistry(registryAddress);
            console2.log("Using existing DatasetRegistry at:", address(registry));
        }

        // Create sample dataset records
        uint32 recordCount = 4;
        bytes[] memory records = new bytes[](4);
        records[0] = '{"epoch":1,"loss":1.82,"acc":85.2}';
        records[1] = '{"epoch":2,"loss":1.41,"acc":88.7}';
        records[2] = '{"epoch":3,"loss":0.98,"acc":91.5}';
        records[3] = '{"epoch":4,"loss":0.65,"acc":94.1}';

        bytes32[] memory leaves = new bytes32[](4);
        for (uint256 i = 0; i < recordCount; i++) {
            leaves[i] = MerkleLib.hashRecord(records[i]);
        }
        bytes32 n01 = MerkleLib.hashNode(leaves[0], leaves[1]);
        bytes32 n23 = MerkleLib.hashNode(leaves[2], leaves[3]);
        bytes32 recordsRoot = MerkleLib.hashNode(n01, n23);

        bytes32 contentHash = keccak256("canonical-serialized-stream-of-4-records");
        bytes32 metadataHash =
            keccak256('{"dataset":"ml-training-trace","model":"resnet18","optimizer":"adamw"}');

        IDatasetRegistry.DatasetParams memory params = IDatasetRegistry.DatasetParams({
            recordsRoot: recordsRoot,
            contentHash: contentHash,
            metadataHash: metadataHash,
            rawSize: 138,
            encodedSize: 120,
            recordCount: recordCount,
            codec: 1, // zstd
            layout: 0, // stream
            packing: 0 // 31 bytes per FE
        });

        // 128 KiB mock blob payload
        bytes memory blobBytes = new bytes(BlobLib.BYTES_PER_BLOB);
        // Header in field element 0: magic 0x52424441 ("RBDA"), version 1
        blobBytes[0] = 0x52;
        blobBytes[1] = 0x42;
        blobBytes[2] = 0x44;
        blobBytes[3] = 0x41;
        blobBytes[4] = 0x01; // version

        // Attach blob to the next call (type-3 tx simulation in Foundry)
        vm.attachBlob(blobBytes);

        bytes32 salt = keccak256("demo-experiment-trace-v1");
        bytes32 datasetId = registry.openDataset(salt, params, 1, true);

        console2.log("Registered Dataset ID:");
        console2.logBytes32(datasetId);

        bytes32 vh = registry.blobHashAt(datasetId, 0);
        console2.log("Blob Versioned Hash recorded from BLOBHASH opcode:");
        console2.logBytes32(vh);

        // Post an optimistic property claim: loss is within [0.00, 2.50] (decimals=2 -> min=0, max=250)
        uint256 claimIdx = registry.postClaim(datasetId, "loss", 2, 0, 250, 486);
        console2.log("Posted Property Claim index:", claimIdx);

        IDatasetRegistry.PropertyClaim memory claim = registry.getClaim(datasetId, claimIdx);
        console2.log("Claim key:", string(claim.key));
        console2.log("Claim deadline (unix):", claim.deadline);

        vm.stopBroadcast();
    }
}
