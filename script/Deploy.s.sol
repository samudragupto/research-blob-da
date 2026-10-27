// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DatasetRegistry} from "../contracts/DatasetRegistry.sol";
import {AnchorRegistry} from "../contracts/baselines/AnchorRegistry.sol";
import {CalldataSink} from "../contracts/baselines/CalldataSink.sol";
import {SstoreArchive} from "../contracts/baselines/SstoreArchive.sol";
import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";

/// @title DeployScript
/// @notice Deploys DatasetRegistry and the three baseline contracts on any EVM Cancun+ network.
contract DeployScript is Script {
    function run()
        external
        returns (
            DatasetRegistry registry,
            CalldataSink calldataSink,
            SstoreArchive sstoreArchive,
            AnchorRegistry anchorRegistry
        )
    {
        uint256 deployerPrivateKey = vm.envOr(
            "PRIVATE_KEY",
            uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80) // Anvil default key 0
        );

        // 1 day minimum challenge period by default
        uint64 minChallengePeriod = uint64(vm.envOr("MIN_CHALLENGE_PERIOD", uint256(1 days)));

        vm.startBroadcast(deployerPrivateKey);

        registry = new DatasetRegistry(minChallengePeriod);
        console2.log("DatasetRegistry deployed at:", address(registry));

        calldataSink = new CalldataSink();
        console2.log("CalldataSink deployed at:", address(calldataSink));

        sstoreArchive = new SstoreArchive();
        console2.log("SstoreArchive deployed at:", address(sstoreArchive));

        anchorRegistry = new AnchorRegistry();
        console2.log("AnchorRegistry deployed at:", address(anchorRegistry));

        vm.stopBroadcast();
    }
}
