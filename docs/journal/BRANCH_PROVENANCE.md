# Branch Provenance and Isolation Audit

This document records the provenance, isolation guarantees, and commit integrity for the journal extension of `research-blob-da`.

## 1. Baseline Repository Identifiers

| Parameter | Identifier / Hash | Verification Command | Status |
|---|---|---|---|
| Repository | `samudragupto/research-blob-da` | `git remote get-url origin` | Verified |
| Initial `origin/main` commit | `ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1` | `git rev-parse origin/main` | Frozen Baseline |
| `v0.1.0` tag hash | `0b523e756d5421e640f4545dc3900e3081fd0d6d` | `git rev-parse v0.1.0` | Frozen Release |
| `v0.1.0` peeled commit hash | `428c7898dd5e5078ad466fa6955058936b33aac3` | `git rev-parse "v0.1.0^{commit}"` | Frozen Release Commit |
| Journal extension branch | `research/journal-extension` | `git branch --show-current` | Active Working Branch |
| Start point | `origin/main` (`ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1`) | `git switch --create research/journal-extension origin/main` | Created 2026-10-28 |

## 2. Mandatory Git Branch Isolation Rules

The following non-negotiable rules govern all work on this repository:

1. **Isolation from Main**: All development, experimentation, and documentation occur exclusively on `research/journal-extension`. No commits may be made directly to `main`.
2. **No Pushing to Main**: Under no circumstances will any command push to `main` or `origin/main`.
3. **No Merging into Main**: No merge commits into `main` will be performed during this task.
4. **No Force-Pushing**: Force-pushing (`--force`, `+branch`) is strictly prohibited on all branches.
5. **No History Rewriting**: Published Git history remains intact; no interactive rebases or commit deletions affecting existing commits.
6. **Preserve Release Tag v0.1.0**: Tag `v0.1.0` (`0b523e756d5421e640f4545dc3900e3081fd0d6d`) must not be moved, retagged, or deleted.
7. **Preserve Published Release Contents**: Content associated with release `v0.1.0` remains historical baseline evidence.
8. **Preserve Frozen Benchmark Artifacts**: Benchmark files enumerated in `benchmarks/FROZEN_BENCHMARKS_v0.1.0.json` must remain unmodified in place. All journal extensions write to `benchmarks/journal-extension/`.
9. **Targeted Remote Push**: Remote synchronization is restricted exclusively to `git push -u origin research/journal-extension`.
10. **No Unauthorized Pull Requests**: No pull request will be opened or merged unless explicitly instructed.
11. **Proof of Unmodified Origin/Main**: The commit hash of `origin/main` is checked at task start (`ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1`) and will be re-verified at task conclusion to prove complete branch isolation.

## 3. Branch Verification Checkpoints

- **Initial State Check**:
  - `git branch --show-current`: `research/journal-extension`
  - `git rev-parse origin/main`: `ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1`
  - `git rev-parse "v0.1.0^{commit}"`: `428c7898dd5e5078ad466fa6955058936b33aac3`
  - Working tree: clean

## 4. Final State and Provenance Verification

- **Task Completion Checkpoint**:
  - Local Working Branch: `research/journal-extension`
  - Initial `origin/main` Commit Hash: `ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1`
  - Final `origin/main` Commit Hash: `ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1`
  - Status of `main`: Strictly unmodified, zero commits or pushes
  - Release Tag `v0.1.0` Commit Hash: `428c7898dd5e5078ad466fa6955058936b33aac3` (Untouched)
  - Frozen v0.1.0 Benchmark Evidence: 100% SHA-256 hash match, zero modifications
  - Journal Extension Artifacts: Contained strictly within `research/journal-extension` branch

## 5. Integrity Audit Baseline

- **Audit Initialization Timestamp**: 2026-10-28T19:01:13+05:30
- **Working Branch**: `research/journal-extension`
- **Verified `origin/main` Commit**: `ad8fefa6157d9e3befa6062fc01ac36f5bfa22f1`
- **Verified `v0.1.0^{commit}` Commit**: `428c7898dd5e5078ad466fa6955058936b33aac3`
- **Journal Extension Pre-Audit HEAD**: `04c23f67c0a717ae2e8e5b5c4ecc563bbb670c51`
- **Isolation Invariant**: Zero writes to `main`, zero tag movements. All integrity corrections isolated to `research/journal-extension`.


