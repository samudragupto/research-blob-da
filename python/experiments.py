"""
Empirical Benchmark Suite for research-blob-da.

Conducts rigorous, reproducible experimental evaluation comparing EIP-4844 blobs
against Calldata, SSTORE, IPFS anchoring, and Cloud storage.

Experiments:
1. `benchmark_costs`: Cost comparison across 128 KiB, 1 MiB, 5 MiB, 20 MiB payloads.
2. `benchmark_encoding_efficiency`: Compression ratios, packing waste, and throughput across data types.
3. `benchmark_verification`: On-chain gas and off-chain execution times for Merkle proofs and property checks.
4. `benchmark_throughput_latency`: Latency breakdown for encoding, chunking, committing, and reconstruction.
5. `benchmark_ablations`: Ablation studies on zstd compression vs raw, and FE31 vs FE254 packing.

Outputs structured CSV files into `benchmarks/`.
"""

import math
import os
import time
from typing import Any

import numpy as np
import pandas as pd
import zstandard as zstd

from .canonical import deserialize_record_stream, serialize_record_stream
from .commitments import (
    MerkleTree,
    keccak256,
    verify_proof,
    verify_range_proof,
)
from .decoder import decode_dataset
from .encoder import (
    BYTES_PER_BLOB,
    HEADER_SIZE,
    USABLE_BYTES_FE31,
    USABLE_BYTES_FE254,
    encode_dataset,
)
from .generate_synthetic_data import (
    generate_academic_paper_metadata,
    generate_climate_timeseries,
    generate_genomics_benchmark,
    generate_ml_training_trace,
)

# -----------------------------------------------------------------------------
# Pricing and Economic Assumptions (Documented for academic rigor)
# -----------------------------------------------------------------------------
# Ethereum mainnet base execution gas price: 15 gwei
# Blob base fee: 1 gwei (target blob gas market) to 10 gwei (congested)
# ETH price assumption: $3,000 USD / ETH
#
# Gas mechanics (Cancun EVM / Pectra):
# - Standard tx base gas: 21,000
# - Calldata: 16 gas per non-zero byte (4 gas per zero byte; ~15.5 gas/byte weighted)
#   Under EIP-7623 (Pectra), calldata-dominated floor is 40 gas per non-zero byte.
# - Blob gas: exactly 131,072 blob gas per blob (2^17)
# - SSTORE: 22,100 gas per 32-byte slot (20,000 write + 2,100 cold access) -> ~690 gas/byte
# - IPFS + on-chain CID: 1 on-chain tx (~48,700 gas) + Filecoin/Pinata pinning (~$0.15/GB/month)
# - AWS S3 Standard: $0.023/GB/month + $0.005/1000 PUT requests
ETH_PRICE_USD = 3000.0
BASE_FEE_GWEI = 15.0
BLOB_FEE_GWEI = 2.0  # 2 gwei per blob gas unit (0.000262 ETH / blob = ~$0.78 / blob)
AWS_S3_PER_GB_MONTH_USD = 0.023
IPFS_PINNING_PER_GB_MONTH_USD = 0.15
ONE_YEAR_MONTHS = 12.0


def ensure_benchmark_dir(output_dir: str = "benchmarks") -> str:
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


# -----------------------------------------------------------------------------
# Experiment 1: Cost Comparison
# -----------------------------------------------------------------------------


def run_cost_comparison(output_dir: str = "benchmarks") -> pd.DataFrame:
    """Evaluates the monetary cost ($ USD) of publishing 128 KiB, 1 MiB, 5 MiB, and 20 MiB payloads.

    Compares:
    - EIP-4844 Blobs (DatasetRegistry registration + blob gas)
    - Calldata (16 gas/byte non-zero)
    - Calldata with EIP-7623 floor (40 gas/byte)
    - Permanent SSTORE storage (690 gas/byte)
    - IPFS + On-chain CID anchoring (tx fee + 1 year pinning)
    - AWS S3 (PUT request + 1 year storage)
    """
    sizes_bytes = [
        128 * 1024,  # 128 KiB (1 blob)
        1024 * 1024,  # 1 MiB (~8 blobs)
        5 * 1024 * 1024,  # 5 MiB (~40 blobs)
        20 * 1024 * 1024,  # 20 MiB (~160 blobs)
    ]
    rows: list[dict[str, Any]] = []

    for sz in sizes_bytes:
        sz_mib = sz / (1024 * 1024)
        sz_gb = sz / (1024 * 1024 * 1024)

        # 1. EIP-4844 Blobs
        # Raw capacity per blob with zstd compression (avg 2.8x ratio):
        # Raw 1 MiB compressed is ~370 KiB -> ~3 blobs.
        # But assuming uncompressed comparison for fair baseline:
        usable_per_blob = USABLE_BYTES_FE31 - HEADER_SIZE
        blobs_needed = math.ceil(sz / usable_per_blob)
        blob_gas = blobs_needed * BYTES_PER_BLOB
        blob_fee_eth = blob_gas * (BLOB_FEE_GWEI * 1e-9)
        blob_exec_gas = 168_000 + (blobs_needed - 1) * 35_000
        blob_exec_fee_eth = blob_exec_gas * (BASE_FEE_GWEI * 1e-9)
        blob_total_usd = (blob_fee_eth + blob_exec_fee_eth) * ETH_PRICE_USD

        # 2. Calldata (standard 16 gas/byte + 21k tx base)
        calldata_gas = 21_000 + (sz * 16)
        calldata_fee_eth = calldata_gas * (BASE_FEE_GWEI * 1e-9)
        calldata_total_usd = calldata_fee_eth * ETH_PRICE_USD

        # 3. Calldata under EIP-7623 (40 gas/byte for DA transactions)
        calldata_7623_gas = 21_000 + (sz * 40)
        calldata_7623_fee_eth = calldata_7623_gas * (BASE_FEE_GWEI * 1e-9)
        calldata_7623_total_usd = calldata_7623_fee_eth * ETH_PRICE_USD

        # 4. SSTORE permanent storage (690 gas/byte)
        # Note: 20 MiB SSTORE would exceed block gas limits, but is calculated theoretically
        sstore_gas = 21_000 + (sz * 690)
        sstore_fee_eth = sstore_gas * (BASE_FEE_GWEI * 1e-9)
        sstore_total_usd = sstore_fee_eth * ETH_PRICE_USD

        # 5. IPFS CID on-chain + 1 year pinning
        ipfs_tx_gas = 48_728
        ipfs_tx_usd = (ipfs_tx_gas * (BASE_FEE_GWEI * 1e-9)) * ETH_PRICE_USD
        ipfs_pin_usd = sz_gb * IPFS_PINNING_PER_GB_MONTH_USD * ONE_YEAR_MONTHS
        ipfs_total_usd = ipfs_tx_usd + ipfs_pin_usd

        # 6. AWS S3 Standard (1 year storage + 1 PUT)
        s3_storage_usd = sz_gb * AWS_S3_PER_GB_MONTH_USD * ONE_YEAR_MONTHS
        s3_put_usd = 0.005 / 1000.0
        s3_total_usd = s3_storage_usd + s3_put_usd

        # Savings multiplier of Blobs vs Calldata
        savings_vs_calldata = (
            calldata_total_usd / blob_total_usd if blob_total_usd > 0 else 0
        )

        rows.append(
            {
                "size_bytes": sz,
                "size_mib": sz_mib,
                "blobs_needed": blobs_needed,
                "cost_blob_usd": round(blob_total_usd, 4),
                "cost_calldata_usd": round(calldata_total_usd, 2),
                "cost_calldata_7623_usd": round(calldata_7623_total_usd, 2),
                "cost_sstore_usd": round(sstore_total_usd, 2),
                "cost_ipfs_1yr_usd": round(ipfs_total_usd, 4),
                "cost_s3_1yr_usd": round(s3_total_usd, 6),
                "blob_savings_vs_calldata_ratio": round(savings_vs_calldata, 1),
            }
        )

    df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, "cost_comparison.csv")
    df.to_csv(csv_path, index=False)
    print(f"[Experiment 1] Cost comparison saved to {csv_path}")
    return df


# -----------------------------------------------------------------------------
# Experiment 2: Encoding Efficiency Across Research Data Types
# -----------------------------------------------------------------------------


def run_encoding_efficiency(output_dir: str = "benchmarks") -> pd.DataFrame:
    """Measures compression ratio, payload packing efficiency, waste, and encoding throughput

    across tabular CSVs, JSON traces, and genomics records.
    """
    datasets = {
        "ML Training Trace (JSON)": generate_ml_training_trace(10000),
        "Climate Station Data (CSV/Tabular)": generate_climate_timeseries(20000),
        "Genomics Variant Benchmark": generate_genomics_benchmark(8000),
        "Academic Paper Metadata (JSON)": generate_academic_paper_metadata(5000),
    }

    rows: list[dict[str, Any]] = []

    for name, data in datasets.items():
        t0 = time.perf_counter()
        encoded = encode_dataset(data, codec=1, packing=0, zstd_level=3)
        t_enc = (time.perf_counter() - t0) * 1000.0  # ms

        raw_kb = encoded.raw_size / 1024.0
        enc_kb = encoded.encoded_size / 1024.0
        compression_ratio = (
            encoded.raw_size / encoded.encoded_size if encoded.encoded_size > 0 else 1.0
        )

        # Packing metrics
        total_blob_capacity_kb = (encoded.blob_count * USABLE_BYTES_FE31) / 1024.0
        utilized_kb = (encoded.encoded_size + encoded.blob_count * HEADER_SIZE) / 1024.0
        packing_waste_kb = total_blob_capacity_kb - utilized_kb
        packing_efficiency_pct = (utilized_kb / total_blob_capacity_kb) * 100.0

        rows.append(
            {
                "dataset_type": name,
                "record_count": encoded.record_count,
                "raw_size_kib": round(raw_kb, 2),
                "compressed_size_kib": round(enc_kb, 2),
                "compression_ratio": round(compression_ratio, 2),
                "blob_count": encoded.blob_count,
                "packing_efficiency_pct": round(packing_efficiency_pct, 1),
                "packing_waste_kib": round(packing_waste_kb, 2),
                "encoding_time_ms": round(t_enc, 2),
                "throughput_mibs": round(
                    (encoded.raw_size / (1024 * 1024)) / (t_enc / 1000.0), 2
                ),
            }
        )

    df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, "encoding_efficiency.csv")
    df.to_csv(csv_path, index=False)
    print(f"[Experiment 2] Encoding efficiency saved to {csv_path}")
    return df


# -----------------------------------------------------------------------------
# Experiment 3: Verification Costs (On-Chain Gas & Off-Chain Latency)
# -----------------------------------------------------------------------------


def run_verification_benchmarks(output_dir: str = "benchmarks") -> pd.DataFrame:
    """Measures single-leaf and range Merkle proof verification costs

    for trees of depth 4, 8, 12, 16 (16 to 65,536 records).
    """
    depths = [4, 8, 12, 16]
    rows: list[dict[str, Any]] = []

    for d in depths:
        leaf_count = 1 << d
        # Mock leaves
        leaves = [keccak256(f"record-{i}".encode()) for i in range(leaf_count)]
        tree = MerkleTree(leaves=leaves)

        target_idx = leaf_count // 2
        proof = tree.get_proof(target_idx)

        # Off-chain verification time (repeat 100 times for statistical precision)
        times = []
        for _ in range(100):
            t0 = time.perf_counter_ns()
            ok = verify_proof(
                tree.root, leaf_count, target_idx, leaves[target_idx], proof
            )
            assert ok
            times.append(time.perf_counter_ns() - t0)

        mean_us = np.mean(times) / 1000.0
        std_us = np.std(times) / 1000.0

        # Theoretical on-chain execution gas for verify:
        # base: ~3,200 gas + d * 750 gas (keccak256 of 65 bytes)
        estimated_gas = 3200 + d * 750

        # Range proof for 8 contiguous leaves
        range_len = 8
        range_proof = tree.get_range_proof(0, range_len)
        range_leaves = leaves[0:range_len]
        ok_range = verify_range_proof(
            tree.root, leaf_count, 0, range_leaves, range_proof
        )
        assert ok_range
        # Range proof is strictly cheaper than 8 individual proofs
        range_estimated_gas = 3800 + (len(range_proof) + range_len) * 450
        independent_8_gas = 8 * estimated_gas
        range_savings_pct = (1.0 - (range_estimated_gas / independent_8_gas)) * 100.0

        rows.append(
            {
                "tree_depth": d,
                "record_count": leaf_count,
                "proof_length_hashes": len(proof),
                "estimated_onchain_gas": estimated_gas,
                "offchain_verify_mean_us": round(mean_us, 2),
                "offchain_verify_std_us": round(std_us, 2),
                "range_proof_leaves": range_len,
                "range_proof_gas": range_estimated_gas,
                "range_vs_independent_savings_pct": round(range_savings_pct, 1),
            }
        )

    df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, "verification_benchmarks.csv")
    df.to_csv(csv_path, index=False)
    print(f"[Experiment 3] Verification benchmarks saved to {csv_path}")
    return df


# -----------------------------------------------------------------------------
# Experiment 4: Throughput & Latency Breakdown
# -----------------------------------------------------------------------------


def run_throughput_latency(output_dir: str = "benchmarks") -> pd.DataFrame:
    """Measures end-to-end latency across serialization, compression, Merkle hashing,

    chunking, and reconstruction.
    """
    trials = 5
    sizes = [1000, 5000, 15000, 30000]
    rows: list[dict[str, Any]] = []

    for n in sizes:
        records = generate_ml_training_trace(n)

        ser_times, comp_times, merkle_times, chunk_times, dec_times = [], [], [], [], []

        for _ in range(trials):
            # 1. Serialization
            t0 = time.perf_counter()
            raw_stream = serialize_record_stream(records)
            ser_times.append((time.perf_counter() - t0) * 1000.0)

            # 2. Compression
            t0 = time.perf_counter()
            cctx = zstd.ZstdCompressor(level=3)
            comp_stream = cctx.compress(raw_stream)
            comp_times.append((time.perf_counter() - t0) * 1000.0)

            # 3. Merkle tree construction
            t0 = time.perf_counter()
            canonical_records = deserialize_record_stream(raw_stream)
            MerkleTree(records=canonical_records)
            merkle_times.append((time.perf_counter() - t0) * 1000.0)

            # 4. Blob encoding & chunking
            t0 = time.perf_counter()
            encoded = encode_dataset(records, codec=1, packing=0)
            chunk_times.append((time.perf_counter() - t0) * 1000.0)

            # 5. Reconstruction & decoding
            t0 = time.perf_counter()
            decode_dataset(
                encoded.blobs,
                expected_content_hash=encoded.content_hash,
                expected_records_root=encoded.records_root,
            )
            dec_times.append((time.perf_counter() - t0) * 1000.0)

        total_times = [
            s + c + m + ch + d
            for s, c, m, ch, d in zip(
                ser_times, comp_times, merkle_times, chunk_times, dec_times
            )
        ]

        rows.append(
            {
                "record_count": n,
                "raw_kib": round(len(raw_stream) / 1024.0, 1),
                "compressed_kib": round(len(comp_stream) / 1024.0, 1),
                "serialization_ms_mean": round(float(np.mean(ser_times)), 2),
                "compression_ms_mean": round(float(np.mean(comp_times)), 2),
                "merkle_ms_mean": round(float(np.mean(merkle_times)), 2),
                "blob_packing_ms_mean": round(float(np.mean(chunk_times)), 2),
                "decode_verify_ms_mean": round(float(np.mean(dec_times)), 2),
                "total_pipeline_ms_mean": round(float(np.mean(total_times)), 2),
                "total_pipeline_ms_std": round(float(np.std(total_times)), 2),
            }
        )

    df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, "throughput_latency.csv")
    df.to_csv(csv_path, index=False)
    print(f"[Experiment 4] Throughput and latency saved to {csv_path}")
    return df


# -----------------------------------------------------------------------------
# Experiment 5: Ablation Studies (Compression & Packing Modes)
# -----------------------------------------------------------------------------


def run_ablations(output_dir: str = "benchmarks") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Runs ablation experiments:

    A. Compression ablation: Zstd (levels 1, 3, 9, 19) vs. Uncompressed (Raw)
    B. Packing ablation: FE31 (31 bytes/FE) vs. FE254 (dense 254 bits/FE)
    """
    data = generate_climate_timeseries(20000)

    # A. Compression Ablation
    comp_configs = [
        ("Raw (No compression)", 0, 0),
        ("Zstandard (Level 1 - Fast)", 1, 1),
        ("Zstandard (Level 3 - Default)", 1, 3),
        ("Zstandard (Level 9 - Balanced)", 1, 9),
        ("Zstandard (Level 19 - Max)", 1, 19),
    ]
    comp_rows: list[dict[str, Any]] = []

    for label, codec, lvl in comp_configs:
        t0 = time.perf_counter()
        enc = encode_dataset(data, codec=codec, zstd_level=lvl if codec == 1 else 3)
        t_enc = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        decode_dataset(enc.blobs, enc.content_hash, enc.records_root)
        t_dec = (time.perf_counter() - t0) * 1000.0

        ratio = enc.raw_size / enc.encoded_size
        comp_rows.append(
            {
                "configuration": label,
                "codec": codec,
                "zstd_level": lvl,
                "encoded_size_kib": round(enc.encoded_size / 1024.0, 2),
                "compression_ratio": round(ratio, 2),
                "blobs_required": enc.blob_count,
                "encode_time_ms": round(t_enc, 2),
                "decode_time_ms": round(t_dec, 2),
            }
        )

    df_comp = pd.DataFrame(comp_rows)
    comp_path = os.path.join(output_dir, "ablation_compression.csv")
    df_comp.to_csv(comp_path, index=False)
    print(f"[Experiment 5A] Compression ablation saved to {comp_path}")

    # B. Packing Strategy Ablation (FE31 vs FE254)
    packing_configs = [
        ("FE31 (Conservative 31 B / element)", 0),
        ("FE254 (Dense 254 bits / element)", 1),
    ]
    pack_rows: list[dict[str, Any]] = []

    for label, packing_mode in packing_configs:
        t0 = time.perf_counter()
        enc = encode_dataset(data, codec=1, packing=packing_mode)
        t_enc = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        decode_dataset(enc.blobs, enc.content_hash, enc.records_root)
        t_dec = (time.perf_counter() - t0) * 1000.0

        usable = USABLE_BYTES_FE254 if packing_mode == 1 else USABLE_BYTES_FE31
        pack_rows.append(
            {
                "packing_strategy": label,
                "packing_mode": packing_mode,
                "usable_bytes_per_blob": usable,
                "blobs_required": enc.blob_count,
                "encode_time_ms": round(t_enc, 2),
                "decode_time_ms": round(t_dec, 2),
            }
        )

    df_pack = pd.DataFrame(pack_rows)
    pack_path = os.path.join(output_dir, "ablation_packing.csv")
    df_pack.to_csv(pack_path, index=False)
    print(f"[Experiment 5B] Packing ablation saved to {pack_path}")

    return df_comp, df_pack


def run_all_experiments() -> None:
    """Executes the complete benchmark suite."""
    out_dir = ensure_benchmark_dir("benchmarks")
    print("=" * 65)
    print("STARTING COMPLETE EMPIRICAL BENCHMARK SUITE")
    print("=" * 65)

    run_cost_comparison(out_dir)
    run_encoding_efficiency(out_dir)
    run_verification_benchmarks(out_dir)
    run_throughput_latency(out_dir)
    run_ablations(out_dir)

    print("=" * 65)
    print("BENCHMARK SUITE FINISHED SUCCESSFULLY. CSVs generated in 'benchmarks/'.")
    print("=" * 65)


if __name__ == "__main__":
    run_all_experiments()
