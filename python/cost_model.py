"""
cost_model.py: Formal Ethereum Data-Availability and Storage Cost Model.

Provides exact, specification-compliant implementations of:
1. Usable blob payload capacity under 31-byte field-element packing (FE31).
2. EIP-7623 exact calldata floor and token calculations.
3. Theoretical SSTORE extrapolation with multi-block requirements.
4. EIP-4844 / Pectra / PeerDAS capacity and inclusion latency bounds.
5. Fee sensitivity grids and mathematical break-even blob fee derivations.
"""

import math
from typing import Any

# Protocol Constants
BYTES_PER_FIELD_ELEMENT = 32
FIELD_ELEMENTS_PER_BLOB = 4096
BYTES_PER_BLOB = BYTES_PER_FIELD_ELEMENT * FIELD_ELEMENTS_PER_BLOB  # 131,072 bytes
HEADER_SIZE = 31  # 31-byte domain header stored in Field Element 0

# Field Element Capacities
USABLE_BYTES_FE31_RAW = FIELD_ELEMENTS_PER_BLOB * 31  # 126,976 bytes
USABLE_BYTES_FE31_BODY = USABLE_BYTES_FE31_RAW - HEADER_SIZE  # 126,945 bytes

USABLE_BYTES_FE254_RAW = (FIELD_ELEMENTS_PER_BLOB * 254) // 8  # 130,048 bytes
USABLE_BYTES_FE254_BODY = USABLE_BYTES_FE254_RAW - HEADER_SIZE  # 130,017 bytes

# Default Economic Baseline
DEFAULT_ETH_PRICE_USD = 3000.0
DEFAULT_BASE_FEE_GWEI = 15.0
DEFAULT_BLOB_FEE_GWEI = 2.0
BLOCK_GAS_LIMIT = 30_000_000  # Standard Ethereum 30M gas target / limit


def get_usable_payload_bytes_per_blob(packing: str = "fe31") -> int:
    """Returns usable application payload bytes per blob after accounting for field element modulus and header.

    FE31: 4096 field elements * 31 bytes - 31 bytes (FE0 header) = 126,945 bytes.
    FE254: (4096 * 254) // 8 bytes - 31 bytes = 130,017 bytes.
    """
    if packing.lower() in ("fe31", "0"):
        return USABLE_BYTES_FE31_BODY
    elif packing.lower() in ("fe254", "1", "dense"):
        return USABLE_BYTES_FE254_BODY
    else:
        raise ValueError(f"Unknown packing strategy: {packing}")


def calculate_blobs_required(payload_size_bytes: int, packing: str = "fe31") -> int:
    """Calculates number of blobs required to carry a given payload size."""
    if payload_size_bytes <= 0:
        return 0
    usable = get_usable_payload_bytes_per_blob(packing)
    return math.ceil(payload_size_bytes / usable)


# -----------------------------------------------------------------------------
# EIP-7623 Formal Calculation
# -----------------------------------------------------------------------------


def calculate_eip7623_calldata_gas(
    payload: bytes, execution_gas_used: int = 0
) -> dict[str, Any]:
    """Calculates calldata and transaction gas under official EIP-7623 specification.

    EIP-7623 Parameters:
        STANDARD_TOKEN_COST = 4 (gas per token)
        TOTAL_COST_FLOOR_PER_TOKEN = 10 (gas per token)
        tokens_in_calldata = zero_bytes * 1 + nonzero_bytes * 4
        standard_tx_gas = 21000 + 4 * tokens_in_calldata + execution_gas_used
        floor_tx_gas = 21000 + 10 * tokens_in_calldata
        tx.gasUsed = 21000 + max(4 * tokens_in_calldata + execution_gas_used, 10 * tokens_in_calldata)

    Args:
        payload: Raw calldata payload bytes.
        execution_gas_used: Gas used for EVM execution excluding 21000 base gas (default 0 for DA sink).

    Returns:
        Dictionary containing exact gas metrics, tokens, and whether floor applied.
    """
    zero_bytes = payload.count(0)
    nonzero_bytes = len(payload) - zero_bytes

    tokens = (zero_bytes * 1) + (nonzero_bytes * 4)
    standard_calldata_gas = 4 * tokens  # 4 gas/zero, 16 gas/non-zero
    standard_tx_gas = 21000 + standard_calldata_gas + execution_gas_used

    floor_calldata_gas = 10 * tokens  # 10 gas/zero, 40 gas/non-zero
    floor_tx_gas = 21000 + floor_calldata_gas

    effective_tx_gas = 21000 + max(
        standard_calldata_gas + execution_gas_used, floor_calldata_gas
    )
    floor_applied = floor_calldata_gas > (standard_calldata_gas + execution_gas_used)

    effective_gas_per_byte = (
        (effective_tx_gas - 21000 - execution_gas_used) / len(payload)
        if len(payload) > 0
        else 0.0
    )

    return {
        "payload_length": len(payload),
        "zero_bytes": zero_bytes,
        "nonzero_bytes": nonzero_bytes,
        "tokens": tokens,
        "standard_calldata_gas": standard_calldata_gas,
        "standard_tx_gas": standard_tx_gas,
        "floor_calldata_gas": floor_calldata_gas,
        "floor_tx_gas": floor_tx_gas,
        "effective_tx_gas": effective_tx_gas,
        "floor_applied": floor_applied,
        "effective_gas_per_byte": round(effective_gas_per_byte, 3),
    }


# -----------------------------------------------------------------------------
# Theoretical SSTORE Extrapolation
# -----------------------------------------------------------------------------


def calculate_sstore_extrapolation(
    size_bytes: int,
    base_fee_gwei: float = DEFAULT_BASE_FEE_GWEI,
    eth_price_usd: float = DEFAULT_ETH_PRICE_USD,
    block_gas_limit: int = BLOCK_GAS_LIMIT,
) -> dict[str, Any]:
    """Calculates theoretical cost and block requirements to store raw bytes in contract storage slots.

    Assumptions (see contracts/baselines/SstoreArchive.sol):
    - 32 bytes per EVM storage slot.
    - 20,000 gas per zero-to-non-zero SSTORE write.
    - 2,100 gas cold account/slot access per slot.
    - Total per-slot gas: 22,100 gas (~690.625 gas/byte).
    - Base transaction intrinsic gas: 21,000.
    """
    if size_bytes <= 0:
        return {
            "size_bytes": 0,
            "slots": 0,
            "total_gas": 21000,
            "blocks_required": 1,
            "cost_eth": 0.0,
            "cost_usd": 0.0,
        }

    slots = math.ceil(size_bytes / 32)
    sstore_write_gas = slots * 20_000
    sstore_cold_gas = slots * 2_100
    total_gas = 21_000 + sstore_write_gas + sstore_cold_gas

    blocks_required = math.ceil(total_gas / block_gas_limit)
    cost_eth = total_gas * (base_fee_gwei * 1e-9)
    cost_usd = cost_eth * eth_price_usd

    return {
        "size_bytes": size_bytes,
        "slots": slots,
        "sstore_write_gas": sstore_write_gas,
        "sstore_cold_gas": sstore_cold_gas,
        "total_gas": total_gas,
        "gas_per_byte": round(total_gas / size_bytes, 2),
        "blocks_required": blocks_required,
        "cost_eth": round(cost_eth, 6),
        "cost_usd": round(cost_usd, 2),
    }


# -----------------------------------------------------------------------------
# Blob Capacity, Transaction, and Block Inclusion Time Model
# -----------------------------------------------------------------------------


def calculate_capacity_and_inclusion(
    size_bytes: int,
    is_compressed: bool = False,
    compressed_size_bytes: int | None = None,
    packing: str = "fe31",
) -> dict[str, Any]:
    """Calculates blob requirements, transaction count, block count, and inclusion latency across protocol eras.

    Configurations:
    1. Cancun / Current Mainnet (EIP-4844): target 3 blobs/block, max 6 blobs/block, max 6 blobs/tx.
    2. Pectra (EIP-7691): target 6 blobs/block, max 9 blobs/block, max 9 blobs/tx.
    3. PeerDAS (EIP-7594 Illustrative Projection): target 32 blobs/block, max 64 blobs/block, max 64 blobs/tx.
    """
    effective_bytes = (
        compressed_size_bytes
        if (is_compressed and compressed_size_bytes is not None)
        else size_bytes
    )
    blobs = calculate_blobs_required(effective_bytes, packing)

    slot_time_sec = 12.0

    configs = {
        "cancun": {
            "name": "Cancun (EIP-4844)",
            "target_blobs": 3,
            "max_blobs": 6,
            "max_tx_blobs": 6,
        },
        "pectra": {
            "name": "Pectra (EIP-7691)",
            "target_blobs": 6,
            "max_blobs": 9,
            "max_tx_blobs": 9,
        },
        "peerdas": {
            "name": "PeerDAS (EIP-7594 Projection)",
            "target_blobs": 32,
            "max_blobs": 64,
            "max_tx_blobs": 64,
        },
    }

    results: dict[str, Any] = {
        "raw_size_bytes": size_bytes,
        "effective_size_bytes": effective_bytes,
        "blobs_needed": blobs,
        "regimes": {},
    }

    for key, cfg in configs.items():
        min_txs = math.ceil(blobs / cfg["max_tx_blobs"])
        min_blocks_max = math.ceil(blobs / cfg["max_blobs"])
        min_time_max_sec = min_blocks_max * slot_time_sec

        min_blocks_target = math.ceil(blobs / cfg["target_blobs"])
        min_time_target_sec = min_blocks_target * slot_time_sec

        results["regimes"][key] = {
            "regime_name": cfg["name"],
            "target_blobs_per_block": cfg["target_blobs"],
            "max_blobs_per_block": cfg["max_blobs"],
            "min_transactions": min_txs,
            "min_blocks_burst": min_blocks_max,
            "inclusion_time_burst_sec": round(min_time_max_sec, 1),
            "min_blocks_target": min_blocks_target,
            "inclusion_time_target_sec": round(min_time_target_sec, 1),
        }

    return results


# -----------------------------------------------------------------------------
# Fee Sensitivity & Break-Even Analysis
# -----------------------------------------------------------------------------


def calculate_breakeven_blob_fee(
    size_bytes: int,
    base_fee_gwei: float = DEFAULT_BASE_FEE_GWEI,
    packing: str = "fe31",
) -> float:
    """Calculates the break-even blob base fee (gwei) where blob posting equals calldata posting.

    Derivation:
        Cost_calldata = (21,000 + 16 * size_bytes) * base_fee * 1e-9
        Cost_blob = [exec_gas * base_fee + (blobs * 131,072) * blob_fee] * 1e-9
        Where exec_gas = 168,000 + (blobs - 1) * 35,000

        Setting Cost_calldata == Cost_blob:
        (blobs * 131,072) * blob_fee = (21,000 + 16 * size_bytes - exec_gas) * base_fee
        blob_fee = [(21,000 + 16 * size_bytes - exec_gas) / (blobs * 131,072)] * base_fee
    """
    blobs = calculate_blobs_required(size_bytes, packing)
    if blobs == 0:
        return 0.0

    calldata_gas = 21_000 + (size_bytes * 16)
    exec_gas = 168_000 + (blobs - 1) * 35_000
    blob_gas = blobs * BYTES_PER_BLOB

    breakeven_gwei = ((calldata_gas - exec_gas) / blob_gas) * base_fee_gwei
    return max(0.0, breakeven_gwei)


def calculate_fee_sensitivity_grid(
    size_bytes: int,
    base_fee_levels: list[float] | None = None,
    blob_fee_levels: list[float] | None = None,
    eth_price_usd: float = DEFAULT_ETH_PRICE_USD,
    packing: str = "fe31",
) -> list[dict[str, Any]]:
    """Generates sensitivity table of blob vs calldata costs across execution and blob gas markets."""
    if base_fee_levels is None:
        base_fee_levels = [5.0, 10.0, 15.0, 25.0, 50.0, 100.0]
    if blob_fee_levels is None:
        blob_fee_levels = [1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0]

    blobs = calculate_blobs_required(size_bytes, packing)
    exec_gas = 168_000 + (blobs - 1) * 35_000
    blob_gas = blobs * BYTES_PER_BLOB
    calldata_gas = 21_000 + (size_bytes * 16)

    rows: list[dict[str, Any]] = []

    for p_base in base_fee_levels:
        calldata_cost_eth = calldata_gas * (p_base * 1e-9)
        calldata_cost_usd = calldata_cost_eth * eth_price_usd

        for p_blob in blob_fee_levels:
            blob_cost_eth = (exec_gas * p_base * 1e-9) + (blob_gas * p_blob * 1e-9)
            blob_cost_usd = blob_cost_eth * eth_price_usd

            savings_ratio = (
                calldata_cost_usd / blob_cost_usd if blob_cost_usd > 0 else 1.0
            )

            rows.append(
                {
                    "size_bytes": size_bytes,
                    "size_mib": round(size_bytes / (1024 * 1024), 2),
                    "blobs_needed": blobs,
                    "base_fee_gwei": p_base,
                    "blob_fee_gwei": p_blob,
                    "calldata_cost_eth": round(calldata_cost_eth, 6),
                    "calldata_cost_usd": round(calldata_cost_usd, 2),
                    "blob_cost_eth": round(blob_cost_eth, 6),
                    "blob_cost_usd": round(blob_cost_usd, 2),
                    "savings_ratio": round(savings_ratio, 2),
                    "cost_per_mib_blob_usd": round(
                        blob_cost_usd / (size_bytes / (1024 * 1024)), 2
                    ),
                    "cost_per_mib_calldata_usd": round(
                        calldata_cost_usd / (size_bytes / (1024 * 1024)), 2
                    ),
                }
            )

    return rows
