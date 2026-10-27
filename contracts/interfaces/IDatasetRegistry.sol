// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IDatasetRegistry
/// @author research-blob-da
/// @notice Interface of a registry that anchors research datasets carried in EIP-4844 blobs.
/// @dev A dataset is described by three independent commitments, each answering a different question:
///      - blob versioned hashes: *which* bytes were made available by the network (KZG, layout-specific);
///      - `recordsRoot`: *which logical records* the dataset contains, in order (Merkle, layout-independent);
///      - `contentHash`: the hash of the canonical, uncompressed record stream (whole-dataset integrity).
///      Property claims add optimistic statements about the records that anyone can refute on-chain during
///      the window in which the blob data is guaranteed to be retrievable.
interface IDatasetRegistry {
    // ---------------------------------------------------------------------------------------------------------
    // Types
    // ---------------------------------------------------------------------------------------------------------

    /// @notice Lifecycle of a dataset.
    /// @dev `Open` datasets may still receive blobs. `Finalized` datasets are immutable.
    enum Status {
        None,
        Open,
        Finalized
    }

    /// @notice Outcome of a property claim.
    enum ClaimStatus {
        Pending,
        Unchallenged,
        Refuted
    }

    /// @notice Caller-supplied commitments and metadata for a new dataset.
    /// @param recordsRoot Merkle root over record leaves (see `MerkleLib`).
    /// @param contentHash keccak256 of the canonical length-prefixed record stream.
    /// @param metadataHash keccak256 of the canonical JSON manifest kept off-chain (schema, encoder config).
    /// @param rawSize Size of the canonical record stream in bytes.
    /// @param encodedSize Total compressed payload size in bytes across all blobs.
    /// @param recordCount Number of records (Merkle leaves). Must be non-zero.
    /// @param codec 0 = none, 1 = zstd.
    /// @param layout 0 = stream (one compressed stream split across blobs), 1 = aligned (self-contained frames).
    /// @param packing 0 = 31 bytes per field element, 1 = 254 bits per field element.
    struct DatasetParams {
        bytes32 recordsRoot;
        bytes32 contentHash;
        bytes32 metadataHash;
        uint64 rawSize;
        uint64 encodedSize;
        uint32 recordCount;
        uint8 codec;
        uint8 layout;
        uint8 packing;
    }

    /// @notice Stored dataset record, packed into five storage slots.
    /// @param researcher Account that opened the dataset and may append blobs and post claims.
    /// @param createdAt Timestamp of `openDataset`.
    /// @param blobCount Total number of blobs registered.
    /// @param externalBlobCount Number of blobs registered by hash rather than read via `BLOBHASH`.
    /// @param firstBlobAt Timestamp of the first transaction that registered blobs.
    struct Dataset {
        address researcher;
        uint40 createdAt;
        uint32 blobCount;
        uint24 externalBlobCount;
        bytes32 recordsRoot;
        bytes32 contentHash;
        bytes32 metadataHash;
        uint64 rawSize;
        uint64 encodedSize;
        uint32 recordCount;
        uint8 codec;
        uint8 layout;
        uint8 packing;
        Status status;
        uint40 firstBlobAt;
    }

    /// @notice Optimistic claim that every record carries a numeric top-level field within `[min, max]`.
    /// @param key Top-level JSON key of the property column.
    /// @param min Claimed lower bound (fixed point, `decimals` fractional digits).
    /// @param max Claimed upper bound (fixed point).
    /// @param sum Claimed column sum (fixed point). Attested only; verifiable off-chain after retrieval.
    /// @param deadline Last timestamp at which a refutation is accepted.
    /// @param decimals Fixed-point scale.
    /// @param refuted Whether a valid refutation was submitted.
    /// @param challenger Account that submitted the refutation.
    struct PropertyClaim {
        bytes key;
        int128 min;
        int128 max;
        int256 sum;
        uint64 deadline;
        uint8 decimals;
        bool refuted;
        address challenger;
    }

    // ---------------------------------------------------------------------------------------------------------
    // Events
    // ---------------------------------------------------------------------------------------------------------

    /// @notice Emitted when a dataset is opened.
    event DatasetOpened(
        bytes32 indexed datasetId,
        address indexed researcher,
        bytes32 recordsRoot,
        bytes32 contentHash,
        bytes32 metadataHash,
        uint32 recordCount
    );

    /// @notice Emitted when blobs are attached to a dataset.
    /// @param bound True if hashes were read from the transaction via `BLOBHASH`; false if supplied by caller.
    event BlobsAppended(bytes32 indexed datasetId, uint256 firstIndex, bytes32[] versionedHashes, bool bound);

    /// @notice Emitted when a dataset becomes immutable.
    event DatasetFinalized(bytes32 indexed datasetId, uint256 blobCount, uint256 recordCount);

    /// @notice Emitted when a property claim is posted.
    event PropertyClaimed(
        bytes32 indexed datasetId,
        uint256 indexed claimIndex,
        bytes key,
        uint8 decimals,
        int128 min,
        int128 max,
        int256 sum,
        uint64 deadline
    );

    /// @notice Emitted when a property claim is refuted by a committed record.
    event ClaimRefuted(
        bytes32 indexed datasetId, uint256 indexed claimIndex, address indexed challenger, uint256 recordIndex
    );

    /// @notice Emitted when field element 0 of a blob is shown, via the point-evaluation precompile, to carry
    ///         the expected dataset header.
    event BlobHeaderVerified(bytes32 indexed datasetId, uint256 indexed blobIndex, bytes32 versionedHash);

    /// @notice Emitted when a record is verified on-chain and checkpointed (for example, cited by a paper).
    event RecordCheckpointed(
        bytes32 indexed datasetId, uint256 indexed recordIndex, bytes32 leaf, address indexed caller
    );

    /// @notice Free-form attestation about a dataset (retrieval, archival copy, replication).
    event Attested(
        bytes32 indexed datasetId, address indexed attester, bytes32 indexed kind, bytes32 evidenceHash
    );

    // ---------------------------------------------------------------------------------------------------------
    // Errors
    // ---------------------------------------------------------------------------------------------------------

    error DatasetAlreadyExists(bytes32 datasetId);
    error DatasetNotFound(bytes32 datasetId);
    error NotResearcher(address caller);
    error InvalidStatus(Status expected, Status actual);
    error InvalidParams();
    error NoBlobs();
    error TooManyBlobs();
    error InvalidVersionedHash(bytes32 versionedHash);
    error ExternalBlobsPreventClaims();
    error ClaimWindowClosed(uint256 deadline, uint256 minChallengePeriod);
    error InvalidClaim();
    error ClaimNotFound(uint256 claimIndex);
    error ChallengeWindowClosed(uint256 deadline);
    error ClaimAlreadyRefuted(uint256 claimIndex);
    error InvalidRecordProof();
    error NotAViolation();
    error BlobNotFound(uint256 blobIndex);
    error HeaderAlreadyVerified(uint256 blobIndex);
    error PointEvaluationFailed();
    error HeaderMismatch(uint8 field);

    // ---------------------------------------------------------------------------------------------------------
    // State-changing functions
    // ---------------------------------------------------------------------------------------------------------

    function openDataset(bytes32 salt, DatasetParams calldata params, uint256 numTxBlobs, bool finalize)
        external
        returns (bytes32 datasetId);

    function appendBlobs(bytes32 datasetId, uint256 numTxBlobs, bool finalize) external;

    function appendExternalBlobs(bytes32 datasetId, bytes32[] calldata versionedHashes, bool finalize)
        external;

    function finalize(bytes32 datasetId) external;

    function postClaim(
        bytes32 datasetId,
        bytes calldata key,
        uint8 decimals,
        int128 min,
        int128 max,
        int256 sum
    ) external returns (uint256 claimIndex);

    function refuteClaim(
        bytes32 datasetId,
        uint256 claimIndex,
        uint256 recordIndex,
        bytes calldata record,
        bytes32[] calldata proof
    ) external;

    function verifyBlobHeader(
        bytes32 datasetId,
        uint256 blobIndex,
        uint256 y,
        bytes calldata commitment,
        bytes calldata proof
    ) external;

    function checkpointRecord(
        bytes32 datasetId,
        uint256 recordIndex,
        bytes calldata record,
        bytes32[] calldata proof
    ) external returns (bytes32 leaf);

    function attest(bytes32 datasetId, bytes32 kind, bytes32 evidenceHash) external;

    // ---------------------------------------------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------------------------------------------

    function computeDatasetId(address researcher, bytes32 salt) external pure returns (bytes32);

    function getDataset(bytes32 datasetId) external view returns (Dataset memory);

    function blobHashes(bytes32 datasetId) external view returns (bytes32[] memory);

    function blobHashAt(bytes32 datasetId, uint256 blobIndex) external view returns (bytes32);

    function verifyRecord(
        bytes32 datasetId,
        uint256 recordIndex,
        bytes calldata record,
        bytes32[] calldata proof
    ) external view returns (bool);

    function verifyRecordLeaf(bytes32 datasetId, uint256 recordIndex, bytes32 leaf, bytes32[] calldata proof)
        external
        view
        returns (bool);

    function verifyRecordRange(
        bytes32 datasetId,
        uint256 start,
        bytes[] calldata records,
        bytes32[] calldata proof
    ) external view returns (bool);

    function availabilityDeadline(bytes32 datasetId) external view returns (uint256);

    function isWithinRetentionWindow(bytes32 datasetId) external view returns (bool);

    function claimCount(bytes32 datasetId) external view returns (uint256);

    function getClaim(bytes32 datasetId, uint256 claimIndex) external view returns (PropertyClaim memory);

    function claimStatus(bytes32 datasetId, uint256 claimIndex) external view returns (ClaimStatus);

    function isHeaderVerified(bytes32 datasetId, uint256 blobIndex) external view returns (bool);

    function attestationCount(bytes32 datasetId) external view returns (uint256);
}
