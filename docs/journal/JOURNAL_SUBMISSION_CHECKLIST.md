# Journal Submission Checklist

This checklist tracks submission readiness across manuscript quality, empirical integrity, claims discipline, and artifact availability.

---

## 1. Title and Abstract Alignment

- [x] **Working Title**: *Beyond Rollups: Evaluating EIP-4844 Blobs as Temporary Verifiable Data Availability for Research Artifacts*.
- [x] **Clear Problem Framing**: Clearly contrasts transient consensus data availability against durable archival persistence.
- [x] **Defensible Core Claim**: ``Ethereum blobs can provide an economical, consensus-committed, temporary publication window for research artifacts, while durable preservation requires a separate archival and retrieval layer.''

---

## 2. Integrity and Claims Discipline

- [x] **No Storage Conflation**: Blobs are never claimed to be permanent archives ($\approx 18.2$-day pruning window is explicitly stated).
- [x] **No Retrieval Conflation**: Local-cache reconstruction is strictly distinguished from public network retrieval.
- [x] **No Cryptographic Overclaiming**: KZG polynomial commitments are identified as proving *commitment consistency*, not *perpetual availability*.
- [x] **No Formal Verification Claims**: Contracts are described as extensively tested (unit, fuzz, invariant campaigns), not ``formally verified''.
- [x] **No Universal Cost Superiors**: Blobs are acknowledged to have economic limits depending on blob base fees, execution fees, payload sizes, and quantization overhead (break-even blob fee of $207.9$~gwei documented).
- [x] **No Hyperbole on Reproducibility**: The paper acknowledges that artifact availability addresses bitwise integrity and publication economics, not the entire reproducibility crisis.

---

## 3. Empirical Evidence and Transparency

- [x] **Evidence Types Explicitly Labeled**:
  - `[Measured locally]` on micro-benchmarks.
  - `[Measured on Sepolia]` on live testnet deployment.
  - `[Empirical retrieval attempts]` on multi-tier retrieval study.
  - `[Analytical model]` on parameter fee sweeps.
- [x] **Pending Network Experiments**: The 30-submission network matrix is documented in `benchmarks/journal-extension/network/pending_experiments.json` with authorization safeguards; no results are fabricated.
- [x] **Raw Trial-Level Data**: Complete trial rows preserved under `benchmarks/journal-extension/`.

---

## 4. Figures and Tables

- [x] **Automated Pipeline**: All LaTeX tables and figures generated via `python/generate_paper_artifacts.py`.
- [x] **Accessible Design**: Legible sans-serif typography, high contrast colors, error bars, and dual-format output (PNG at 300 DPI and vector PDF).
- [x] **No Misleading Axes**: Bar charts with logarithmic scales are clearly marked; linear axes are zero-based.

---

## 5. Peer-Reviewed Literature Standards

- [x] **Verified References**: All 14 BibTeX entries in `paper/references.bib` verified with primary author names, publication venues, years, and stable URLs/DOIs.
- [x] **No Hallucinated Citations**: Every citation matches an authoritative published source or IETF standard.
