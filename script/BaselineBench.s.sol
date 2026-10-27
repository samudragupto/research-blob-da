// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DatasetRegistry} from "../contracts/DatasetRegistry.sol";
import {AnchorRegistry} from "../contracts/baselines/AnchorRegistry.sol";
import {CalldataSink} from "../contracts/baselines/CalldataSink.sol";
import {SstoreArchive} from "../contracts/baselines/SstoreArchive.sol";
import {IDatasetRegistry} from "../contracts/interfaces/IDatasetRegistry.sol";
import {BlobLib} from "../contracts/libraries/BlobLib.sol";
import {MerkleLib} from "../contracts/libraries/MerkleLib.sol";
import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";

/// @title BaselineBenchScript
/// @notice Measures empirical execution gas for blob registration vs. calldata vs. SSTORE vs. IPFS anchoring.
contract BaselineBenchScript is Script {
    function run() external {
        console2.log("=== EMPIRICAL GAS BENCHMARK (CANCUN EVM) ===");

        CalldataSink calldataSink = new CalldataSink();
        SstoreArchive sstoreArchive = new SstoreArchive();
        AnchorRegistry anchorRegistry = new AnchorRegistry();
        DatasetRegistry datasetRegistry = new DatasetRegistry(1 days);

        // 1. CalldataSink gas per byte
        uint256[] memory sizes = new uint256[](5);
        sizes[0] = 1024; // 1 KiB
        sizes[1] = 4096; // 4 KiB
        sizes[2] = 16_384; // 16 KiB
        sizes[3] = 65_536; // 64 KiB
        sizes[4] = 126_976; // 1 blob payload size

        for (uint256 i = 0; i < sizes.length; i++) {
            uint256 sz = sizes[i];
            bytes memory payload = new bytes(sz);
            for (uint256 j = 0; j < sz; j++) {
                payload[j] = bytes1(uint8((j * 31 + 7) % 256)); // non-zero bytes (16 gas/byte)
            }
            bytes32 did = keccak256(abi.encodePacked("calldata-bench", i));
            uint256 g0 = gasleft();
            calldataSink.post(did, 0, payload);
            uint256 used = g0 - gasleft();
            console2.log("CalldataSink %s bytes used gas: %s (avg gas/byte: %s)", sz, used, used / sz);
        }

        // 2. SstoreArchive gas per word
        uint256[] memory sstoreSizes = new uint256[](4);
        sstoreSizes[0] = 32; // 1 slot
        sstoreSizes[1] = 64; // 2 slots
        sstoreSizes[2] = 256; // 8 slots
        sstoreSizes[3] = 1024; // 32 slots

        for (uint256 i = 0; i < sstoreSizes.length; i++) {
            uint256 sz = sstoreSizes[i];
            bytes memory payload = new bytes(sz);
            for (uint256 j = 0; j < sz; j++) {
                payload[j] = bytes1(uint8((j * 17 + 1) % 256));
            }
            bytes32 did = keccak256(abi.encodePacked("sstore-bench", i));
            uint256 g0 = gasleft();
            sstoreArchive.store(did, payload);
            uint256 used = g0 - gasleft();
            console2.log("SstoreArchive %s bytes used gas: %s (avg gas/byte: %s)", sz, used, used / sz);
        }

        // 3. AnchorRegistry (IPFS / Cloud locator)
        bytes32 digest = keccak256("dataset-sha256-content");
        bytes memory ipfsCid = "ipfs://bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi";
        uint256 g0Anchor = gasleft();
        anchorRegistry.anchor(keccak256("anchor-ipfs"), digest, ipfsCid);
        uint256 anchorGas = g0Anchor - gasleft();
        console2.log("AnchorRegistry (IPFS CID) gas: %s", anchorGas);

        // 4. DatasetRegistry: openDataset + 1 blob (reads BLOBHASH)
        bytes32[] memory bHashes = new bytes32[](1);
        bHashes[0] = bytes32(hex"0100000000000000000000000000000000000000000000000000000000001234");
        vm.blobhashes(bHashes);

        bytes32 root = keccak256("records-root");
        IDatasetRegistry.DatasetParams memory params = IDatasetRegistry.DatasetParams({
            recordsRoot: root,
            contentHash: keccak256("canonical-stream"),
            metadataHash: keccak256("manifest"),
            rawSize: 126_976,
            encodedSize: 65_000,
            recordCount: 1000,
            codec: 1,
            layout: 0,
            packing: 0
        });

        bytes32 salt = keccak256("bench-blob-dataset");
        uint256 g0Blob = gasleft();
        bytes32 datasetId = datasetRegistry.openDataset(salt, params, 1, true);
        uint256 blobRegGas = g0Blob - gasleft();
        console2.log("DatasetRegistry openDataset + 1 blob execution gas: %s", blobRegGas);

        // 5. Checkpoint Record (Merkle leaf inclusion)
        bytes memory rec = '{"step":10,"loss":0.42}';
        bytes32 leaf = MerkleLib.hashRecord(rec);
        // Build 2-leaf tree for checkpoint test
        bytes32 otherLeaf = MerkleLib.hashRecord('{"step":20,"loss":0.38}');
        bytes32 benchRoot = MerkleLib.hashNode(leaf, otherLeaf);
        IDatasetRegistry.DatasetParams memory params2 = IDatasetRegistry.DatasetParams({
            recordsRoot: benchRoot,
            contentHash: keccak256("stream-2"),
            metadataHash: keccak256("manifest-2"),
            rawSize: 100,
            encodedSize: 80,
            recordCount: 2,
            codec: 1,
            layout: 0,
            packing: 0
        });
        vm.blobhashes(bHashes);
        bytes32 did2 = datasetRegistry.openDataset(keccak256("bench-chk"), params2, 1, true);

        bytes32[] memory proof = new bytes32[](1);
        proof[0] = otherLeaf;

        uint256 g0Chk = gasleft();
        datasetRegistry.checkpointRecord(did2, 0, rec, proof);
        uint256 chkGas = g0Chk - gasleft();
        console2.log("DatasetRegistry checkpointRecord gas: %s", chkGas);
    }
}
