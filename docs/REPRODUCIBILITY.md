# Reproducibility Guide: research-blob-da

This guide provides end-to-end instructions for reproducing all empirical experiments, benchmark tables, publication figures, smart contract verifications, and CLI demonstrations from source.

---

## 1. Prerequisites and Installation

### 1.1 Software Dependencies
- **Git** (version 2.40+)
- **Python** (version 3.11, 3.12, or 3.13)
- **Foundry** (`forge` and `cast` version 1.0.0+)
- **Node.js** (version 20+; optional, for TypeScript helper)

### 1.2 Foundry Toolchain Setup
If Foundry is not installed:
```bash
# Linux/macOS
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Windows (PowerShell)
powershell -c "irm https://foundry.paradigm.xyz | iex"
foundryup
```

Verify Foundry installation:
```bash
forge --version
```

### 1.3 Python Environment Setup
Clone the repository and initialize a virtual environment:
```bash
git clone https://github.com/samudragupto/research-blob-da.git
cd research-blob-da

# Create and activate virtual environment
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Smart Contract Compilation and Formal Testing

Verify that all smart contracts compile under the `cancun` EVM target and pass all unit tests, fuzz tests, and state invariant checks:

```bash
# Compile contracts with via-IR enabled
forge build

# Run complete test suite (unit tests, fuzzing, invariants)
forge test -v
```

Expected output:
```text
Ran 5 test suites: 31 tests passed, 0 failed, 0 skipped (31 total tests)
- DatasetRegistryTest: 9 passed
- BaselinesTest: 4 passed
- JsonFieldLibTest: 11 passed
- MerkleLibTest: 6 passed
- InvariantTest: 1 passed (16,384 calls across 256 runs, 0 reverts)
```

Run gas benchmarking script:
```bash
forge script script/BaselineBench.s.sol
```

---

## 3. Dataset Generation and Empirical Benchmarks

### 3.1 Generate Deterministic Academic Datasets
Generate the 4 synthetic academic datasets in `data/`:
```bash
python python/generate_synthetic_data.py
```
This generates:
- `data/ml_training_trace.json` (10,000 step records, ~1.05 MiB)
- `data/climate_sensor_timeseries.csv` (20,000 rows, ~3.05 MiB)
- `data/genomics_variant_benchmark.json` (8,000 variant calls, ~946 KiB)
- `data/academic_paper_metadata.json` (5,000 bibliographic items, ~825 KiB)

### 3.2 Execute Benchmark Experiment Suite
Run the 5 empirical experiment pipelines:
```bash
python python/experiments.py
```
This performs 10 repetitions per condition with warm-up cycles and writes structured CSVs to `benchmarks/`:
- `benchmarks/cost_comparison.csv`
- `benchmarks/encoding_efficiency.csv`
- `benchmarks/verification_benchmarks.csv`
- `benchmarks/throughput_latency.csv`
- `benchmarks/ablation_compression.csv`
- `benchmarks/ablation_packing.csv`

### 3.3 Benchmark Freeze (v0.1.0)
The benchmark generation accompanying the v0.1.0 release is frozen in `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json`.
To verify that your benchmark CSV files match the frozen release generation:
```bash
# On Linux / macOS
sha256sum -c <(jq -r '.benchmark_files | to_entries[] | "\(.value)  \(.key)"' benchmarks/FROZEN_BENCHMARKS_v0.1.0.json)

# On Windows PowerShell
Get-FileHash benchmarks/*.csv, benchmarks/generated_tables.md -Algorithm SHA256
```
*Note on Execution Hardware:* Re-running `experiments.py` on different hardware or operating systems will naturally produce hardware-dependent timing latencies (mean and standard deviation), while dataset sizes, compression ratios, blob counts, and monetary cost models remain strictly invariant and deterministic.

### 3.3 Generate Publication Plots
Generate high-resolution vector (PDF) and raster (PNG) publication figures:
```bash
python python/plot_results.py
```
Outputs generated in `benchmarks/` and `docs/figures/`:
- `figure1_cost_comparison.{png,pdf}`
- `figure2_compression_efficiency.{png,pdf}`
- `figure3_verification_scaling.{png,pdf}`
- `figure4_latency_breakdown.{png,pdf}`
- `figure5_compression_ablation.{png,pdf}`

---

## 4. Python Unit and Integration Tests

Run the full pytest suite:
```bash
pytest -v tests
```
Expected output:
```text
tests/test_canonical.py ........
tests/test_commitments.py .....
tests/test_encoder_decoder.py .........
tests/test_retriever.py .......
============================= 26 passed in 0.3s =============================
```

---

## 5. Command-Line Interface (CLI) Demonstration

The CLI (`frontend-or-cli/rbda_cli.py`) demonstrates complete dataset lifecycle workflows:

### 5.1 Encode and Cache Dataset
```bash
python frontend-or-cli/rbda_cli.py encode \
  --input data/ml_training_trace.json \
  --out-dir data/encoded_demo \
  --codec zstd \
  --packing fe31 \
  --zstd-level 3 \
  --cache
```

### 5.2 Verify Blob Sidecars against Manifest
```bash
python frontend-or-cli/rbda_cli.py verify \
  --manifest data/encoded_demo/manifest.json \
  --blobs-dir data/encoded_demo
```

### 5.3 Retrieve and Reconstruct Dataset
```bash
python frontend-or-cli/rbda_cli.py retrieve \
  --manifest data/encoded_demo/manifest.json \
  --out-file data/reconstructed.json \
  --source local
```

### 5.4 Submit Property Claim
```bash
python frontend-or-cli/rbda_cli.py claim \
  --input data/ml_training_trace.json \
  --key loss \
  --scale 2
```

### 5.5 Refute Fraudulent Claim
Simulate refuting a false claim asserting that loss never exceeded 2.0 (scaled: 200):
```bash
python frontend-or-cli/rbda_cli.py refute \
  --input data/ml_training_trace.json \
  --key loss \
  --scale 2 \
  --claimed-min 18 \
  --claimed-max 200
```
This generates the exact record index, record calldata, and Merkle sibling proofs for the on-chain call `refutePropertyClaim`.

---

## 6. Testnet Deployment (Sepolia)

To deploy the contracts to Ethereum Sepolia:

```bash
export SEPOLIA_RPC_URL="https://ethereum-sepolia.publicnode.com"
export PRIVATE_KEY="0x..."
export ETHERSCAN_API_KEY="..."

forge script script/Deploy.s.sol:DeployScript \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  --verify
```

To broadcast a Type-3 blob transaction posting a research dataset:
```bash
# Using Foundry script:
forge script script/PostBlobDataset.s.sol:PostBlobDatasetScript \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast

# Or using TypeScript viem SDK:
cd frontend-or-cli/ts
npm install
npm run build
REGISTRY_ADDRESS="0x..." PRIVATE_KEY="0x..." npx ts-node src/blob_tx.ts ../../data/encoded_demo/manifest.json ../../data/encoded_demo
```
