# Journal Dataset Corpus and Provenance

This document specifies the five scientific and benchmark dataset classes evaluated in the `research-blob-da` journal extension. All datasets are preserved under `data/` and `data/journal/` with machine-readable manifests under `data/journal/manifests/`.

---

## 1. Corpus Overview

| Dataset ID | Class / Category | Primary Source | License | Records | Source Bytes | Canonical Bytes | Compression Ratio (zstd-3) |
|---|---|---|---|---|---|---|---|
| `real_scholarly_openalex` | Real Academic Metadata | OpenAlex API | CC0 1.0 Universal | 500 | 264,057 | 212,517 | 4.13x |
| `synthetic_climate_sensor_noaa_format` | Synthetic Environmental Telemetry (NOAA Format) | Local Generator (NOAA ISD Schema) | MIT / Public Domain Equivalent Schema | 5,000 | 1,051,953 | 781,950 | 10.11x |
| `synthetic_ml_training_trace` | Synthetic ML Training Telemetry | Local Generator (PyTorch Schema) | MIT / Apache 2.0 Generator | 5,000 | 531,339 | 541,339 | 5.78x |
| `synthetic_scale_*` | Deterministic Scaling Benchmarks | PRNG Generator (Seed `42`) | MIT | Scaled | Scaled | 100K - 23M | 4.40x - 4.60x |
| `negative_control_1mib` | Negative Control (Incompressible) | High-Entropy PRNG (Seed `42`) | MIT | 1 | 1,048,576 | 1,048,576 | 1.00x (No Gain) |

---

## 2. Detailed Dataset Profiles

### 2.1 Real Scholarly Metadata: OpenAlex Works
- **Identifier**: `real_scholarly_openalex`
- **Source**: OpenAlex API (`https://api.openalex.org/works`)
- **Query Filter**: `publication_year:2023,is_oa:true`, sorted by `cited_by_count:desc`
- **Retrieval Date**: 2026-10-27T16:20:00Z
- **License**: CC0 1.0 Universal (Public Domain)
- **Record Count**: 500 works
- **Source File Size**: 264,057 bytes
- **Source SHA-256**: `af65584227c707d3c16f7841a233070808ab1ed070f10f32e841082889a8c544`
- **Canonical Payload Size**: 212,517 bytes
- **Canonical Payload SHA-256**: `0b7175bfbd6aa0cf048d8c9e5bf1a2c51302531fcce936871bcb84d8b919c12c`
- **Retained Fields**: `id`, `doi`, `title`, `publication_year`, `publication_date`, `cited_by_count`, `type`, `first_author`, `is_oa`, `concepts`.
- **Inclusion Rationale**: Represents real-world academic bibliographic records with nested string structures, author affiliations, and concept taxonomies. Preserves bit-for-bit parity with the frozen v0.1.0 baseline.

### 2.2 Synthetic Environmental Telemetry: Atmospheric Observations (NOAA Format)
- **Identifier**: `synthetic_climate_sensor_noaa_format`
- **Source**: Local synthetic generator (`python/generate_synthetic_data.py`) implementing NOAA Integrated Surface Database (ISD) schema
- **Generation Date**: 2026-10-28T00:00:00Z
- **License**: MIT / Public Domain Equivalent Schema
- **Record Count**: 5,000 observations
- **Source File Size**: 1,051,953 bytes
- **Source SHA-256**: `6f2a156a187b25c083732b6e41425c12c8f169eaeb181fe4442f2dd80473a109`
- **Canonical Payload Size**: 781,950 bytes
- **Canonical Payload SHA-256**: `07e9799b6b4df3a1c7cbbdd843ec2e23d9d4273e718d3e1e53a1267f4bd8dfc8`
- **Retained Fields**: `timestamp`, `station_id`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `wind_speed_ms`, `pm25`.
- **Inclusion Rationale**: Evaluates dense numerical time-series observations from physical environmental sensor networks with high floating-point precision and station groupings. Because these data points were synthesized locally to match NOAA ISD distributions rather than downloaded directly from a NOAA endpoint, this corpus is accurately classified as synthetic data in NOAA format.

### 2.3 Synthetic ML Training Telemetry: Transformer Training Logs (Synthetic PyTorch Format)
- **Identifier**: `synthetic_ml_training_trace`
- **Source**: Local synthetic generator (`python/generate_synthetic_data.py`) implementing PyTorch / WandB training trace schema
- **Generation Date**: 2026-10-28T00:00:00Z
- **License**: MIT / Apache 2.0 Generator
- **Record Count**: 5,000 steps
- **Source File Size**: 531,339 bytes
- **Source SHA-256**: `f64ab5bdf1f111a8a5573e02082e9a8ba91fe96cfe03f3ef7ed6bdb71bf86a56`
- **Canonical Payload Size**: 541,339 bytes
- **Canonical Payload SHA-256**: `78a64a4b77e1050d2def3e3e837f1e134af80c6328f1aa3715d2ca5974bcb45a`
- **Retained Fields**: `step`, `epoch`, `loss`, `accuracy`, `lr`, `grad_norm`, `val_loss`.
- **Inclusion Rationale**: Evaluates machine learning experiment provenance, verifying step-by-step training reproducibility and loss convergence curves. Because these steps were generated locally via procedural simulation rather than exported from an external live cluster run, this corpus is accurately classified as synthetic telemetry in PyTorch schema.

### 2.4 Deterministic Scaling Synthetic Datasets
- **Identifiers**: `synthetic_scale_100k`, `synthetic_scale_1m`, `synthetic_scale_5m`, `synthetic_scale_20m`
- **Generator**: `python/prepare_journal_datasets.py` (Fixed PRNG seed `42`)
- **License**: MIT
- **Schema**: Controlled scientific experiment records (`record_id`, `experiment_id`, `parameter_alpha`, `parameter_beta`, `convergence_metric`, `status`, `tags`).
- **Inclusion Rationale**: Enables strictly controlled size scaling across exact power-of-two boundaries ($100\text{ KiB}$ to $> 20\text{ MiB}$) to measure asymptotic latency and memory behavior without schema drift.

### 2.5 Incompressible Binary Negative Control
- **Identifier**: `negative_control_1mib`
- **Generator**: Deterministic high-entropy pseudo-random bytes (Mersenne Twister PRNG seed `42`)
- **License**: MIT / Public Domain
- **Size**: 1,048,576 bytes ($1.0\text{ MiB}$)
- **Compression Ratio**: $1.00\times$ (Zstandard produces zero reduction).
- **Inclusion Rationale**: Evaluates protocol boundary behavior under worst-case data entropy, demonstrating baseline blob capacity limits when compression yields no benefit.

---

## 3. Provenance and Checksum Manifests

- Master provenance manifest: `data/journal/manifests/dataset_provenance.json`
- Checksum catalog: `data/journal/manifests/checksums.sha256`
- Verification command:
  ```bash
  python -c "import json, hashlib; m = json.load(open('data/journal/manifests/dataset_provenance.json'))['datasets']; [print(d['dataset_id'], 'OK' if hashlib.sha256(open(d['source_file_path'],'rb').read()).hexdigest() == d['source_sha256'] else 'FAIL') for d in m]"
  ```
