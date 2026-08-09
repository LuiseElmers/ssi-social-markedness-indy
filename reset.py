"""Reset the SSI demo: wipes the Indy ledger, all four agent wallets, and
the local setup state.

This cannot be undone. Run start.py afterwards for a clean setup.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VON_NETWORK_DIR = PROJECT_DIR / "von-network"

print("This deletes the Indy ledger, all agent wallets, and runtime/state.json.")
answer = input("Type 'reset' to continue: ")

if answer != "reset":
    print("Aborted, nothing was changed.")
    sys.exit(0)

print("Wiping the SSI agents ...")
subprocess.run(["docker", "compose", "down", "-v"], cwd=PROJECT_DIR, check=True)

if (VON_NETWORK_DIR / "manage").exists():
    print("Wiping von-network ...")
    subprocess.run(["./manage", "down"], cwd=VON_NETWORK_DIR, check=True)

state_file = PROJECT_DIR / "runtime" / "state.json"
genesis_file = PROJECT_DIR / "genesis.txn"

state_file.unlink(missing_ok=True)
genesis_file.unlink(missing_ok=True)

print("Reset complete. Run start.py for a fresh setup.")
