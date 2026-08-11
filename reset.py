"""Reset the SSI demo: wipes all four agent wallets and the local setup
state. Optionally also wipes the Indy ledger itself (von-network) --
kept separate because that forces the slow rebuild ledger_up.py exists
to avoid paying on every reset. Most of the time, only the agents need
resetting (e.g. after a schema/wallet mismatch); the ledger can just
keep running.

This cannot be undone. Run start.py afterwards for a clean setup
(run ledger_up.py first too, if you chose to wipe the ledger).
"""

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VON_NETWORK_DIR = PROJECT_DIR / "von-network"

print("This deletes all four agent wallets and runtime/state.json.")
answer = input("Type 'reset' to continue: ")

if answer != "reset":
    print("Aborted, nothing was changed.")
    sys.exit(0)

wipe_ledger = input(
    "Also wipe the Indy ledger itself (von-network)? This forces the "
    "slow multi-minute rebuild next time -- usually not needed, since "
    "schemas/credentials belong to the agent wallets, not the ledger. "
    "[y/N]: "
).strip().lower() == "y"

print("Wiping the SSI agents ...")
subprocess.run(["docker", "compose", "down", "-v"], cwd=PROJECT_DIR, check=True)

state_file = PROJECT_DIR / "runtime" / "state.json"
state_file.unlink(missing_ok=True)

if wipe_ledger:
    if (VON_NETWORK_DIR / "manage").exists():
        print("Wiping von-network ...")
        subprocess.run(["./manage", "down"], cwd=VON_NETWORK_DIR, check=True)

    genesis_file = PROJECT_DIR / "genesis.txn"
    genesis_file.unlink(missing_ok=True)

    print("Reset complete. Run ledger_up.py, then start.py, for a fresh setup.")
else:
    print("Reset complete (ledger kept running). Run start.py for a fresh agent setup.")
