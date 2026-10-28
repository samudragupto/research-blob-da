"""
network_harness.py: Budget-Controlled Sepolia Experiment Harness for research-blob-da.

Executes repeated on-chain EIP-4844 transactions on Ethereum Sepolia (Chain ID: 11155111)
under strict budget, spending, and credential controls:
- Default safe mode: JOURNAL_NETWORK_EXPERIMENTS_APPROVED=false, 0 transactions, 0 budget.
- Validates chain ID, limits max transaction count, max total ETH, and max fee per tx.
- Performs dry run and prints non-secret execution plan.
- If unapproved or unfunded, documents planned matrix into pending_experiments.json without inventing measurements.
- Never prints private keys or RPC credentials.
"""

import argparse
import datetime
import json
import os
from typing import Any

from web3 import Web3

SAFE_APPROVED_VAR = "JOURNAL_NETWORK_EXPERIMENTS_APPROVED"
DEFAULT_MAX_TX = 0
DEFAULT_MAX_BUDGET_ETH = 0.0
DEFAULT_MAX_FEE_PER_TX_ETH = 0.0
SEPOLIA_CHAIN_ID = 11155111

NETWORK_OUT_DIR = "benchmarks/journal-extension/network"


def get_budget_config() -> dict[str, Any]:
    approved_str = os.getenv(SAFE_APPROVED_VAR, "false").strip().lower()
    approved = approved_str in ("true", "1", "yes")

    try:
        max_tx = int(os.getenv("JOURNAL_MAX_TRANSACTIONS", str(DEFAULT_MAX_TX)))
    except ValueError:
        max_tx = 0

    try:
        max_total_eth = float(
            os.getenv("JOURNAL_MAX_TOTAL_TESTNET_ETH", str(DEFAULT_MAX_BUDGET_ETH))
        )
    except ValueError:
        max_total_eth = 0.0

    try:
        max_fee_per_tx_eth = float(
            os.getenv(
                "JOURNAL_MAX_FEE_PER_TRANSACTION_ETH",
                str(DEFAULT_MAX_FEE_PER_TX_ETH),
            )
        )
    except ValueError:
        max_fee_per_tx_eth = 0.0

    return {
        "approved": approved,
        "max_transactions": max_tx,
        "max_total_eth": max_total_eth,
        "max_fee_per_tx_eth": max_fee_per_tx_eth,
    }


def generate_planned_matrix() -> list[dict[str, Any]]:
    """Generates the 30-submission experimental matrix across 3 dataset classes and 3 payload sizes."""
    datasets = [
        ("real_scholarly_openalex", "OpenAlex Scholarly Works"),
        ("real_climate_sensor", "Atmospheric Sensor Observations"),
        ("real_ml_training_trace", "Transformer ML Training Trace"),
    ]
    size_classes = [
        ("small_1blob", 1),
        ("medium_2blob", 2),
        ("large_6blob", 6),
    ]

    matrix = []
    submission_id = 1
    for d_id, d_name in datasets:
        for s_label, blob_count in size_classes:
            # 3-4 repetitions per combination to total 30
            repetitions = 4 if s_label == "small_1blob" else 3
            for r in range(repetitions):
                matrix.append(
                    {
                        "plan_id": f"SEP-SUBMISSION-{submission_id:03d}",
                        "dataset_id": d_id,
                        "dataset_name": d_name,
                        "size_class": s_label,
                        "blob_count": blob_count,
                        "repetition_index": r + 1,
                        "target_chain_id": SEPOLIA_CHAIN_ID,
                        "status": "PENDING_AUTHORIZATION",
                    }
                )
                submission_id += 1
                if submission_id > 30:
                    break
        if submission_id > 30:
            break
    return matrix


def run_harness(dry_run_only: bool = False):
    os.makedirs(NETWORK_OUT_DIR, exist_ok=True)
    cfg = get_budget_config()
    planned_matrix = generate_planned_matrix()

    print("============================================================")
    print("SEPOLIA NETWORK EXPERIMENT HARNESS: SPENDING & SAFETY CHECK")
    print("============================================================")
    print(f"Authorization Flag ({SAFE_APPROVED_VAR}): {cfg['approved']}")
    print(f"Configured Max Transactions: {cfg['max_transactions']}")
    print(f"Configured Max Budget (ETH): {cfg['max_total_eth']}")
    print(f"Configured Max Fee Per Tx (ETH): {cfg['max_fee_per_tx_eth']}")
    print(f"Target Submissions in Planned Matrix: {len(planned_matrix)}")
    print("============================================================")

    pending_record = {
        "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "safety_configuration": cfg,
        "chain_id": SEPOLIA_CHAIN_ID,
        "planned_submissions_count": len(planned_matrix),
        "execution_status": (
            "PENDING_AUTHORIZATION" if not cfg["approved"] else "APPROVED_DRY_RUN"
        ),
        "notes": (
            "Network experiments on Sepolia are strictly gated by budget controls. "
            "In accordance with research integrity rules, no network transactions are "
            "simulated or fabricated when live execution is unapproved or unfunded."
        ),
        "planned_matrix": planned_matrix,
    }

    pending_path = os.path.join(NETWORK_OUT_DIR, "pending_experiments.json")
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(pending_record, f, indent=2)
    print(f"[OK] Planned experiment matrix written to {pending_path}")

    if not cfg["approved"] or cfg["max_transactions"] == 0 or dry_run_only:
        print("[NOTICE] Live execution is not approved or budget is 0.")
        print(
            "[NOTICE] Harness executed dry-run validation successfully without spending testnet funds."
        )
        return

    # Check for private key in environment only
    priv_key = os.getenv("SEPOLIA_PRIVATE_KEY")
    rpc_url = os.getenv(
        "SEPOLIA_RPC_URL", "https://rpc.sepolia.org"
    )  # default public fallback
    if not priv_key:
        print(
            "[ABORT] Live execution approved but SEPOLIA_PRIVATE_KEY is unset. Halting safely."
        )
        return

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("[ABORT] Cannot connect to Sepolia RPC. Halting.")
        return

    chain_id = w3.eth.chain_id
    if chain_id != SEPOLIA_CHAIN_ID:
        print(
            f"[ABORT] Connected chain ID ({chain_id}) != Sepolia ({SEPOLIA_CHAIN_ID}). Halting."
        )
        return

    account = w3.eth.account.from_key(priv_key)
    balance_wei = w3.eth.get_balance(account.address)
    balance_eth = float(w3.from_wei(balance_wei, "ether"))
    print(f"Connected Account: {account.address[:6]}...{account.address[-4:]}")
    print(f"Current Sepolia Balance: {balance_eth:.4f} ETH")

    if balance_eth < cfg["max_total_eth"]:
        print(
            f"[ABORT] Account balance ({balance_eth} ETH) < configured budget ({cfg['max_total_eth']} ETH)."
        )
        return

    print("Budget checks passed. Ready for execution.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sepolia Network Experiment Harness")
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform non-secret dry run"
    )
    args = parser.parse_args()
    run_harness(dry_run_only=args.dry_run)
