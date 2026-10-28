"""
generate_paper_artifacts.py: Generates LaTeX Tables and Figures from Raw Benchmarks.

Outputs:
- paper/tables/*.tex
- paper/figures/*.png & *.pdf
"""

import json
import os
import shutil

import matplotlib.pyplot as plt
import pandas as pd

TABLES_DIR = "paper/tables"
FIGURES_DIR = "paper/figures"


def escape_latex(s: str) -> str:
    return (
        str(s)
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
        .replace("~", "$\\sim$")
        .replace(">=", "$\\ge$")
        .replace("<=", "$\\le$")
        .replace("!=", "$\\neq$")
    )


def generate_tables():
    os.makedirs(TABLES_DIR, exist_ok=True)

    # 1. Table: Local Scaling Matrix
    df_local = pd.read_csv(
        "benchmarks/journal-extension/local/summary_local_matrix.csv"
    )
    with open(
        os.path.join(TABLES_DIR, "table_local_matrix.tex"), "w", encoding="utf-8"
    ) as f:
        f.write("% Auto-generated from summary_local_matrix.csv\n")
        f.write("\\begin{table*}[t]\n\\centering\n\\small\n")
        f.write(
            "\\caption{Local Evaluation Matrix Across Scientific and Synthetic Datasets [Measured locally]}\n"
        )
        f.write("\\label{tab:local_matrix}\n")
        f.write(
            "\\begin{tabular}{lrrrrrrr}\n\\hline\n"
            "Dataset & Canonical Size & Comp. Size & Ratio & Blobs & Waste & Encoding Latency & Throughput \\\\\n"
            "& (KiB) & (KiB) & & Count & (\\%) & Mean $\\pm$ SD (ms) & (MiB/s) \\\\\n\\hline\n"
        )
        for _, row in df_local.iterrows():
            d_name = escape_latex(row["dataset_name"])
            can_kib = row["canonical_bytes"] / 1024.0
            comp_kib = row["compressed_bytes"] / 1024.0
            ratio = row["compression_ratio"]
            blobs = row["blobs_needed"]
            waste = row["packing_waste_pct"]
            lat_str = (
                f"{row['encoding_mean_ms']:.2f} $\\pm$ {row['encoding_std_ms']:.2f}"
            )
            tp = row["throughput_mib_s"]
            f.write(
                f"{d_name} & {can_kib:.1f} & {comp_kib:.1f} & {ratio:.2f}$\\times$ & {blobs} & {waste:.1f}\\% & {lat_str} & {tp:.1f} \\\\\n"
            )
        f.write("\\hline\n\\end{tabular}\n\\end{table*}\n")

    # 2. Table: Retrieval Evaluation
    df_ret = pd.read_csv("benchmarks/journal-extension/retrieval/summary.csv")
    with open(
        os.path.join(TABLES_DIR, "table_retrieval.tex"), "w", encoding="utf-8"
    ) as f:
        f.write("% Auto-generated from retrieval/summary.csv\n")
        f.write("\\begin{table*}[t]\n\\centering\n\\small\n")
        f.write(
            "\\caption{Sidecar Retrieval Outcomes Across Infrastructure Tiers [Public endpoint probes and local verification]}\n"
        )
        f.write("\\label{tab:retrieval_summary}\n")
        f.write(
            "\\begin{tabular}{llrrrl}\n\\hline\n"
            "Endpoint Identifier & Source Type & Attempts & Success Rate & Median Latency (ms) & Observed Errors \\\\\n\\hline\n"
        )
        # Section A: Public Endpoint Probes
        f.write(
            "\\multicolumn{6}{l}{\\textbf{A. Public Endpoint Probes [Public endpoint probe]}} \\\\\n\\hline\n"
        )
        for _, row in df_ret[
            df_ret["source_type"].isin(["beacon_api", "beacon_indexer"])
        ].iterrows():
            ep = escape_latex(row["endpoint_id"])
            st = escape_latex(row["source_type"])
            att = int(row["attempt_count"])
            succ = int(row["success_count"])
            sr = f"{succ}/{att} ({row['success_rate_pct']:.1f}\\%)"
            lat = f"{row['median_latency_ms']:.1f}"
            err = escape_latex(row["observed_error_categories"])
            f.write(f"{ep} & {st} & {att} & {sr} & {lat} & {err} \\\\\n")
        f.write("\\hline\n")
        # Section B: Local Verification
        f.write(
            "\\multicolumn{6}{l}{\\textbf{B. Local Verification [Simulated / Local prototype measurement]}} \\\\\n\\hline\n"
        )
        for _, row in df_ret[
            df_ret["source_type"].isin(["simulated_archival_cache", "local_cache"])
        ].iterrows():
            ep = escape_latex(row["endpoint_id"])
            st = escape_latex(row["source_type"])
            att = int(row["attempt_count"])
            succ = int(row["success_count"])
            sr = f"{succ}/{att} ({row['success_rate_pct']:.1f}\\%)"
            lat = f"{row['median_latency_ms']:.1f}"
            err = escape_latex(row["observed_error_categories"])
            f.write(f"{ep} & {st} & {att} & {sr} & {lat} & {err} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n\\end{table*}\n")

    # 3. Table: Guarantee-Aware Baselines
    df_base = pd.read_csv("benchmarks/journal-extension/baseline_comparison.csv")
    with open(
        os.path.join(TABLES_DIR, "table_baselines.tex"), "w", encoding="utf-8"
    ) as f:
        f.write("% Auto-generated from baseline_comparison.csv\n")
        f.write("\\begin{table*}[t]\n\\centering\n\\scriptsize\n")
        f.write(
            "\\caption{Guarantee-Aware Storage Architecture Comparison [Estimated from documented pricing and Analytically derived]}\n"
        )
        f.write("\\label{tab:guarantee_baselines}\n")
        f.write(
            "\\begin{tabular}{p{2.6cm} p{2.2cm} p{3.2cm} p{3.6cm} r p{2.0cm}}\n\\hline\n"
            "System & Availability Period & Consensus Verification & Permanence Model & Cost / MiB & Evidence Type \\\\\n\\hline\n"
        )
        for _, row in df_base.iterrows():
            sys_name = escape_latex(row["system_name"])
            avail = escape_latex(row["availability_period"])
            cv = escape_latex(row["consensus_verification"])
            perm = escape_latex(row["permanence_model"])
            cost = row["cost_model_usd_per_mib"]
            c_str = f"\\${cost:.4f}" if cost < 1 else f"\\${cost:,.2f}"
            ev_type = escape_latex(row["evidence_type"].replace("_", " "))
            f.write(
                f"{sys_name} & {avail} & {cv} & {perm} & {c_str} & {ev_type} \\\\\n"
            )
        f.write("\\hline\n\\end{tabular}\n\\end{table*}\n")

    # 4. Table: Adversarial Security Results
    with open(
        "benchmarks/journal-extension/security/results.json",
        "r",
        encoding="utf-8",
    ) as f:
        sec_data = json.load(f)["scenarios"]

    with open(
        os.path.join(TABLES_DIR, "table_security.tex"), "w", encoding="utf-8"
    ) as f:
        f.write("% Auto-generated from security/results.json\n")
        f.write("\\begin{table*}[t]\n\\centering\n\\scriptsize\n")
        f.write(
            "\\caption{Adversarial Threat Scenarios and Detection Invariants [Tested security suite / Measured locally]}\n"
        )
        f.write("\\label{tab:security_matrix}\n")
        f.write(
            "\\begin{tabular}{p{1.4cm} p{4.2cm} p{8.2cm} p{1.6cm}}\n\\hline\n"
            "ID & Threat Scenario & Detection Mechanism & Outcome \\\\\n\\hline\n"
        )
        for sc in sec_data:
            s_id = escape_latex(sc["id"])
            s_name = escape_latex(sc["name"])
            mech = escape_latex(sc["detection_mechanism"])
            out = escape_latex(sc["test_status"].replace("_", " "))
            f.write(f"{s_id} & {s_name} & {mech} & {out} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n\\end{table*}\n")

    print("[OK] LaTeX tables generated in paper/tables/")


def generate_figures():
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # Copy guarantee cost matrix from benchmarks
    shutil.copy(
        "benchmarks/journal-extension/figures/guarantee_cost_matrix.png",
        os.path.join(FIGURES_DIR, "fig_guarantee_cost.png"),
    )
    shutil.copy(
        "benchmarks/journal-extension/figures/guarantee_cost_matrix.pdf",
        os.path.join(FIGURES_DIR, "fig_guarantee_cost.pdf"),
    )

    # 1. Throughput scaling figure
    df_local = pd.read_csv(
        "benchmarks/journal-extension/local/summary_local_matrix.csv"
    )
    plt.figure(figsize=(7, 4), dpi=300)
    sizes_mib = df_local["canonical_bytes"] / (1024 * 1024)
    throughputs = df_local["throughput_mib_s"]
    plt.plot(
        sizes_mib,
        throughputs,
        marker="o",
        linewidth=2,
        color="#0275d8",
        label="Encoding Throughput",
    )
    plt.xscale("log")
    plt.xlabel("Canonical Payload Size (MiB, Log Scale)")
    plt.ylabel("Throughput (MiB/s)")
    plt.title("Client Preparation Throughput Scaling [Measured locally]")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig_throughput_scaling.png"), dpi=300)
    plt.savefig(os.path.join(FIGURES_DIR, "fig_throughput_scaling.pdf"))
    plt.close()

    # 2. Compression ablation figure
    df_comp = pd.read_csv("benchmarks/journal-extension/local/ablation_compression.csv")
    plt.figure(figsize=(7, 4), dpi=300)
    levels = df_comp["zstd_level"]
    ratios = df_comp["compression_ratio"]
    latencies = df_comp["latency_mean_ms"]

    fig, ax1 = plt.subplots(figsize=(7, 4), dpi=300)
    ax1.set_xlabel("Zstandard Compression Level")
    ax1.set_ylabel("Compression Ratio", color="#0275d8")
    ax1.plot(
        levels,
        ratios,
        marker="s",
        color="#0275d8",
        linewidth=2,
        label="Compression Ratio",
    )
    ax1.tick_params(axis="y", labelcolor="#0275d8")

    ax2 = ax1.twinx()
    ax2.set_ylabel("Compression Latency (ms)", color="#d9534f")
    ax2.plot(
        levels,
        latencies,
        marker="^",
        color="#d9534f",
        linewidth=2,
        linestyle="--",
        label="Latency (ms)",
    )
    ax2.tick_params(axis="y", labelcolor="#d9534f")

    plt.title("Zstandard Compression Level Trade-off [Measured locally]")
    fig.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig_compression_ablation.png"), dpi=300)
    plt.savefig(os.path.join(FIGURES_DIR, "fig_compression_ablation.pdf"))
    plt.close()

    # 3. Dual-Horizon Lifecycle Diagram / Archival Latency
    with open(
        "benchmarks/journal-extension/archival/results.json",
        "r",
        encoding="utf-8",
    ) as f:
        arch_data = json.load(f)

    stages = [
        "Canonicalization",
        "Blob Encoding",
        "Archival Upload",
        "Archival Retrieval",
        "Commitment Verification",
    ]
    times = [
        arch_data["publication"]["timings_ms"]["canonicalization"],
        arch_data["publication"]["timings_ms"]["blob_encoding"],
        arch_data["publication"]["timings_ms"]["archival_upload"],
        arch_data["post_expiry_reconstruction"]["retrieval_latency_ms"],
        arch_data["post_expiry_reconstruction"]["verification_latency_ms"],
    ]

    plt.figure(figsize=(8, 4), dpi=300)
    plt.barh(stages, times, color="#5cb85c")
    plt.xlabel("Latency (ms)")
    plt.title("Dual-Horizon Archival Bridge Latency Breakdown [Measured locally]")
    plt.grid(axis="x", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig_archival_latencies.png"), dpi=300)
    plt.savefig(os.path.join(FIGURES_DIR, "fig_archival_latencies.pdf"))
    plt.close()

    print("[OK] Paper figures generated in paper/figures/")


if __name__ == "__main__":
    generate_tables()
    generate_figures()
