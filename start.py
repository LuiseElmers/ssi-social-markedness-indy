#!/usr/bin/env python3
"""Starts the SSI prototype by calling main.py"""

import subprocess
import sys
from pathlib import Path

from scripts.environment import prepare_environment
from scripts.ledger import ledger_is_ready

PROJECT_DIR = Path(__file__).resolve().parent

if not ledger_is_ready():
    sys.exit(
        "von-network is not running or not ready yet. Start the "
        "prototype with 'python3 main.py' instead, which handles the "
        "ledger startup automatically."
    )

print("von-network is up ...")
prepare_environment()

print("Starting the SSI prototype ...")
subprocess.run([sys.executable, "main.py"], cwd=PROJECT_DIR, check=True)
