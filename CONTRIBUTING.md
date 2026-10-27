# Contributing to research-blob-da

Thank you for your interest in contributing to **research-blob-da**. We welcome contributions from protocol researchers, cryptographers, data engineers, and decentralized systems developers.

---

## 1. Code of Conduct and Scientific Integrity

We adhere to the highest standards of scientific reproducibility, open-source peer review, and academic integrity. All benchmark claims, gas evaluations, and cryptographic proofs must be accompanied by automated reproduction tests.

---

## 2. Development Setup

### Prerequisites
- Python 3.11+
- Foundry (`forge`, `cast`)
- Git

### Initializing the Workspace
```bash
git clone https://github.com/ethereum-research/research-blob-da.git
cd research-blob-da

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Install and build Foundry contracts
forge build
```

---

## 3. Style Guidelines and Formatting

All codebase files must pass automated linters without warnings or errors.

### Solidity (`contracts/`, `test/`, `script/`)
- Formatting: Follow standard Foundry formatting:
  ```bash
  forge fmt --check
  ```
- Compiler Profile: Must compile cleanly under EVM target `cancun` with `via_ir = true`.
- NatSpec: All public and external functions, events, custom errors, and state variables must feature complete NatSpec documentation (`@notice`, `@dev`, `@param`, `@return`).

### Python (`python/`, `tests/`, `frontend-or-cli/`)
- Formatting: Format using `black`:
  ```bash
  black --check python tests frontend-or-cli
  ```
- Linting: Lint using `ruff`:
  ```bash
  ruff check python tests frontend-or-cli
  ```
- Type Hints: All module functions must include complete PEP 484 type annotations.

### Tone and Documentation
- Zero Emojis: In accordance with academic publishing standards, emojis are strictly prohibited across all code, tests, scripts, commits, documentation, and pull requests.

---

## 4. Testing Requirements

Every pull request must include tests demonstrating correctness:

1. **Unit & Invariant Tests:**
   ```bash
   forge test -v
   pytest -v tests
   ```
2. **Empirical Benchmarks:**
   If modifying encoding algorithms, compression codecs, or Merkle construction:
   ```bash
   python python/experiments.py
   python python/plot_results.py
   ```
   Verify that all output CSVs and publication figures in `benchmarks/` and `docs/figures/` are updated accordingly.

---

## 5. Pull Request Workflow

1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Implement your changes adhering to all style and testing guidelines.
3. Commit with concise, descriptive commit messages.
4. Push to your branch and open a Pull Request against `main`.
5. Ensure all GitHub Actions CI checks (`ci.yml`) pass.
