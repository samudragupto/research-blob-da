// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IDatasetRegistry} from "./interfaces/IDatasetRegistry.sol";

/// @title ResearchArchiveRegistry
/// @author research-blob-da
/// @notice Dual-horizon archival extension for research datasets published via EIP-4844 blobs.
/// @dev Links transient Ethereum blob commitments in DatasetRegistry to durable, content-addressed
///      storage networks (IPFS, Filecoin, Arweave, local CAS). Stores compact 32-byte content identifiers
///      to minimize EVM state bloat while preserving cryptographic verification.
contract ResearchArchiveRegistry {
    enum StorageProvider {
        None,
        IPFS,
        Filecoin,
        Arweave,
        LocalCAS
    }

    struct ArchivalRecord {
        StorageProvider provider;
        uint64 archivedAt;
        address archiver;
        bytes32 archivalCidHash;
        bytes32 payloadSha256;
    }

    error DatasetNotFinalized(bytes32 datasetId);
    error UnauthorizedArchiver(bytes32 datasetId, address caller);
    error InvalidCidHash();
    error RecordAlreadyExists(bytes32 datasetId, bytes32 archivalCidHash);
    error RecordNotFound(bytes32 datasetId);

    event DatasetArchived(
        bytes32 indexed datasetId,
        StorageProvider indexed provider,
        bytes32 indexed archivalCidHash,
        bytes32 payloadSha256,
        address archiver,
        uint64 archivedAt
    );

    IDatasetRegistry public immutable datasetRegistry;

    // datasetId => archivalCidHash => ArchivalRecord
    mapping(bytes32 datasetId => mapping(bytes32 cidHash => ArchivalRecord)) private _records;
    // datasetId => primary/latest cidHash
    mapping(bytes32 datasetId => bytes32) private _primaryCidHash;
    // datasetId => count of registered archival replicas
    mapping(bytes32 datasetId => uint256) private _archiveCount;

    constructor(address datasetRegistryAddress) {
        datasetRegistry = IDatasetRegistry(datasetRegistryAddress);
    }

    /// @notice Registers an external content-addressed archival persistence record for a finalized dataset.
    /// @param datasetId Identifier of the dataset in DatasetRegistry.
    /// @param provider Storage provider type (IPFS, Filecoin, Arweave, LocalCAS).
    /// @param archivalCidHash Keccak256 hash of the content identifier string or multihash.
    /// @param payloadSha256 SHA-256 hash of the uncompressed or canonical archival byte payload.
    function registerArchivalRecord(
        bytes32 datasetId,
        StorageProvider provider,
        bytes32 archivalCidHash,
        bytes32 payloadSha256
    ) external {
        if (archivalCidHash == bytes32(0)) revert InvalidCidHash();
        if (_records[datasetId][archivalCidHash].archiver != address(0)) {
            revert RecordAlreadyExists(datasetId, archivalCidHash);
        }

        // Verify dataset exists and is finalized in DatasetRegistry
        IDatasetRegistry.Dataset memory ds = datasetRegistry.getDataset(datasetId);
        if (ds.status != IDatasetRegistry.Status.Finalized) {
            revert DatasetNotFinalized(datasetId);
        }

        _records[datasetId][archivalCidHash] = ArchivalRecord({
            provider: provider,
            archivedAt: uint64(block.timestamp),
            archiver: msg.sender,
            archivalCidHash: archivalCidHash,
            payloadSha256: payloadSha256
        });

        _primaryCidHash[datasetId] = archivalCidHash;
        _archiveCount[datasetId] += 1;

        emit DatasetArchived(
            datasetId, provider, archivalCidHash, payloadSha256, msg.sender, uint64(block.timestamp)
        );
    }

    /// @notice Returns the primary archival record for a dataset.
    function getPrimaryArchivalRecord(bytes32 datasetId) external view returns (ArchivalRecord memory) {
        bytes32 cidHash = _primaryCidHash[datasetId];
        if (cidHash == bytes32(0)) revert RecordNotFound(datasetId);
        return _records[datasetId][cidHash];
    }

    /// @notice Returns a specific archival record by datasetId and archivalCidHash.
    function getArchivalRecord(bytes32 datasetId, bytes32 archivalCidHash)
        external
        view
        returns (ArchivalRecord memory)
    {
        ArchivalRecord memory rec = _records[datasetId][archivalCidHash];
        if (rec.archiver == address(0)) revert RecordNotFound(datasetId);
        return rec;
    }

    /// @notice Returns the number of registered archival persistence locations for a dataset.
    function archiveCount(bytes32 datasetId) external view returns (uint256) {
        return _archiveCount[datasetId];
    }

    /// @notice Cryptographically verifies whether a given CID hash is bound to a finalized dataset.
    function verifyArchivalBinding(bytes32 datasetId, bytes32 archivalCidHash) external view returns (bool) {
        return _records[datasetId][archivalCidHash].archiver != address(0);
    }
}
