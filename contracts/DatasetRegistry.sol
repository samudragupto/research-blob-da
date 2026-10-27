// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IDatasetRegistry} from "./interfaces/IDatasetRegistry.sol";
import {BlobLib} from "./libraries/BlobLib.sol";
import {JsonFieldLib} from "./libraries/JsonFieldLib.sol";
import {MerkleLib} from "./libraries/MerkleLib.sol";

/// @title DatasetRegistry
/// @author research-blob-da
/// @notice Anchors research datasets (tabular results, ML training traces, experiment logs, paper metadata)
///         whose bytes are published in EIP-4844 blobs, together with record-level Merkle commitments,
///         optimistic property claims, and permissionless attestations.
/// @dev Design notes (see docs/RESEARCH.md, Section 4).
///
///      Binding blobs to datasets. `openDataset` and `appendBlobs` must be called *inside* the type-3
///      transaction that carries the blobs. They read the versioned hashes with `BLOBHASH`, so the registry never
///      trusts a caller-supplied hash on this path. `appendExternalBlobs` exists for blobs published by other
///      means (aggregators, earlier transactions); such hashes are flagged and can later be content-bound with
///      {verifyBlobHeader}.
///
///      Retention-aware claims. Consensus clients only guarantee blob retrieval for 4096 epochs. A property
///      claim is therefore only meaningful while challengers can still download the data, so every claim's
///      challenge deadline equals the end of the retention window of the dataset's earliest blob, and claims
///      must leave at least `MIN_CHALLENGE_PERIOD` seconds for challengers. After the deadline, an unrefuted
///      claim is reported as `Unchallenged`, never as "proven".
///
///      Gas. Storage is packed into five slots per dataset; dynamic arrays hold versioned hashes; all failure
///      modes use custom errors. No external calls are made other than a static call to the point-evaluation
///      precompile, so the contract has no reentrancy surface.
contract DatasetRegistry is IDatasetRegistry {
    /// @notice Attestation kind: the attester retrieved the blobs and verified all commitments.
    bytes32 public constant ATTEST_RETRIEVED = keccak256("rbda.attest.retrieved-and-verified");
    /// @notice Attestation kind: the attester holds an archival copy beyond the blob retention window.
    bytes32 public constant ATTEST_ARCHIVED = keccak256("rbda.attest.archived-copy");
    /// @notice Attestation kind: the attester reproduced a result derived from the dataset.
    bytes32 public constant ATTEST_REPLICATED = keccak256("rbda.attest.replicated-result");

    /// @notice ASCII "RBDA", the magic number at the start of every blob payload.
    uint32 public constant HEADER_MAGIC = 0x52424441;
    /// @notice Blob payload format version understood by {verifyBlobHeader}.
    uint8 public constant HEADER_VERSION = 1;
    /// @notice Size of the blob header; it occupies exactly field element 0 under 31-byte packing.
    uint256 public constant HEADER_BYTES = 31;
    /// @notice Upper bound on blobs per dataset imposed by the 16-bit blob index in the header.
    uint256 public constant MAX_BLOBS_PER_DATASET = type(uint16).max;

    /// @notice Minimum time a claim must remain open to challenges.
    uint256 public immutable MIN_CHALLENGE_PERIOD;

    mapping(bytes32 datasetId => Dataset) private _datasets;
    mapping(bytes32 datasetId => bytes32[]) private _blobs;
    mapping(bytes32 datasetId => PropertyClaim[]) private _claims;
    mapping(bytes32 datasetId => mapping(uint256 blobIndex => bool)) private _headerVerified;
    mapping(bytes32 datasetId => uint256) private _attestations;

    /// @param minChallengePeriod Minimum challenge period in seconds; must be shorter than the retention window.
    constructor(uint64 minChallengePeriod) {
        if (minChallengePeriod >= BlobLib.BLOB_RETENTION_SECONDS) revert InvalidParams();
        MIN_CHALLENGE_PERIOD = minChallengePeriod;
    }

    // ---------------------------------------------------------------------------------------------------------
    // Publication
    // ---------------------------------------------------------------------------------------------------------

    /// @notice Opens a dataset and optionally registers the blobs carried by the current transaction.
    /// @dev The identifier is `keccak256(abi.encode(msg.sender, salt))`, which prevents identifier squatting by
    ///      front-runners: a copied transaction from another sender produces a different identifier.
    /// @param salt Researcher-chosen salt (for example, keccak256 of a human-readable dataset name).
    /// @param params Commitments and metadata.
    /// @param numTxBlobs Number of blobs of this transaction to register (0 to register later).
    /// @param finalize_ Whether to finalize immediately (requires at least one blob).
    /// @return datasetId The new dataset identifier.
    function openDataset(bytes32 salt, DatasetParams calldata params, uint256 numTxBlobs, bool finalize_)
        external
        returns (bytes32 datasetId)
    {
        if (
            params.recordCount == 0 || params.recordsRoot == bytes32(0) || params.contentHash == bytes32(0)
                || params.codec > 1 || params.layout > 1 || params.packing > 1
        ) revert InvalidParams();
        datasetId = computeDatasetId(msg.sender, salt);
        Dataset storage d = _datasets[datasetId];
        if (d.status != Status.None) revert DatasetAlreadyExists(datasetId);

        _datasets[datasetId] = Dataset({
            researcher: msg.sender,
            createdAt: uint40(block.timestamp),
            blobCount: 0,
            externalBlobCount: 0,
            recordsRoot: params.recordsRoot,
            contentHash: params.contentHash,
            metadataHash: params.metadataHash,
            rawSize: params.rawSize,
            encodedSize: params.encodedSize,
            recordCount: params.recordCount,
            codec: params.codec,
            layout: params.layout,
            packing: params.packing,
            status: Status.Open,
            firstBlobAt: 0
        });
        emit DatasetOpened(
            datasetId,
            msg.sender,
            params.recordsRoot,
            params.contentHash,
            params.metadataHash,
            params.recordCount
        );

        if (numTxBlobs != 0) _appendTxBlobs(datasetId, d, numTxBlobs);
        if (finalize_) _finalize(datasetId, d);
    }

    /// @notice Registers blobs of the current transaction for an open dataset.
    /// @dev Datasets larger than the per-transaction blob limit are published across several transactions.
    /// @param datasetId Dataset identifier.
    /// @param numTxBlobs Number of blobs of this transaction to register (non-zero).
    /// @param finalize_ Whether to finalize after appending.
    function appendBlobs(bytes32 datasetId, uint256 numTxBlobs, bool finalize_) external {
        Dataset storage d = _openDatasetOf(datasetId);
        if (numTxBlobs == 0) revert NoBlobs();
        _appendTxBlobs(datasetId, d, numTxBlobs);
        if (finalize_) _finalize(datasetId, d);
    }

    /// @notice Registers versioned hashes of blobs that were published outside this registry.
    /// @dev These hashes are not checked against any transaction, so they are counted in
    ///      `externalBlobCount`, they disable property claims, and they should be content-bound with
    ///      {verifyBlobHeader} before being relied upon.
    /// @param datasetId Dataset identifier.
    /// @param versionedHashes KZG versioned hashes (version byte `0x01`).
    /// @param finalize_ Whether to finalize after appending.
    function appendExternalBlobs(bytes32 datasetId, bytes32[] calldata versionedHashes, bool finalize_)
        external
    {
        Dataset storage d = _openDatasetOf(datasetId);
        uint256 n = versionedHashes.length;
        if (n == 0) revert NoBlobs();
        uint256 first = d.blobCount;
        if (first + n > MAX_BLOBS_PER_DATASET || uint256(d.externalBlobCount) + n > type(uint24).max) {
            revert TooManyBlobs();
        }
        bytes32[] storage arr = _blobs[datasetId];
        for (uint256 i; i < n;) {
            bytes32 h = versionedHashes[i];
            if (!BlobLib.isKzgVersionedHash(h)) revert InvalidVersionedHash(h);
            arr.push(h);
            unchecked {
                ++i;
            }
        }
        d.blobCount = uint32(first + n);
        d.externalBlobCount = uint24(uint256(d.externalBlobCount) + n);
        if (d.firstBlobAt == 0) d.firstBlobAt = uint40(block.timestamp);
        emit BlobsAppended(datasetId, first, versionedHashes, false);
        if (finalize_) _finalize(datasetId, d);
    }

    /// @notice Makes a dataset immutable.
    /// @param datasetId Dataset identifier.
    function finalize(bytes32 datasetId) external {
        Dataset storage d = _openDatasetOf(datasetId);
        _finalize(datasetId, d);
    }

    // ---------------------------------------------------------------------------------------------------------
    // Property claims
    // ---------------------------------------------------------------------------------------------------------

    /// @notice Posts an optimistic range claim over a numeric top-level field of every record.
    /// @dev `min`/`max` are refutable on-chain by any single committed record (see {refuteClaim}). `sum` is an
    ///      attested value: refuting it would require all records, which is checked off-chain by
    ///      `python/commitments.py::verify_property_claim`. The record count needs no claim because it is bound by
    ///      the Merkle commitment.
    /// @param datasetId Finalized dataset whose blobs were all read via `BLOBHASH`.
    /// @param key Top-level JSON key, restricted to `[A-Za-z0-9_.-]`.
    /// @param decimals Fixed-point scale of `min`, `max`, `sum` (at most 18).
    /// @param min Claimed minimum.
    /// @param max Claimed maximum.
    /// @param sum Claimed sum.
    /// @return claimIndex Index of the new claim.
    function postClaim(
        bytes32 datasetId,
        bytes calldata key,
        uint8 decimals,
        int128 min,
        int128 max,
        int256 sum
    ) external returns (uint256 claimIndex) {
        Dataset storage d = _existing(datasetId);
        if (d.researcher != msg.sender) revert NotResearcher(msg.sender);
        if (d.status != Status.Finalized) revert InvalidStatus(Status.Finalized, d.status);
        if (d.externalBlobCount != 0) revert ExternalBlobsPreventClaims();
        if (!JsonFieldLib.isValidKey(key) || decimals > JsonFieldLib.MAX_DECIMALS || min > max) {
            revert InvalidClaim();
        }
        uint256 deadline = uint256(d.firstBlobAt) + BlobLib.BLOB_RETENTION_SECONDS;
        if (block.timestamp + MIN_CHALLENGE_PERIOD > deadline) {
            revert ClaimWindowClosed(deadline, MIN_CHALLENGE_PERIOD);
        }
        PropertyClaim[] storage claims = _claims[datasetId];
        claimIndex = claims.length;
        claims.push(
            PropertyClaim({
                key: key,
                min: min,
                max: max,
                sum: sum,
                deadline: uint64(deadline),
                decimals: decimals,
                refuted: false,
                challenger: address(0)
            })
        );
        emit PropertyClaimed(datasetId, claimIndex, key, decimals, min, max, sum, uint64(deadline));
    }

    /// @notice Refutes a range claim by exhibiting a committed record whose field is missing, malformed, or out
    ///         of the claimed bounds.
    /// @dev Reverts with {NotAViolation} for records that satisfy the claim, so honest claims cannot be marked
    ///      refuted. Challengers obtain the record and its proof from the blob data during the retention window.
    /// @param datasetId Dataset identifier.
    /// @param claimIndex Claim to refute.
    /// @param recordIndex Position of the record.
    /// @param record Canonical record bytes.
    /// @param proof Merkle inclusion proof of the record.
    function refuteClaim(
        bytes32 datasetId,
        uint256 claimIndex,
        uint256 recordIndex,
        bytes calldata record,
        bytes32[] calldata proof
    ) external {
        Dataset storage d = _existing(datasetId);
        PropertyClaim[] storage claims = _claims[datasetId];
        if (claimIndex >= claims.length) revert ClaimNotFound(claimIndex);
        PropertyClaim storage c = claims[claimIndex];
        if (c.refuted) revert ClaimAlreadyRefuted(claimIndex);
        if (block.timestamp > c.deadline) revert ChallengeWindowClosed(c.deadline);
        if (!MerkleLib.verify(d.recordsRoot, d.recordCount, recordIndex, MerkleLib.hashRecord(record), proof))
        {
            revert InvalidRecordProof();
        }
        (bool ok, int256 v) = JsonFieldLib.readFixed(record, c.key, c.decimals);
        if (ok && v >= c.min && v <= c.max) revert NotAViolation();
        c.refuted = true;
        c.challenger = msg.sender;
        emit ClaimRefuted(datasetId, claimIndex, msg.sender, recordIndex);
    }

    // ---------------------------------------------------------------------------------------------------------
    // Content binding, citation, attestation
    // ---------------------------------------------------------------------------------------------------------

    /// @notice Proves, with the KZG point-evaluation precompile, that field element 0 of a registered blob
    ///         carries the header expected for this dataset and blob position.
    /// @dev Evaluating the blob polynomial at `z = 1` yields field element 0 because the first root of unity in
    ///      bit-reversal order is 1. The header encodes magic, version, codec, layout, packing, blob index, blob
    ///      count, body length, and the first 15 bytes of `contentHash`. This turns an opaque versioned hash into
    ///      an on-chain statement about blob *contents*, and it can be executed long after the blob was pruned by
    ///      anyone who kept the commitment and proof.
    /// @param datasetId Finalized dataset.
    /// @param blobIndex Position of the blob within the dataset.
    /// @param y Value of field element 0.
    /// @param commitment 48-byte KZG commitment of the blob.
    /// @param proof 48-byte KZG opening proof at `z = 1`.
    function verifyBlobHeader(
        bytes32 datasetId,
        uint256 blobIndex,
        uint256 y,
        bytes calldata commitment,
        bytes calldata proof
    ) external {
        Dataset storage d = _existing(datasetId);
        if (d.status != Status.Finalized) revert InvalidStatus(Status.Finalized, d.status);
        if (blobIndex >= d.blobCount) revert BlobNotFound(blobIndex);
        if (_headerVerified[datasetId][blobIndex]) revert HeaderAlreadyVerified(blobIndex);
        bytes32 vh = _blobs[datasetId][blobIndex];
        if (!BlobLib.verifyPointEvaluation(vh, 1, y, commitment, proof)) revert PointEvaluationFailed();
        _checkHeader(d, blobIndex, y);
        _headerVerified[datasetId][blobIndex] = true;
        emit BlobHeaderVerified(datasetId, blobIndex, vh);
    }

    /// @notice Verifies a record and emits a durable on-chain checkpoint of it.
    /// @dev Intended for citations: a paper can reference the transaction that checkpointed "record i of dataset
    ///      X", which remains verifiable from the Merkle root after the blob is pruned.
    /// @param datasetId Dataset identifier.
    /// @param recordIndex Position of the record.
    /// @param record Canonical record bytes.
    /// @param proof Merkle inclusion proof.
    /// @return leaf The verified leaf hash.
    function checkpointRecord(
        bytes32 datasetId,
        uint256 recordIndex,
        bytes calldata record,
        bytes32[] calldata proof
    ) external returns (bytes32 leaf) {
        Dataset storage d = _existing(datasetId);
        leaf = MerkleLib.hashRecord(record);
        if (!MerkleLib.verify(d.recordsRoot, d.recordCount, recordIndex, leaf, proof)) {
            revert InvalidRecordProof();
        }
        emit RecordCheckpointed(datasetId, recordIndex, leaf, msg.sender);
    }

    /// @notice Records a permissionless attestation about a dataset.
    /// @dev Attestations are signals, not proofs. `ATTEST_ARCHIVED` in particular is the hook for a future
    ///      extended-availability layer in which archivists stake on holding data past the retention window.
    /// @param datasetId Dataset identifier.
    /// @param kind Attestation kind (see the `ATTEST_*` constants; other values are allowed).
    /// @param evidenceHash Hash of off-chain evidence (for example, a signed retrieval report).
    function attest(bytes32 datasetId, bytes32 kind, bytes32 evidenceHash) external {
        _existing(datasetId);
        unchecked {
            ++_attestations[datasetId];
        }
        emit Attested(datasetId, msg.sender, kind, evidenceHash);
    }

    // ---------------------------------------------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------------------------------------------

    /// @inheritdoc IDatasetRegistry
    function computeDatasetId(address researcher, bytes32 salt) public pure returns (bytes32) {
        return keccak256(abi.encode(researcher, salt));
    }

    /// @inheritdoc IDatasetRegistry
    function getDataset(bytes32 datasetId) external view returns (Dataset memory) {
        return _existing(datasetId);
    }

    /// @inheritdoc IDatasetRegistry
    function blobHashes(bytes32 datasetId) external view returns (bytes32[] memory) {
        _existing(datasetId);
        return _blobs[datasetId];
    }

    /// @inheritdoc IDatasetRegistry
    function blobHashAt(bytes32 datasetId, uint256 blobIndex) external view returns (bytes32) {
        Dataset storage d = _existing(datasetId);
        if (blobIndex >= d.blobCount) revert BlobNotFound(blobIndex);
        return _blobs[datasetId][blobIndex];
    }

    /// @inheritdoc IDatasetRegistry
    function verifyRecord(
        bytes32 datasetId,
        uint256 recordIndex,
        bytes calldata record,
        bytes32[] calldata proof
    ) external view returns (bool) {
        Dataset storage d = _datasets[datasetId];
        return
            MerkleLib.verify(d.recordsRoot, d.recordCount, recordIndex, MerkleLib.hashRecord(record), proof);
    }

    /// @inheritdoc IDatasetRegistry
    function verifyRecordLeaf(bytes32 datasetId, uint256 recordIndex, bytes32 leaf, bytes32[] calldata proof)
        external
        view
        returns (bool)
    {
        Dataset storage d = _datasets[datasetId];
        return MerkleLib.verify(d.recordsRoot, d.recordCount, recordIndex, leaf, proof);
    }

    /// @inheritdoc IDatasetRegistry
    function verifyRecordRange(
        bytes32 datasetId,
        uint256 start,
        bytes[] calldata records,
        bytes32[] calldata proof
    ) external view returns (bool) {
        Dataset storage d = _datasets[datasetId];
        uint256 n = records.length;
        bytes32[] memory leaves = new bytes32[](n);
        for (uint256 i; i < n;) {
            leaves[i] = MerkleLib.hashRecord(records[i]);
            unchecked {
                ++i;
            }
        }
        return MerkleLib.verifyRange(d.recordsRoot, d.recordCount, start, leaves, proof);
    }

    /// @inheritdoc IDatasetRegistry
    function availabilityDeadline(bytes32 datasetId) public view returns (uint256) {
        uint256 first = _existing(datasetId).firstBlobAt;
        return first == 0 ? 0 : first + BlobLib.BLOB_RETENTION_SECONDS;
    }

    /// @inheritdoc IDatasetRegistry
    /// @dev Returns false when external blobs are present, because their inclusion time, and therefore their
    ///      pruning time, is unknown to the registry.
    function isWithinRetentionWindow(bytes32 datasetId) external view returns (bool) {
        Dataset storage d = _existing(datasetId);
        if (d.firstBlobAt == 0 || d.externalBlobCount != 0) return false;
        return block.timestamp <= uint256(d.firstBlobAt) + BlobLib.BLOB_RETENTION_SECONDS;
    }

    /// @inheritdoc IDatasetRegistry
    function claimCount(bytes32 datasetId) external view returns (uint256) {
        return _claims[datasetId].length;
    }

    /// @inheritdoc IDatasetRegistry
    function getClaim(bytes32 datasetId, uint256 claimIndex) external view returns (PropertyClaim memory) {
        if (claimIndex >= _claims[datasetId].length) revert ClaimNotFound(claimIndex);
        return _claims[datasetId][claimIndex];
    }

    /// @inheritdoc IDatasetRegistry
    function claimStatus(bytes32 datasetId, uint256 claimIndex) external view returns (ClaimStatus) {
        if (claimIndex >= _claims[datasetId].length) revert ClaimNotFound(claimIndex);
        PropertyClaim storage c = _claims[datasetId][claimIndex];
        if (c.refuted) return ClaimStatus.Refuted;
        if (block.timestamp > c.deadline) return ClaimStatus.Unchallenged;
        return ClaimStatus.Pending;
    }

    /// @inheritdoc IDatasetRegistry
    function isHeaderVerified(bytes32 datasetId, uint256 blobIndex) external view returns (bool) {
        return _headerVerified[datasetId][blobIndex];
    }

    /// @inheritdoc IDatasetRegistry
    function attestationCount(bytes32 datasetId) external view returns (uint256) {
        return _attestations[datasetId];
    }

    // ---------------------------------------------------------------------------------------------------------
    // Internal helpers
    // ---------------------------------------------------------------------------------------------------------

    function _existing(bytes32 datasetId) private view returns (Dataset storage d) {
        d = _datasets[datasetId];
        if (d.status == Status.None) revert DatasetNotFound(datasetId);
    }

    function _openDatasetOf(bytes32 datasetId) private view returns (Dataset storage d) {
        d = _existing(datasetId);
        if (d.researcher != msg.sender) revert NotResearcher(msg.sender);
        if (d.status != Status.Open) revert InvalidStatus(Status.Open, d.status);
    }

    function _appendTxBlobs(bytes32 datasetId, Dataset storage d, uint256 n) private {
        uint256 first = d.blobCount;
        if (first + n > MAX_BLOBS_PER_DATASET) revert TooManyBlobs();
        bytes32[] memory hashes = BlobLib.txBlobHashes(n);
        bytes32[] storage arr = _blobs[datasetId];
        for (uint256 i; i < n;) {
            arr.push(hashes[i]);
            unchecked {
                ++i;
            }
        }
        d.blobCount = uint32(first + n);
        if (d.firstBlobAt == 0) d.firstBlobAt = uint40(block.timestamp);
        emit BlobsAppended(datasetId, first, hashes, true);
    }

    function _finalize(bytes32 datasetId, Dataset storage d) private {
        if (d.blobCount == 0) revert NoBlobs();
        d.status = Status.Finalized;
        emit DatasetFinalized(datasetId, d.blobCount, d.recordCount);
    }

    /// @dev Header layout (31 bytes, big-endian): magic u32 | version u8 | codec u8 | layout u8 | packing u8 |
    ///      blobIndex u16 | blobCount u16 | bodyLength u32 | contentTag bytes15. Under 254-bit packing field
    ///      element 0 holds the header in its top 248 bits followed by 6 payload bits, hence the shift.
    function _checkHeader(Dataset storage d, uint256 blobIndex, uint256 y) private view {
        uint8 packing = d.packing;
        uint256 h = packing == 1 ? y >> 6 : y;
        if (h >> 248 != 0) revert HeaderMismatch(0);
        if (uint32(h >> 216) != HEADER_MAGIC) revert HeaderMismatch(1);
        if (uint8(h >> 208) != HEADER_VERSION) revert HeaderMismatch(2);
        if (uint8(h >> 200) != d.codec) revert HeaderMismatch(3);
        if (uint8(h >> 192) != d.layout) revert HeaderMismatch(4);
        if (uint8(h >> 184) != packing) revert HeaderMismatch(5);
        if (uint16(h >> 168) != blobIndex) revert HeaderMismatch(6);
        if (uint16(h >> 152) != d.blobCount) revert HeaderMismatch(7);
        uint256 capacity =
            (packing == 1 ? BlobLib.USABLE_BYTES_FE254 : BlobLib.USABLE_BYTES_FE31) - HEADER_BYTES;
        if (uint32(h >> 120) > capacity) revert HeaderMismatch(8);
        if (uint120(h) != uint120(uint256(d.contentHash) >> 136)) revert HeaderMismatch(9);
    }
}
