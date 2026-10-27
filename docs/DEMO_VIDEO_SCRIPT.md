# Two-Minute Demonstration Video Script: research-blob-da

**Project:** `research-blob-da` (v0.1.0)  
**Author:** Arrhat Nag (GitHub: samudragupto)  
**Target Duration:** 2 minutes (120 seconds)  
**Prerequisites:** Terminal open in repository root with `.venv` active.

---

### Segment 1: Introduction and Canonical Blob Encoding (0:00 - 0:25)

**Visual:** Terminal in `research-blob-da` root.  
**Spoken Narration:**
> "Hello. I am Arrhat Nag. Today I am demonstrating research-blob-da, an open-source prototype using Ethereum EIP-4844 blobs as a cheap, verifiable data-availability primitive for scientific datasets and ML training telemetry. Let us encode 500 real academic metadata records harvested from the OpenAlex API into canonical blob sidecars."

**Terminal Command:**
```bash
python frontend-or-cli/rbda_cli.py encode \
  --input data/real_academic_openalex.json \
  --out-dir data/encoded_demo \
  --cache
```

**Expected Output:**
```text
[INFO] Loaded 500 records from data/real_academic_openalex.json
[INFO] Encoding with codec=zstd, packing=fe31, zstd_level=3...
[INFO] Cached 1 blobs in local sidecar cache.
[SUCCESS] Encoding complete.
  Blobs produced:      1
  Raw payload size:    212517 bytes
  Compressed size:     51479 bytes
  Compression ratio:   4.13x
  Records Merkle Root: 0x6120e0c2e0712d0eca82b57aa8581dd02cbbb3bddf8136b7976aa63421544064
  Content Hash:        0x46b91d8c2a4535a190e8f36f551cdb6f32512dbc1e5b802bb3320aca167ff686
  Manifest written:    data/encoded_demo/manifest.json
```

**Narration (voiceover as command finishes):**
> "In 12 milliseconds, the encoder serializes the records to RFC 8785 canonical JSON, compresses them 4.1x with Zstandard, packs them into 31-byte field elements to satisfy the BLS12-381 modulus, and binds them to a Keccak-256 Merkle root."

---

### Segment 2: Cryptographic Verification and Tamper Detection (0:25 - 0:55)

**Visual:** Verify command succeeding, then flipping a byte to demonstrate failure.  
**Spoken Narration:**
> "Next, we verify the sidecar against the cryptographic manifest."

**Terminal Command:**
```bash
python frontend-or-cli/rbda_cli.py verify \
  --manifest data/encoded_demo/manifest.json \
  --blobs-dir data/encoded_demo
```

**Expected Output:**
```text
[INFO] Loaded 1 blobs from data/encoded_demo
[INFO] Verifying field-element headers, unpacking stream, and checking commitments...
[SUCCESS] All cryptographic verifications passed:
  Reconstructed records: 500
  Raw payload size:      212517 bytes
  Records Merkle Root:   0x6120e0c2e0712d0eca82b57aa8581dd02cbbb3bddf8136b7976aa63421544064 (MATCH)
  Content Hash:          0x46b91d8c2a4535a190e8f36f551cdb6f32512dbc1e5b802bb3320aca167ff686 (MATCH)
```

**Spoken Narration:**
> "Now let us deliberately corrupt a single byte inside the 128 KiB binary blob sidecar to demonstrate cryptographic tamper detection."

**Terminal Command:**
```bash
python -c "with open('data/encoded_demo/blob_0.bin', 'r+b') as f: f.seek(100); b = f.read(1); f.seek(100); f.write(bytes([b[0] ^ 0xFF]))"
python frontend-or-cli/rbda_cli.py verify \
  --manifest data/encoded_demo/manifest.json \
  --blobs-dir data/encoded_demo
```

**Expected Output:**
```text
[INFO] Loaded 1 blobs from data/encoded_demo
[INFO] Verifying field-element headers, unpacking stream, and checking commitments...
zstandard.backend_c.ZstdError: decompression error: Data corruption detected
```

**Spoken Narration:**
> "The decoder instantly halts on stream corruption, protecting downstream consumers from corrupted or adversary-modified payloads."

---

### Segment 3: Optimistic Property Claims and Fraud Refutation (0:55 - 1:25)

**Visual:** Re-encoding clean blob, generating a claim, and refuting a fraudulent claim.  
**Spoken Narration:**
> "Because smart contracts cannot directly inspect blob bodies on-chain, DatasetRegistry supports optimistic property claims. Let us inspect the citation counts across this academic dataset."

**Terminal Command:**
```bash
python frontend-or-cli/rbda_cli.py encode --input data/real_academic_openalex.json --out-dir data/encoded_demo
python frontend-or-cli/rbda_cli.py claim \
  --input data/real_academic_openalex.json \
  --key cited_by_count \
  --dataset-id 0x46b91d8c2a4535a190e8f36f551cdb6f32512dbc1e5b802bb3320aca167ff686
```

**Expected Output:**
```text
[PROPERTY SUMMARY: 'cited_by_count']
  Record count:     500
  Min value (scaled): 78900 (789.0)
  Max value (scaled): 7664500 (76645.0)
  Mean (scaled):      183640.00 (1836.4000)
```

**Spoken Narration:**
> "If a submitter posts a false claim on-chain—asserting that no paper has over 5,000 citations—anyone can generate a single-record refutation proof."

**Terminal Command:**
```bash
python frontend-or-cli/rbda_cli.py refute \
  --input data/real_academic_openalex.json \
  --key cited_by_count \
  --scale 2 \
  --claimed-min 78900 \
  --claimed-max 500000 \
  --dataset-id 0x46b91d8c2a4535a190e8f36f551cdb6f32512dbc1e5b802bb3320aca167ff686 \
  --claim-index 0
```

**Expected Output:**
```text
[VIOLATION DETECTED]
  Violating record index: 0
  Record content:         {"cited_by_count":76645,"concepts":["Computer science",...],"title":"Exploiting Generative AI..."}
  Merkle Proof Siblings:  9
```

**Spoken Narration:**
> "The CLI identifies record zero with 76,645 citations and outputs the 9 Merkle sibling hashes to slash the false claim on-chain."

---

### Segment 4: Economic Costs and Disaggregated Baselines (1:25 - 1:45)

**Visual:** Display generated benchmark table summary.  
**Spoken Narration:**
> "Now let us view the monetary economics in benchmarks/generated_tables.md."

**Terminal Command:**
```bash
head -n 25 benchmarks/generated_tables.md
```

**Expected Output (Table A display):**
```text
| Dataset Size | Raw Bytes | Blobs Needed | Blob Cost (USD) | Standard Calldata (USD) | Blob Savings vs Calldata | Theoretical SSTORE (USD)* | Min Blocks (SSTORE at 30M Gas) |
| 0.125 MiB | 131,072 | 2 | $10.7079 | $95.32 | 8.9x | $4,074.42 | 4 blocks |
| 1.0 MiB | 1,048,576 | 9 | $27.2379 | $755.92 | 27.8x | $32,588.72 | 25 blocks |
| 5.0 MiB | 5,242,880 | 42 | $105.1651 | $3775.82 | 35.9x | $162,939.83 | 121 blocks |
| 20.0 MiB | 20,971,520 | 166 | $397.9827 | $15100.44 | 37.9x | $651,756.47 | 483 blocks |
```

**Spoken Narration:**
> "At 15 gwei base fee and 2 gwei blob fee, a 1.0 MiB uncompressed payload costs 27 dollars in blobs versus 755 dollars in calldata—a 27.8x saving. Storing 1 MiB in SSTORE would theoretically cost over 32,000 dollars and require 25 full blocks at the 30M gas limit, proving contract storage is impractical. When compressed, as in Table B, the 1 MiB ML trace compresses to 175 KiB and costs just 10 dollars in 2 blobs."

---

### Segment 5: Limitations and Conclusion (1:45 - 2:00)

**Visual:** Display `docs/SEPOLIA_DEPLOYMENT.md` or repository homepage.  
**Spoken Narration:**
> "Finally, the fundamental limitation: consensus clients prune blob sidecars after approximately 4096 epochs, or 18.2 days. Blobs provide temporary decentralized data availability, not permanent storage. Datasets must be archived off-chain or indexed within this window. The codebase, Foundry contracts, and reproduction benchmarks are fully open source on GitHub. Thank you."
