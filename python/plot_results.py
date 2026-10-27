"""
Plotting Script for research-blob-da Academic Evaluation.

Generates publication-quality figures (both high-res PNG and PDF) using Matplotlib & Seaborn:
- `figure1_cost_comparison.png` / `.pdf`: Log-scale monetary cost comparison across storage primitives.
- `figure2_compression_efficiency.png` / `.pdf`: Compression ratios and packing efficiency across synthetic and real datasets.
- `figure3_verification_scaling.png` / `.pdf`: Single-leaf vs range proof verification gas and off-chain latency.
- `figure4_latency_breakdown.png` / `.pdf`: Stacked latency breakdown as dataset record count scales.
- `figure5_compression_ablation.png` / `.pdf`: Compression ratio vs encoding latency Pareto frontier.
- `figure6_fee_sensitivity.png` / `.pdf`: Fee sensitivity curves and break-even blob fee operating envelope.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Academic styling
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "figure.dpi": 300,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    }
)


def plot_cost_comparison(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    csv_path = os.path.join(benchmarks_dir, "cost_comparison_uncompressed.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(benchmarks_dir, "cost_comparison.csv")
    if not os.path.exists(csv_path):
        print(f"Skipping plot_cost_comparison: {csv_path} not found")
        return
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(8.5, 5.2))

    x = np.arange(len(df))
    width = 0.18

    calldata_col = (
        "cost_calldata_standard_usd"
        if "cost_calldata_standard_usd" in df.columns
        else "cost_calldata_usd"
    )
    sstore_col = (
        "sstore_theoretical_extrapolated_usd"
        if "sstore_theoretical_extrapolated_usd" in df.columns
        else "cost_sstore_usd"
    )

    ax.bar(
        x - 1.5 * width,
        df["cost_blob_usd"],
        width,
        label="EIP-4844 Blobs",
        color="#1f77b4",
    )
    ax.bar(
        x - 0.5 * width,
        df[calldata_col],
        width,
        label="Calldata (Standard 16 gas/byte)",
        color="#ff7f0e",
    )
    ax.bar(
        x + 0.5 * width,
        df[sstore_col],
        width,
        label="Theoretical SSTORE Extrapolation*",
        color="#9467bd",
    )
    ax.bar(
        x + 1.5 * width,
        df["cost_ipfs_1yr_usd"],
        width,
        label="IPFS + On-chain CID (1 yr)",
        color="#2ca02c",
    )

    ax.set_ylabel("Publication Cost (USD, Log Scale)")
    ax.set_title(
        "Publication Cost Comparison Across Storage Primitives (Table A Baseline)"
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{mib:.2f} MiB" if mib < 1 else f"{int(mib)} MiB" for mib in df["size_mib"]]
    )
    ax.set_yscale("log")
    ax.legend(frameon=True, facecolor="white", framealpha=0.9, loc="upper left")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        p = os.path.join(output_dir, f"figure1_cost_comparison.{ext}")
        fig.savefig(p)
    plt.close(fig)
    print("Generated figure1_cost_comparison")


def plot_compression_efficiency(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    csv_path = os.path.join(benchmarks_dir, "encoding_efficiency.csv")
    if not os.path.exists(csv_path):
        return
    df = pd.read_csv(csv_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))

    short_names = [n.split(" (")[0] for n in df["dataset_type"]]
    colors = ["#2b5c8f", "#388e3c", "#d32f2f", "#7b1fa2", "#e65100"]

    # 1. Compression ratio
    bars1 = ax1.bar(
        short_names, df["compression_ratio"], color=colors[: len(df)], width=0.55
    )
    ax1.set_ylabel("Compression Ratio (Raw Size / Compressed Size)")
    ax1.set_title("Zstandard Compression Ratio by Data Type")
    ax1.set_xticklabels(short_names, rotation=20, ha="right")
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + 0.2,
            f"{yval:.1f}x",
            ha="center",
            va="bottom",
            weight="bold",
        )

    # 2. Packing efficiency
    bars2 = ax2.bar(
        short_names, df["packing_efficiency_pct"], color=colors[: len(df)], width=0.55
    )
    ax2.set_ylabel("Blob Space Utilization (%)")
    ax2.set_title("Blob Payload Packing Efficiency (FE31)")
    ax2.set_xticklabels(short_names, rotation=20, ha="right")
    ax2.set_ylim(0, 105)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + 1.5,
            f"{yval:.1f}%",
            ha="center",
            va="bottom",
            weight="bold",
        )

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(output_dir, f"figure2_compression_efficiency.{ext}"))
    plt.close(fig)
    print("Generated figure2_compression_efficiency")


def plot_verification_scaling(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    csv_path = os.path.join(benchmarks_dir, "verification_benchmarks.csv")
    if not os.path.exists(csv_path):
        return
    df = pd.read_csv(csv_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.plot(
        df["tree_depth"],
        df["estimated_onchain_gas"],
        marker="o",
        color="#1f77b4",
        linewidth=2,
        label="Single-leaf Proof",
    )
    ax1.plot(
        df["tree_depth"],
        df["range_proof_gas"],
        marker="s",
        color="#2ca02c",
        linewidth=2,
        linestyle="--",
        label="8-Leaf Range Proof",
    )
    ax1.set_xlabel("Tree Depth (Log2 Record Count)")
    ax1.set_ylabel("Execution Gas (EVM)")
    ax1.set_title("On-Chain Merkle Proof Verification Gas")
    ax1.legend()

    ax2.errorbar(
        df["tree_depth"],
        df["offchain_verify_mean_us"],
        yerr=df["offchain_verify_std_us"],
        fmt="o-",
        color="#d62728",
        capsize=4,
        linewidth=2,
    )
    ax2.set_xlabel("Tree Depth")
    ax2.set_ylabel("Off-Chain Verification Time (μs)")
    ax2.set_title("Off-Chain Proof Check Latency")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(output_dir, f"figure3_verification_scaling.{ext}"))
    plt.close(fig)
    print("Generated figure3_verification_scaling")


def plot_latency_breakdown(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    csv_path = os.path.join(benchmarks_dir, "throughput_latency.csv")
    if not os.path.exists(csv_path):
        return
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(8.5, 5))

    labels = [f"{n:,} rows" for n in df["record_count"]]
    x = np.arange(len(labels))
    width = 0.55

    s_ser = df["serialization_ms_mean"]
    s_comp = df["compression_ms_mean"]
    s_merkle = df["merkle_ms_mean"]
    s_pack = df["blob_packing_ms_mean"]
    s_dec = df["decode_verify_ms_mean"]

    ax.bar(x, s_ser, width, label="Canonical Serialization")
    ax.bar(x, s_comp, width, bottom=s_ser, label="Zstd Compression")
    ax.bar(x, s_merkle, width, bottom=s_ser + s_comp, label="Merkle Tree Construction")
    ax.bar(
        x,
        s_pack,
        width,
        bottom=s_ser + s_comp + s_merkle,
        label="Blob Chunking & FE Packing",
    )
    ax.bar(
        x,
        s_dec,
        width,
        bottom=s_ser + s_comp + s_merkle + s_pack,
        label="Reconstruction & Verification",
    )

    ax.set_ylabel("Time (Milliseconds)")
    ax.set_title("End-to-End Pipeline Latency Breakdown")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(frameon=True, facecolor="white", framealpha=0.9)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(output_dir, f"figure4_latency_breakdown.{ext}"))
    plt.close(fig)
    print("Generated figure4_latency_breakdown")


def plot_compression_ablation(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    csv_path = os.path.join(benchmarks_dir, "ablation_compression.csv")
    if not os.path.exists(csv_path):
        return
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(8, 4.8))

    ax.plot(
        df["encode_time_ms"],
        df["compression_ratio"],
        marker="o",
        color="#8c564b",
        linewidth=2,
        markersize=8,
    )

    for _, row in df.iterrows():
        lbl = row["configuration"].split(" (")[0]
        ax.annotate(
            lbl,
            (row["encode_time_ms"], row["compression_ratio"]),
            textcoords="offset points",
            xytext=(10, -5 if row["compression_ratio"] > 8 else 5),
            fontsize=9,
            weight="bold",
        )

    ax.set_xlabel("Encoding Latency (ms)")
    ax.set_ylabel("Compression Ratio (x)")
    ax.set_title("Pareto Trade-off: Compression Ratio vs. Encoding Time")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(output_dir, f"figure5_compression_ablation.{ext}"))
    plt.close(fig)
    print("Generated figure5_compression_ablation")


def plot_fee_sensitivity(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    csv_path = os.path.join(benchmarks_dir, "fee_sensitivity.csv")
    if not os.path.exists(csv_path):
        print(f"Skipping plot_fee_sensitivity: {csv_path} not found")
        return
    df = pd.read_csv(csv_path)
    df_1m = df[df["size_mib"] == 1.0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    base_fees = [10.0, 15.0, 25.0, 50.0]
    colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]

    for bf, col in zip(base_fees, colors):
        sub = df_1m[df_1m["base_fee_gwei"] == bf].sort_values("blob_fee_gwei")
        ax1.plot(
            sub["blob_fee_gwei"],
            sub["savings_ratio"],
            marker="o",
            label=f"Base Fee = {int(bf)} gwei",
            color=col,
            linewidth=2,
        )

    ax1.axhline(
        1.0, color="gray", linestyle="--", linewidth=1.5, label="Break-Even (1.0x)"
    )
    ax1.set_xlabel("Blob Base Fee (gwei)")
    ax1.set_ylabel("Blob Savings Ratio vs. Calldata (x)")
    ax1.set_title("Savings Ratio Sensitivity (1.0 MiB Dataset)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.legend(frameon=True, facecolor="white", framealpha=0.9)

    # Subplot 2: Break-even curve
    base_range = np.linspace(5, 100, 50)
    # Ratio for 1.0 MiB is ~13.86
    breakeven_blobs = 13.859 * base_range

    ax2.plot(
        base_range,
        breakeven_blobs,
        color="#005580",
        linewidth=2.5,
        label="Break-Even Boundary",
    )
    ax2.fill_between(
        base_range,
        0,
        breakeven_blobs,
        color="#cce5ff",
        alpha=0.6,
        label="Blob Advantage Region (Blobs Cheaper)",
    )
    ax2.fill_between(
        base_range,
        breakeven_blobs,
        1500,
        color="#ffe6e6",
        alpha=0.4,
        label="Calldata Advantage Region (Extreme Congestion)",
    )

    ax2.set_xlabel("Execution Base Fee (gwei)")
    ax2.set_ylabel("Break-Even Blob Base Fee (gwei)")
    ax2.set_title("Economic Operating Envelope (1.0 MiB Payload)")
    ax2.set_ylim(0, 1400)
    ax2.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(output_dir, f"figure6_fee_sensitivity.{ext}"))
    plt.close(fig)
    print("Generated figure6_fee_sensitivity")


def generate_all_plots(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    plot_cost_comparison(benchmarks_dir, output_dir)
    plot_compression_efficiency(benchmarks_dir, output_dir)
    plot_verification_scaling(benchmarks_dir, output_dir)
    plot_latency_breakdown(benchmarks_dir, output_dir)
    plot_compression_ablation(benchmarks_dir, output_dir)
    plot_fee_sensitivity(benchmarks_dir, output_dir)
    print("All plots generated successfully.")


if __name__ == "__main__":
    generate_all_plots()
