// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title BlobLib
/// @author research-blob-da
/// @notice Constants and helpers for working with EIP-4844 blobs from the execution layer.
/// @dev Research rationale. From the EVM, a blob is visible only through its 32-byte versioned hash
///      (`BLOBHASH` opcode, EIP-4844) and through the KZG point-evaluation precompile at address `0x0a`.
///      The blob bytes themselves are never accessible to contracts and are pruned by consensus clients after
///      `MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS = 4096` epochs (about 18.2 days). This library collects the
///      protocol constants and the two on-chain primitives that a research-data registry can rely on:
///
///      1. Reading the versioned hashes of the *current* transaction. Recording them from inside the blob
///         transaction is the only way for a contract to know, without trusting the caller, that the hashes
///         correspond to blobs that were actually propagated and made available by the network.
///      2. Point evaluation. Given a commitment and proof, the precompile convinces the contract that the
///         blob polynomial evaluates to `y` at `z`. Evaluating at `z = 1` (the first root of unity in
///         bit-reversed order) reveals field element 0 of the blob, which carries the dataset header.
///         This binds blob *contents* to a dataset on-chain and keeps working after the blob is pruned,
///         provided someone retained the 48-byte commitment and the 48-byte proof.
library BlobLib {
    /// @notice Thrown when fewer blobs are attached to the transaction than requested.
    /// @param index The first index for which `blobhash` returned zero.
    error BlobIndexMissing(uint256 index);

    /// @notice Number of field elements per blob.
    uint256 internal constant FIELD_ELEMENTS_PER_BLOB = 4096;
    /// @notice Raw size of a blob in bytes.
    uint256 internal constant BYTES_PER_BLOB = 131_072;
    /// @notice Blob gas charged per blob (2**17).
    uint256 internal constant GAS_PER_BLOB = 131_072;
    /// @notice Usable payload bytes per blob with the conservative 31-bytes-per-element packing.
    uint256 internal constant USABLE_BYTES_FE31 = 126_976;
    /// @notice Usable payload bytes per blob with dense 254-bits-per-element packing.
    uint256 internal constant USABLE_BYTES_FE254 = 130_048;
    /// @notice Beacon chain slot time in seconds.
    uint256 internal constant SECONDS_PER_SLOT = 12;
    /// @notice Slots per beacon epoch.
    uint256 internal constant SLOTS_PER_EPOCH = 32;
    /// @notice Minimum number of epochs for which consensus clients must serve blob sidecars.
    uint256 internal constant MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS = 4096;
    /// @notice Guaranteed availability window in seconds (4096 * 32 * 12 = 1 572 864 s, about 18.2 days).
    uint256 internal constant BLOB_RETENTION_SECONDS =
        MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS * SLOTS_PER_EPOCH * SECONDS_PER_SLOT;
    /// @notice Version byte of KZG-based versioned hashes.
    bytes1 internal constant VERSIONED_HASH_VERSION_KZG = 0x01;
    /// @notice Address of the KZG point-evaluation precompile.
    address internal constant POINT_EVALUATION_PRECOMPILE = address(0x0a);
    /// @notice Scalar field modulus of BLS12-381; every field element of a blob must be below it.
    uint256 internal constant BLS_MODULUS =
        52_435_875_175_126_190_479_447_740_508_185_965_837_690_552_500_527_637_822_603_658_699_938_581_184_513;

    /// @notice Reads the first `count` versioned hashes of the current transaction.
    /// @dev Reverts if the transaction carries fewer than `count` blobs, so a successful call proves that each
    ///      returned hash belongs to a blob included in this very transaction.
    /// @param count Number of hashes to read.
    /// @return hashes The versioned hashes, in sidecar order.
    function txBlobHashes(uint256 count) internal view returns (bytes32[] memory hashes) {
        hashes = new bytes32[](count);
        for (uint256 i; i < count;) {
            bytes32 h = blobhash(i);
            if (h == bytes32(0)) revert BlobIndexMissing(i);
            hashes[i] = h;
            unchecked {
                ++i;
            }
        }
    }

    /// @notice Counts the blobs attached to the current transaction.
    /// @dev Bounded by the protocol's per-transaction blob limit.
    /// @return n Number of blobs.
    function txBlobCount() internal view returns (uint256 n) {
        while (blobhash(n) != bytes32(0)) {
            unchecked {
                ++n;
            }
        }
    }

    /// @notice Returns true if `h` carries the KZG version byte.
    /// @param h Candidate versioned hash.
    /// @return True if the first byte equals `0x01`.
    function isKzgVersionedHash(bytes32 h) internal pure returns (bool) {
        return h[0] == VERSIONED_HASH_VERSION_KZG;
    }

    /// @notice Computes `0x01 || sha256(commitment)[1:]`, the EIP-4844 versioned hash of a KZG commitment.
    /// @dev Lets a verifier check a retrieved sidecar commitment against a stored hash without trusting the
    ///      data source.
    /// @param commitment 48-byte compressed G1 point.
    /// @return The versioned hash.
    function versionedHash(bytes memory commitment) internal pure returns (bytes32) {
        bytes32 digest = sha256(commitment);
        return (digest & 0x00ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff)
            | bytes32(uint256(uint8(VERSIONED_HASH_VERSION_KZG)) << 248);
    }

    /// @notice Calls the point-evaluation precompile.
    /// @param vh Versioned hash the commitment must match.
    /// @param z Evaluation point (must be below `BLS_MODULUS`).
    /// @param y Claimed evaluation (must be below `BLS_MODULUS`).
    /// @param commitment 48-byte KZG commitment.
    /// @param proof 48-byte KZG opening proof.
    /// @return True if and only if `p(z) == y` for the blob polynomial committed to by `vh`.
    function verifyPointEvaluation(
        bytes32 vh,
        uint256 z,
        uint256 y,
        bytes calldata commitment,
        bytes calldata proof
    ) internal view returns (bool) {
        if (commitment.length != 48 || proof.length != 48) return false;
        (bool ok, bytes memory out) =
            POINT_EVALUATION_PRECOMPILE.staticcall(abi.encodePacked(vh, z, y, commitment, proof));
        if (!ok || out.length != 64) return false;
        (uint256 fe, uint256 modulus) = abi.decode(out, (uint256, uint256));
        return fe == FIELD_ELEMENTS_PER_BLOB && modulus == BLS_MODULUS;
    }
}
