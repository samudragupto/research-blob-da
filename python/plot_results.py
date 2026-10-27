"""
Plotting Script for research-blob-da Academic Evaluation.

Generates publication-quality figures (both high-res PNG and PDF) using Matplotlib & Seaborn:
- `figure1_cost_comparison.png` / `.pdf`: Log-scale monetary cost comparison across storage primitives.
- `figure2_compression_efficiency.png` / `.pdf`: Compression ratios and packing efficiency by dataset type.
- `figure3_verification_scaling.png` / `.pdf`: Single-leaf vs range proof verification gas and off-chain latency.
- `figure4_latency_breakdown.png` / `.pdf`: Stacked latency breakdown as dataset record count scales.
- `figure5_compression_ablation.png` / `.pdf`: Compression ratio vs encoding latency Pareto frontier.
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
    csv_path = os.path.join(benchmarks_dir, "cost_comparison.csv")
    if not os.path.exists(csv_path):
        print(f"Skipping plot_cost_comparison: {csv_path} not found")
        return
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(len(df))
    width = 0.16

    ax.bar(
        x - 2 * width,
        df["cost_blob_usd"],
        width,
        label="EIP-4844 Blobs",
        color="#1f77b4",
    )
    ax.bar(
        x - width,
        df["cost_calldata_usd"],
        width,
        label="Calldata (Standard)",
        color="#ff7f0e",
    )
    ax.bar(
        x,
        df["cost_calldata_7623_usd"],
        width,
        label="Calldata (EIP-7623 Floor)",
        color="#d62728",
    )
    ax.bar(
        x + width,
        df["cost_sstore_usd"],
        width,
        label="SSTORE Permanent",
        color="#9467bd",
    )
    ax.bar(
        x + 2 * width,
        df["cost_ipfs_1yr_usd"],
        width,
        label="IPFS + On-chain CID (1 yr)",
        color="#2ca02c",
    )

    ax.set_ylabel("Publication Cost (USD, Log Scale)")
    ax.set_title("Publication Cost Comparison Across Storage Primitives")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{mib:.2f} MiB" if mib < 1 else f"{int(mib)} MiB" for mib in df["size_mib"]]
    )
    ax.set_yscale("log")
    ax.legend(frameon=True, facecolor="white", framealpha=0.9)

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

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    short_names = [n.split(" (")[0] for n in df["dataset_type"]]
    colors = ["#2b5c8f", "#388e3c", "#d32f2f", "#7b1fa2"]

    # 1. Compression ratio
    bars1 = ax1.bar(short_names, df["compression_ratio"], color=colors, width=0.55)
    ax1.set_ylabel("Compression Ratio (Raw Size / Compressed Size)")
    ax1.set_title("Zstandard Compression Ratio by Data Type")
    ax1.set_xticklabels(short_names, rotation=15, ha="right")
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
    bars2 = ax2.bar(short_names, df["packing_efficiency_pct"], color=colors, width=0.55)
    ax2.set_ylabel("Blob Space Utilization (%)")
    ax2.set_title("Blob Payload Packing Efficiency (FE31)")
    ax2.set_xticklabels(short_names, rotation=15, ha="right")
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

    # 1. On-chain gas scaling
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

    # 2. Off-chain latency with error bars
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


def generate_all_plots(
    benchmarks_dir: str = "benchmarks", output_dir: str = "benchmarks"
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    plot_cost_comparison(benchmarks_dir, output_dir)
    plot_compression_efficiency(benchmarks_dir, output_dir)
    plot_verification_scaling(benchmarks_dir, output_dir)
    plot_latency_breakdown(benchmarks_dir, output_dir)
    plot_compression_ablation(benchmarks_dir, output_dir)
    print("All plots generated successfully.")


if __name__ == "__main__":
    generate_all_plots()
