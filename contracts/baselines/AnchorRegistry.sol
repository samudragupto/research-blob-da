// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AnchorRegistry
/// @author research-blob-da
/// @notice Baseline for the cost study: anchors a content digest and an off-chain locator (IPFS CID or cloud
///         URL) on-chain, while the bytes live elsewhere.
/// @dev This is how most "on-chain research data" projects operate today. It is cheap and permanent, but the
///      chain only guarantees *integrity* of the anchored digest; *availability* depends entirely on whoever
///      pins or hosts the content. The cost study pairs the measured anchoring gas with explicit, documented
///      assumptions about off-chain storage prices.
contract AnchorRegistry {
    /// @notice Thrown when an identifier is reused.
    error AnchorExists(bytes32 datasetId);

    /// @notice Stored anchor.
    /// @param digest Content digest (for IPFS, the sha2-256 multihash digest; for cloud objects, sha256).
    /// @param owner Account that created the anchor.
    /// @param anchoredAt Timestamp of anchoring.
    struct Anchor {
        bytes32 digest;
        address owner;
        uint64 anchoredAt;
    }

    /// @notice Anchors by dataset identifier.
    mapping(bytes32 datasetId => Anchor) public anchors;

    /// @notice Emitted when an anchor is created; the locator is only logged, not stored.
    event Anchored(bytes32 indexed datasetId, address indexed owner, bytes32 digest, bytes locator);

    /// @notice Creates an anchor.
    /// @param datasetId Dataset identifier.
    /// @param digest Content digest.
    /// @param locator Off-chain locator, for example `ipfs://bafy...` or `https://bucket.example/obj`.
    function anchor(bytes32 datasetId, bytes32 digest, bytes calldata locator) external {
        if (anchors[datasetId].owner != address(0)) revert AnchorExists(datasetId);
        anchors[datasetId] = Anchor({digest: digest, owner: msg.sender, anchoredAt: uint64(block.timestamp)});
        emit Anchored(datasetId, msg.sender, digest, locator);
    }
}
