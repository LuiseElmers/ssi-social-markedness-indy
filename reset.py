"""Reset the SSI prototyype: deletes all four agent wallets and the local setup state. Optionally also deletes the Indy ledger (von-network)"""

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

delete_ledger = (
    input("Also delete the Indy ledger (von-network)?" "[Y/N]: ").strip().lower() == "y"
)

print("Wiping the SSI agents ...")
subprocess.run(["docker", "compose", "down", "-v"], cwd=PROJECT_DIR, check=True)

state_file = PROJECT_DIR / "runtime" / "state.json"
state_file.unlink(missing_ok=True)

if delete_ledger:
    if (VON_NETWORK_DIR / "manage").exists():
        print("Wiping von-network ...")
        subprocess.run(["./manage", "down"], cwd=VON_NETWORK_DIR, check=True)

    genesis_file = PROJECT_DIR / "genesis.txn"
    genesis_file.unlink(missing_ok=True)

    print("Reset complete.")
else:
    print("Reset complete (ledger kept running)")
