# Release Asset Integrity Audit (v0.1.0)

This audit documents the byte-for-byte verification of all release assets attached to the protected `v0.1.0` release tag (`428c7898dd5e5078ad466fa6955058936b33aac3`), comparing tagged repository files, downloaded GitHub release attachments, GitHub-reported digests, and the frozen benchmark manifest `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json`.

---

## 1. Audit Methodology

1. **Clean-Checkout Verification**:
   Cloned repository at tag `v0.1.0` into a pristine temporary clone (`git clone --branch v0.1.0 --depth 1 https://github.com/samudragupto/research-blob-da.git`).
2. **Release Asset Download**:
   Downloaded all 7 published assets from GitHub release `v0.1.0` via GitHub CLI (`gh release download v0.1.0 --repo samudragupto/research-blob-da`).
3. **Digest Comparison**:
   Computed SHA-256 hashes of the tagged clone files and downloaded release assets, and compared them directly against the GitHub API asset digests (`gh release view v0.1.0 --json assets`) and `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json`.

---

## 2. Release Asset Verification Matrix

| Asset Name | Tagged File SHA-256 | Downloaded File SHA-256 | GitHub API Reported Digest | Freeze Manifest Match | Status |
|---|---|---|---|---|---|
| `blob_capacity_limits.csv` | `c766f6f38713ea66e052ae1e91e2d9569f3dcb7974fdedbe1e4cd0e95024b52a` | `c766f6f38713ea66e052ae1e91e2d9569f3dcb7974fdedbe1e4cd0e95024b52a` | `sha256:c766f6f38713ea66e052ae1e91e2d9569f3dcb7974fdedbe1e4cd0e95024b52a` | MATCH | PASS |
| `calldata_eip7623_sensitivity.csv` | `03f86bcbbe3b43b2e3804267ec2cef85eae89d99062b4426397270642fe445ee` | `03f86bcbbe3b43b2e3804267ec2cef85eae89d99062b4426397270642fe445ee` | `sha256:03f86bcbbe3b43b2e3804267ec2cef85eae89d99062b4426397270642fe445ee` | MATCH | PASS |
| `cost_comparison_compressed.csv` | `c7f3c36590ef2984a4c28fdba70d2341070d733a63633fdd7c48168c2fbd4171` | `c7f3c36590ef2984a4c28fdba70d2341070d733a63633fdd7c48168c2fbd4171` | `sha256:c7f3c36590ef2984a4c28fdba70d2341070d733a63633fdd7c48168c2fbd4171` | MATCH | PASS |
| `cost_comparison_uncompressed.csv` | `833ce76fb0df34b40f3c72f9f1f6fd19589e691ec3ebed8f3fa7e16c1b318224` | `833ce76fb0df34b40f3c72f9f1f6fd19589e691ec3ebed8f3fa7e16c1b318224` | `sha256:833ce76fb0df34b40f3c72f9f1f6fd19589e691ec3ebed8f3fa7e16c1b318224` | MATCH | PASS |
| `encoding_efficiency.csv` | `a71a6464a06c70f875f23ce3910d68c2f533f19df481422bf8087c45d6db061b` | `a71a6464a06c70f875f23ce3910d68c2f533f19df481422bf8087c45d6db061b` | `sha256:a71a6464a06c70f875f23ce3910d68c2f533f19df481422bf8087c45d6db061b` | MATCH | PASS |
| `fee_sensitivity.csv` | `61c9379a2dd4325f67dd2db05c6c3ee6e64fa2eacb64935435a2d5f829387ff4` | `61c9379a2dd4325f67dd2db05c6c3ee6e64fa2eacb64935435a2d5f829387ff4` | `sha256:61c9379a2dd4325f67dd2db05c6c3ee6e64fa2eacb64935435a2d5f829387ff4` | MATCH | PASS |
| `FROZEN_BENCHMARKS_v0.1.0.json` | `fb06aa73b4456fcef96486aff057186ff444aa757c95815dff3ea2c628a35747` | `fb06aa73b4456fcef96486aff057186ff444aa757c95815dff3ea2c628a35747` | `sha256:fb06aa73b4456fcef96486aff057186ff444aa757c95815dff3ea2c628a35747` | Self-Manifest | PASS |

---

## 3. Frozen Benchmark Integrity Verification

Every file registered in `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json` inside the tagged clone matches its recorded SHA-256 digest:

1. `benchmarks/cost_comparison_uncompressed.csv`: `833ce76fb0df34b40f3c72f9f1f6fd19589e691ec3ebed8f3fa7e16c1b318224` (PASS)
2. `benchmarks/cost_comparison_compressed.csv`: `c7f3c36590ef2984a4c28fdba70d2341070d733a63633fdd7c48168c2fbd4171` (PASS)
3. `benchmarks/encoding_efficiency.csv`: `a71a6464a06c70f875f23ce3910d68c2f533f19df481422bf8087c45d6db061b` (PASS)
4. `benchmarks/fee_sensitivity.csv`: `61c9379a2dd4325f67dd2db05c6c3ee6e64fa2eacb64935435a2d5f829387ff4` (PASS)
5. `benchmarks/calldata_eip7623_sensitivity.csv`: `03f86bcbbe3b43b2e3804267ec2cef85eae89d99062b4426397270642fe445ee` (PASS)
6. `benchmarks/blob_capacity_limits.csv`: `c766f6f38713ea66e052ae1e91e2d9569f3dcb7974fdedbe1e4cd0e95024b52a` (PASS)
7. `benchmarks/generated_tables.md`: `0d06f83ae5c788d60318f60d0f18da24d4f68cc9b672c0f8dfc1eee65836f233` (PASS)

---

## 4. Audit Conclusion

The v0.1.0 release assets exhibit complete byte-for-byte fidelity across tagged repository files, downloaded release assets, GitHub API release digests, and the freeze manifest. Zero discrepancies or hash mismatches exist. No assets required replacement, and the `v0.1.0` tag remains completely untouched.
