// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title CalldataSink
/// @author research-blob-da
/// @notice Baseline for the cost study: publishes dataset bytes as transaction calldata.
/// @dev Calldata is part of the execution payload and is retained by every full node that keeps history
///      (subject to EIP-4444 history expiry), so it is the natural "pre-4844" way to make data available.
///      The contract hashes each chunk and emits the digest so that an indexer can reassemble and check the
///      dataset; it deliberately stores nothing. Since Pectra (EIP-7623) calldata-dominated transactions pay a
///      floor of 10/40 gas per zero/non-zero byte, which this baseline exercises.
contract CalldataSink {
    /// @notice Emitted for every chunk.
    /// @param datasetId Caller-chosen dataset identifier.
    /// @param publisher Sender of the chunk.
    /// @param chunkIndex Position of the chunk.
    /// @param chunkHash keccak256 of the chunk bytes.
    /// @param length Chunk length in bytes.
    event ChunkPosted(
        bytes32 indexed datasetId,
        address indexed publisher,
        uint256 chunkIndex,
        bytes32 chunkHash,
        uint256 length
    );

    /// @notice Publishes one chunk of a dataset as calldata.
    /// @param datasetId Dataset identifier.
    /// @param chunkIndex Position of the chunk.
    /// @param chunk Chunk bytes.
    function post(bytes32 datasetId, uint256 chunkIndex, bytes calldata chunk) external {
        emit ChunkPosted(datasetId, msg.sender, chunkIndex, keccak256(chunk), chunk.length);
    }
}
