// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {Counter} from "../src/Counter.sol";

/// @notice Class 7 (Web3 on L2): deploy the same bytecode to Sepolia and to
/// Base Sepolia and compare gas/latency on both explorers. Class 4: this is
/// the script contracts.yml runs on a tagged release, using a deploy key
/// that lives ONLY as a GitHub Actions secret -- never in this file.
contract DeployScript is Script {
    function run() external returns (Counter) {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        Counter counter = new Counter();
        console.log("Counter deployed at:", address(counter));

        vm.stopBroadcast();
        return counter;
    }
}
