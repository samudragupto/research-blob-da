"""
test_cost_model.py: Formal Unit Tests for Cost, EIP-7623, Capacity, and Sensitivity Models.
"""

from python.cost_model import (
    HEADER_SIZE,
    calculate_blobs_required,
    calculate_breakeven_blob_fee,
    calculate_capacity_and_inclusion,
    calculate_eip7623_calldata_gas,
    calculate_fee_sensitivity_grid,
    calculate_sstore_extrapolation,
    get_usable_payload_bytes_per_blob,
)


def test_usable_payload_capacity_formula():
    """Validates mathematical derivation of usable payload bytes per blob."""
    # FE31: 4096 * 31 - 31 = 126,945 bytes
    fe31_cap = get_usable_payload_bytes_per_blob("fe31")
    assert fe31_cap == 126945
    assert fe31_cap == (4096 * 31) - HEADER_SIZE

    # FE254: (4096 * 254 // 8) - 31 = 130,017 bytes
    fe254_cap = get_usable_payload_bytes_per_blob("fe254")
    assert fe254_cap == 130017
    assert fe254_cap == ((4096 * 254) // 8) - HEADER_SIZE


def test_blob_counts_across_standard_dataset_sizes():
    """Validates blob count calculations across theoretical uncompressed sizes."""
    # 128 KiB = 131,072 bytes -> ceil(131,072 / 126,945) = 2 blobs
    assert calculate_blobs_required(128 * 1024, "fe31") == 2

    # 1.0 MiB = 1,048,576 bytes -> ceil(1,048,576 / 126,945) = 9 blobs
    assert calculate_blobs_required(1024 * 1024, "fe31") == 9

    # 5.0 MiB = 5,242,880 bytes -> ceil(5,242,880 / 126,945) = 42 blobs
    assert calculate_blobs_required(5 * 1024 * 1024, "fe31") == 42

    # 20.0 MiB = 20,971,520 bytes -> ceil(20,971,520 / 126,945) = 166 blobs
    assert calculate_blobs_required(20 * 1024 * 1024, "fe31") == 166


def test_eip7623_vector_all_zeros():
    """Tests EIP-7623 token and floor calculation on all-zero byte payload."""
    payload = bytes(1000)  # 1,000 zero bytes
    res = calculate_eip7623_calldata_gas(payload, execution_gas_used=0)

    assert res["zero_bytes"] == 1000
    assert res["nonzero_bytes"] == 0
    assert res["tokens"] == 1000  # 1 token per zero byte
    assert res["standard_calldata_gas"] == 4000  # 4 gas per token
    assert res["standard_tx_gas"] == 25000  # 21,000 + 4,000
    assert res["floor_calldata_gas"] == 10000  # 10 gas per token
    assert res["floor_tx_gas"] == 31000  # 21,000 + 10,000
    assert res["effective_tx_gas"] == 31000
    assert res["floor_applied"] is True
    assert res["effective_gas_per_byte"] == 10.0


def test_eip7623_vector_all_nonzeros():
    """Tests EIP-7623 token and floor calculation on all non-zero byte payload."""
    payload = bytes([0xFF] * 1000)  # 1,000 non-zero bytes
    res = calculate_eip7623_calldata_gas(payload, execution_gas_used=0)

    assert res["zero_bytes"] == 0
    assert res["nonzero_bytes"] == 1000
    assert res["tokens"] == 4000  # 4 tokens per non-zero byte
    assert res["standard_calldata_gas"] == 16000  # 16 gas per non-zero byte
    assert res["standard_tx_gas"] == 37000  # 21,000 + 16,000
    assert (
        res["floor_calldata_gas"] == 40000
    )  # 40 gas per non-zero byte (4 tokens * 10)
    assert res["floor_tx_gas"] == 61000  # 21,000 + 40,000
    assert res["effective_tx_gas"] == 61000
    assert res["floor_applied"] is True
    assert res["effective_gas_per_byte"] == 40.0


def test_eip7623_high_execution_gas_floor_not_applied():
    """Tests that regular compute-heavy transactions do not hit the EIP-7623 floor."""
    payload = bytes(
        [0xAA] * 500
    )  # 500 non-zero bytes (tokens = 2000, floor = 20,000 calldata)
    # 50,000 EVM execution gas
    res = calculate_eip7623_calldata_gas(payload, execution_gas_used=50000)

    assert res["standard_calldata_gas"] == 8000
    assert res["floor_calldata_gas"] == 20000
    # standard_tx_gas = 21,000 + 8,000 + 50,000 = 79,000 gas
    # floor_tx_gas = 21,000 + 20,000 = 41,000 gas
    assert res["standard_tx_gas"] == 79000
    assert res["floor_tx_gas"] == 41000
    assert res["effective_tx_gas"] == 79000
    assert res["floor_applied"] is False


def test_eip7623_realistic_json_payload():
    """Validates EIP-7623 behavior on real JSON text bytes."""
    payload = b'{"id":"https://openalex.org/W12345","title":"Empirical Analysis","citations":42}'
    res = calculate_eip7623_calldata_gas(payload, execution_gas_used=0)

    # In ASCII JSON, there are zero 0x00 bytes
    assert res["zero_bytes"] == 0
    assert res["nonzero_bytes"] == len(payload)
    assert res["effective_gas_per_byte"] == 40.0
    assert res["floor_applied"] is True


def test_sstore_extrapolation_bounds():
    """Validates theoretical SSTORE extrapolation calculations and block count barriers."""
    # 1.0 MiB payload
    sz_1mib = 1024 * 1024
    res_1mib = calculate_sstore_extrapolation(sz_1mib)

    assert res_1mib["slots"] == 32768
    # 32,768 slots * 22,100 gas + 21,000 = 724,193,800 gas
    assert res_1mib["total_gas"] > 700_000_000
    # Over 24 Ethereum blocks required at 30M gas limit
    assert res_1mib["blocks_required"] >= 24

    # 20.0 MiB payload
    sz_20mib = 20 * 1024 * 1024
    res_20mib = calculate_sstore_extrapolation(sz_20mib)
    assert res_20mib["slots"] == 655360
    assert res_20mib["blocks_required"] >= 480


def test_capacity_and_inclusion_time_model():
    """Validates transaction, block, and inclusion time modeling across protocol regimes."""
    res = calculate_capacity_and_inclusion(1024 * 1024, is_compressed=False)
    assert res["blobs_needed"] == 9

    regimes = res["regimes"]

    # Cancun (max 6 blobs per tx, 6 per block, target 3)
    cancun = regimes["cancun"]
    assert cancun["min_transactions"] == 2  # ceil(9 / 6)
    assert cancun["min_blocks_burst"] == 2  # ceil(9 / 6)
    assert cancun["inclusion_time_burst_sec"] == 24.0  # 2 * 12s
    assert cancun["min_blocks_target"] == 3  # ceil(9 / 3)
    assert cancun["inclusion_time_target_sec"] == 36.0  # 3 * 12s

    # Pectra (max 9 blobs per tx, 9 per block, target 6)
    pectra = regimes["pectra"]
    assert pectra["min_transactions"] == 1  # fits in 1 transaction
    assert pectra["min_blocks_burst"] == 1
    assert pectra["inclusion_time_burst_sec"] == 12.0
    assert pectra["min_blocks_target"] == 2
    assert pectra["inclusion_time_target_sec"] == 24.0

    # PeerDAS (max 64 blobs per block)
    peerdas = regimes["peerdas"]
    assert peerdas["min_transactions"] == 1
    assert peerdas["min_blocks_burst"] == 1
    assert peerdas["inclusion_time_burst_sec"] == 12.0


def test_breakeven_blob_fee_derivation():
    """Validates break-even blob fee calculation against analytical derivation."""
    # At 1 MiB, base_fee = 15 gwei:
    # blobs = 9, exec_gas = 168k + 8 * 35k = 448k
    # calldata_gas = 21,000 + 1,048,576 * 16 = 16,798,216
    # net_exec = 16,798,216 - 448,000 = 16,350,216
    # blob_gas = 9 * 131,072 = 1,179,648
    # ratio = 16,350,216 / 1,179,648 = ~13.86
    # breakeven = 13.86 * 15 = ~207.9 gwei
    be = calculate_breakeven_blob_fee(1024 * 1024, base_fee_gwei=15.0)
    assert 200.0 < be < 215.0

    # If base fee doubles to 30 gwei, breakeven fee doubles proportionally
    be_30 = calculate_breakeven_blob_fee(1024 * 1024, base_fee_gwei=30.0)
    assert abs(be_30 - (2 * be)) < 1e-4


def test_fee_sensitivity_grid_generation():
    """Validates fee sensitivity grid contains expected rows and realistic savings."""
    grid = calculate_fee_sensitivity_grid(1024 * 1024)
    assert len(grid) == 48  # 6 base fee levels * 8 blob fee levels

    # Check first row (base=5, blob=1)
    row0 = grid[0]
    assert row0["base_fee_gwei"] == 5.0
    assert row0["blob_fee_gwei"] == 1.0
    assert row0["savings_ratio"] > 10.0  # Blobs are significantly cheaper

    # Check high congestion row (base=15, blob=200)
    cong = next(
        r for r in grid if r["base_fee_gwei"] == 15.0 and r["blob_fee_gwei"] == 200.0
    )
    assert (
        cong["savings_ratio"] > 1.0
    )  # Still slightly cheaper at 200 gwei (break-even is ~208 gwei)
