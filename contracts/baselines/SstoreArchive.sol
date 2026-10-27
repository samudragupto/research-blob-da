// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title SstoreArchive
/// @author research-blob-da
/// @notice Baseline for the cost study: stores dataset bytes in contract storage, one 32-byte word per slot.
/// @dev This is the only option that keeps data permanently readable by contracts, and the most expensive one:
///      every fresh slot costs 22 100 gas (20 000 for the zero-to-non-zero write plus 2 100 for the cold access),
///      i.e. roughly 690 gas per byte before calldata. It bounds the cost of "permanent on-chain archival".
contract SstoreArchive {
    /// @notice Thrown when a chunk would overwrite already written words.
    error WordsAlreadyWritten(bytes32 datasetId, uint256 offsetWord);

    /// @notice Number of words written per dataset.
    mapping(bytes32 datasetId => uint256) public wordCount;
    /// @notice Total byte length written per dataset.
    mapping(bytes32 datasetId => uint256) public byteLength;
    mapping(bytes32 datasetId => mapping(uint256 wordIndex => bytes32)) private _words;

    /// @notice Emitted after every chunk.
    event ChunkStored(bytes32 indexed datasetId, uint256 offsetWord, uint256 words);

    /// @notice Appends a chunk to a dataset.
    /// @dev Chunks must be appended in order; the final partial word is right-padded with zeros.
    /// @param datasetId Dataset identifier.
    /// @param chunk Chunk bytes.
    function store(bytes32 datasetId, bytes calldata chunk) external {
        uint256 offsetWord = wordCount[datasetId];
        if (byteLength[datasetId] % 32 != 0) revert WordsAlreadyWritten(datasetId, offsetWord);
        uint256 words = (chunk.length + 31) / 32;
        mapping(uint256 => bytes32) storage slots = _words[datasetId];
        for (uint256 i; i < words;) {
            bytes32 w;
            assembly ("memory-safe") {
                w := calldataload(add(chunk.offset, shl(5, i)))
            }
            uint256 remaining = chunk.length - (i << 5);
            if (remaining < 32) {
                // Mask out bytes beyond the end of the chunk that calldataload may have read.
                w &= bytes32(type(uint256).max << ((32 - remaining) << 3));
            }
            slots[offsetWord + i] = w;
            unchecked {
                ++i;
            }
        }
        wordCount[datasetId] = offsetWord + words;
        byteLength[datasetId] += chunk.length;
        emit ChunkStored(datasetId, offsetWord, words);
    }

    /// @notice Reads one stored word.
    /// @param datasetId Dataset identifier.
    /// @param wordIndex Word position.
    /// @return The stored word.
    function wordAt(bytes32 datasetId, uint256 wordIndex) external view returns (bytes32) {
        return _words[datasetId][wordIndex];
    }
}
