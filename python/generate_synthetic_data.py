"""
Synthetic Realistic Academic Research Datasets Generator.

Produces domain-specific, deterministic research datasets with fixed seeds for reproducibility:
1. `ml_training_trace.json`: 10,000 neural network training iterations (step, epoch, loss, accuracy, lr, grad_norm).
2. `climate_sensor_timeseries.csv`: 25,000 hourly environmental sensor readings (timestamp, station, temp, humidity, pressure, pm25).
3. `genomics_variant_benchmark.json`: 8,000 genomic variant records (chrom, pos, ref, alt, qual, depth, allele_freq).
4. `academic_paper_metadata.json`: 5,000 paper metadata records (id, title, categories, year, citations, open_access).
"""

import csv
import json
import math
import os
import random
from typing import Any

DEFAULT_SEED = 0x4844  # 18500


def generate_ml_training_trace(
    num_steps: int = 10000, seed: int = DEFAULT_SEED
) -> list[dict[str, Any]]:
    """Generates synthetic ML training telemetry with realistic loss decay and accuracy progression."""
    rng = random.Random(seed)
    steps_per_epoch = 500
    records: list[dict[str, Any]] = []

    # Model training trajectory
    current_loss = 2.85
    current_acc = 10.5
    base_lr = 3e-4

    for step in range(1, num_steps + 1):
        epoch = (step - 1) // steps_per_epoch + 1
        progress = step / num_steps

        # Cosine learning rate decay
        lr = round(base_lr * 0.5 * (1 + math.cos(math.pi * progress)), 6)

        # Gradual loss decay with stochastic noise
        decay_rate = 0.00035 / (1.0 + 2.0 * progress)
        step_delta = decay_rate + rng.gauss(0, 0.015)
        current_loss = max(0.18, current_loss - step_delta)

        # Accuracy inverse progression
        acc_gain = (0.012 / (1.0 + progress)) + rng.gauss(0, 0.12)
        current_acc = min(96.5, max(10.0, current_acc + acc_gain))

        grad_norm = max(0.05, round(rng.gauss(1.2, 0.35) / (1.0 + 0.5 * progress), 4))
        val_loss = round(current_loss + rng.gauss(0.04, 0.02), 4)

        rec = {
            "step": step,
            "epoch": epoch,
            "loss": round(current_loss, 4),
            "accuracy": round(current_acc, 2),
            "lr": lr,
            "grad_norm": grad_norm,
            "val_loss": val_loss,
        }
        records.append(rec)

    return records


def generate_climate_timeseries(
    num_rows: int = 25000, seed: int = DEFAULT_SEED
) -> list[dict[str, Any]]:
    """Generates synthetic climate sensor station data with realistic diurnal cycles and weather patterns."""
    rng = random.Random(seed)
    stations = [
        "STATION-US-NE01",
        "STATION-EU-WEST04",
        "STATION-AP-EAST02",
        "STATION-SA-SUL01",
    ]
    records: list[dict[str, Any]] = []

    base_time = 1704067200  # 2024-01-01 00:00:00 UTC

    for i in range(num_rows):
        ts = base_time + i * 3600  # hourly
        station = stations[i % len(stations)]
        hour = i % 24
        day = i // 24

        # Diurnal temperature oscillation + seasonal drift
        diurnal = 6.5 * math.sin((hour - 9) * math.pi / 12)
        seasonal = 10.0 * math.sin((day / 365) * 2 * math.pi)
        noise = rng.gauss(0, 1.2)
        temp_c = round(14.0 + diurnal + seasonal + noise, 2)

        # Humidity inversely correlated with temperature
        humidity = round(
            min(100.0, max(20.0, 75.0 - diurnal * 2.2 + rng.gauss(0, 4.0))), 1
        )
        pressure_hpa = round(1013.25 + rng.gauss(0, 8.5) + math.sin(day / 7) * 5.0, 1)
        wind_speed_ms = round(max(0.2, rng.weibullvariate(3.5, 2.0)), 2)
        pm25 = round(max(1.0, rng.expovariate(1 / 15.0)), 1)

        records.append(
            {
                "timestamp": ts,
                "station_id": station,
                "temperature_c": temp_c,
                "humidity_pct": humidity,
                "pressure_hpa": pressure_hpa,
                "wind_speed_ms": wind_speed_ms,
                "pm25": pm25,
            }
        )

    return records


def generate_genomics_benchmark(
    num_records: int = 8000, seed: int = DEFAULT_SEED
) -> list[dict[str, Any]]:
    """Generates synthetic genomic variant evaluation records."""
    rng = random.Random(seed)
    chroms = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]
    bases = ["A", "C", "G", "T"]
    impacts = ["LOW", "MODERATE", "HIGH", "MODIFIER"]
    records: list[dict[str, Any]] = []

    pos_counter = 100000

    for i in range(num_records):
        chrom = chroms[i % len(chroms)]
        pos_counter += rng.randint(200, 15000)
        ref = rng.choice(bases)
        alt = rng.choice([b for b in bases if b != ref])
        qual = round(rng.uniform(30.0, 99.9), 1)
        depth = rng.randint(15, 120)
        af = round(rng.betavariate(2.0, 2.0), 3)
        impact = rng.choice(impacts)

        records.append(
            {
                "chrom": chrom,
                "pos": pos_counter,
                "ref": ref,
                "alt": alt,
                "qual": qual,
                "filter": "PASS" if qual >= 50.0 else "LowQual",
                "dp": depth,
                "af": af,
                "impact": impact,
            }
        )

    return records


def generate_academic_paper_metadata(
    num_papers: int = 5000, seed: int = DEFAULT_SEED
) -> list[dict[str, Any]]:
    """Generates synthetic academic preprint metadata records."""
    rng = random.Random(seed)
    categories_list = [
        ["cs.CR", "cs.DC"],
        ["cs.LG", "stat.ML"],
        ["cs.DS", "math.CO"],
        ["physics.soc-ph", "cs.SI"],
        ["eess.SP", "cs.IT"],
    ]
    adjectives = [
        "Verifiable",
        "Decentralized",
        "Scalable",
        "Robust",
        "Cryptographic",
        "Empirical",
    ]
    nouns = [
        "Data Availability",
        "Consensus Protocol",
        "Neural Compression",
        "Zero-Knowledge Proofs",
        "State Transition",
    ]

    records: list[dict[str, Any]] = []

    for i in range(1, num_papers + 1):
        arxiv_id = f"240{rng.randint(1, 9)}.{rng.randint(1000, 9999):05d}"
        title = f"{rng.choice(adjectives)} {rng.choice(nouns)} for Academic Systems"
        cats = rng.choice(categories_list)
        year = rng.choice([2022, 2023, 2024, 2025, 2026])
        citations = int(rng.paretovariate(1.8) * 3)
        open_access = rng.random() > 0.05

        records.append(
            {
                "paper_id": arxiv_id,
                "title": title,
                "categories": cats,
                "year": year,
                "citations": citations,
                "open_access": open_access,
            }
        )

    return records


def save_synthetic_datasets(data_dir: str = "data") -> dict[str, str]:
    """Generates and writes all synthetic datasets to disk."""
    os.makedirs(data_dir, exist_ok=True)
    paths: dict[str, str] = {}

    # 1. ML training trace JSON
    ml_data = generate_ml_training_trace(10000)
    ml_path = os.path.join(data_dir, "ml_training_trace.json")
    with open(ml_path, "w", encoding="utf-8") as f:
        json.dump(ml_data, f, indent=2)
    paths["ml_trace"] = ml_path

    # 2. Climate sensor timeseries CSV
    climate_data = generate_climate_timeseries(25000)
    climate_path = os.path.join(data_dir, "climate_sensor_timeseries.csv")
    with open(climate_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(climate_data[0].keys()))
        writer.writeheader()
        writer.writerows(climate_data)
    paths["climate_csv"] = climate_path

    # 3. Genomics variant benchmark JSON
    genomics_data = generate_genomics_benchmark(8000)
    genomics_path = os.path.join(data_dir, "genomics_variant_benchmark.json")
    with open(genomics_path, "w", encoding="utf-8") as f:
        json.dump(genomics_data, f, indent=2)
    paths["genomics_json"] = genomics_path

    # 4. Academic paper metadata JSON
    papers_data = generate_academic_paper_metadata(5000)
    papers_path = os.path.join(data_dir, "academic_paper_metadata.json")
    with open(papers_path, "w", encoding="utf-8") as f:
        json.dump(papers_data, f, indent=2)
    paths["papers_json"] = papers_path

    print(f"Generated 4 synthetic research datasets in '{data_dir}':")
    for k, p in paths.items():
        sz_kb = os.path.getsize(p) / 1024
        print(f"  - {k}: {p} ({sz_kb:.1f} KiB)")

    return paths


if __name__ == "__main__":
    save_synthetic_datasets()
