"""Start the SSI prototype's ACA-Py agents against an already-running
von-network ledger.

This does NOT start von-network itself anymore -- run ledger_up.py once
per work session (or after a reboot) and leave it running. Starting the
ledger is the slow part on an emulated host (several minutes); checking
that it's already up, which is all this script does, is fast. That
keeps repeated test/demo runs fast too.

Safe to run again and again - the agent wallets are kept.
Use reset.py if you want to wipe the agents (and optionally the ledger)
and start over.
"""

import shutil
import socket
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values, set_key

from scripts.setup_infrastructure import SERVICES as AGENT_SERVICES

PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE_FILE = PROJECT_DIR / ".env.example"
GENESIS_FILE = PROJECT_DIR / "genesis.txn"

# Host ports each agent needs (inbound transport + admin API). Only the
# host side is ever changed here -- the container-internal port stays
# fixed in docker-compose.yml, so agent-to-agent connections (which use
# the Docker network, not these host ports) are never affected.
AGENT_PORT_DEFAULTS = {
    "GOVERNMENT_HTTP_PORT": 8031,
    "GOVERNMENT_ADMIN_PORT": 8032,
    "EMPLOYER_HTTP_PORT": 8021,
    "EMPLOYER_ADMIN_PORT": 8022,
    "TENANT_HTTP_PORT": 8041,
    "TENANT_ADMIN_PORT": 8042,
    "LANDLORD_HTTP_PORT": 8051,
    "LANDLORD_ADMIN_PORT": 8052,
}


def find_free_port(preferred):
    """Return preferred if it's free right now, otherwise the next free
    port after it (checked one at a time, up to 100 above preferred)."""
    for port in range(preferred, preferred + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue

    sys.exit(f"Could not find a free port near {preferred}.")

# Check that Docker is installed and that we have the newer "docker
# compose" command, not the old separate "docker-compose".
if shutil.which("docker") is None:
    sys.exit("Docker is not installed or not on PATH.")

result = subprocess.run(["docker", "compose", "version"], capture_output=True)
if result.returncode != 0:
    sys.exit("Docker Compose v2 is required (the 'docker compose' command).")

# Create .env from .env.example the first time this runs.
if not ENV_EXAMPLE_FILE.exists():
    sys.exit(
        f"{ENV_EXAMPLE_FILE} is missing. It should be part of this "
        "project's files -- please restore it before running this script."
    )

if not ENV_FILE.exists():
    print("No .env found, creating one from .env.example ...")
    shutil.copy(ENV_EXAMPLE_FILE, ENV_FILE)

# If .env already existed from before .env.example gained new variables
# (e.g. the wallet keys/seeds), add whatever is missing or blank. A blank
# value (key present but empty, e.g. "GOVERNMENT_WALLET_KEY=") is treated
# the same as missing, since it's not something anyone set on purpose.
# Anything with an actual value in .env is never touched.
#
# All missing lines are collected first and appended in a single write,
# instead of writing the file once per key -- calling set_key() in a loop
# rewrites the whole file every time, which turned out to be unreliable.
example_values = dotenv_values(ENV_EXAMPLE_FILE)
current_values = dotenv_values(ENV_FILE)
lines_to_add = []

for key, value in example_values.items():
    if not current_values.get(key):
        print(f"Adding missing {key} to .env ...")
        lines_to_add.append(f"{key}={value}")

if lines_to_add:
    with open(ENV_FILE, "a") as env_file:
        env_file.write("\n" + "\n".join(lines_to_add) + "\n")

# Confirm the values docker-compose.yml actually needs are really there
# now, instead of only finding out four containers later. Re-read .env
# fresh, since the values above were just written to it.
required_keys = [
    "GOVERNMENT_WALLET_KEY",
    "GOVERNMENT_SEED",
    "EMPLOYER_WALLET_KEY",
    "EMPLOYER_SEED",
    "TENANT_WALLET_KEY",
    "TENANT_SEED",
    "LANDLORD_WALLET_KEY",
    "LANDLORD_SEED",
]
current_values = dotenv_values(ENV_FILE)
still_missing = [key for key in required_keys if not current_values.get(key)]

if still_missing:
    sys.exit(
        "These values are still missing from .env after trying to fill "
        f"them in: {', '.join(still_missing)}. Please open .env and check "
        "these lines directly."
    )

# von-network is expected to already be running (started separately via
# ledger_up.py -- see that file's docstring for why). This only checks
# readiness; it never starts, restarts, or waits minutes for it, so a
# missing ledger fails fast with clear instructions instead of hanging.
von_network_name = dotenv_values(ENV_FILE).get("VON_NETWORK_NAME") or "von_von"

network_exists = subprocess.run(
    ["docker", "network", "inspect", von_network_name],
    capture_output=True,
).returncode == 0

ledger_ready = False

if network_exists:
    try:
        response = requests.get("http://localhost:9000/status", timeout=3)
        ledger_ready = response.ok and response.json().get("ready", False)
    except (requests.RequestException, ValueError):
        pass

if not ledger_ready or not GENESIS_FILE.exists():
    sys.exit(
        "von-network is not running (or not ready yet). This project no "
        "longer starts it automatically, so repeated test/demo runs stay "
        "fast:\n"
        "  python3 ledger_up.py\n"
        "Run that once per session (after a reboot, or the first time) "
        "and leave it running -- start.py picks it up automatically and "
        "stays fast every time after that."
    )

print("von-network is up and ready, continuing ...")

# Each agent needs two host ports. Always try the project's own default
# first (so ports stay predictable run to run); only move to the next
# free one if something else on the machine already has the default.
#
# Skip this entirely if the agent containers are already running (e.g.
# start.py is just being run again while the prototype is still up) --
# otherwise a "busy" default port would just be their own container, and
# reassigning it would force an unnecessary restart.
running_services = subprocess.run(
    ["docker", "compose", "ps", "--services", "--filter", "status=running"],
    cwd=PROJECT_DIR,
    capture_output=True,
    text=True,
).stdout.split()

if all(service in running_services for service in AGENT_SERVICES):
    print("ACA-Py containers are already running, keeping their current ports ...")
else:
    for key, default_port in AGENT_PORT_DEFAULTS.items():
        resolved_port = find_free_port(default_port)

        if resolved_port != default_port:
            print(f"Port {default_port} is busy, using {resolved_port} for {key} instead ...")

        set_key(str(ENV_FILE), key, str(resolved_port))

# Now start the SSI prototype itself.
print("Starting the SSI prototype ...")
subprocess.run([sys.executable, "main.py"], cwd=PROJECT_DIR, check=True)
