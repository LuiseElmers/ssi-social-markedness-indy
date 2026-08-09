"""Start the full SSI demo: von-network (a real Indy ledger) plus the
SSI prototype.

Safe to run again and again - the ledger and the wallets are kept.
Use reset.py if you want to wipe everything and start over.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values, set_key

PROJECT_DIR = Path(__file__).resolve().parent
VON_NETWORK_DIR = PROJECT_DIR / "von-network"
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE_FILE = PROJECT_DIR / ".env.example"
GENESIS_FILE = PROJECT_DIR / "genesis.txn"

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

# von-network is a git submodule. If it hasn't been fetched yet, do that
# now instead of asking for a separate manual clone.
if not (VON_NETWORK_DIR / "manage").exists():
    print("Fetching von-network (first run only) ...")
    try:
        subprocess.run(
            ["git", "submodule", "update", "--init", "--recursive"],
            cwd=PROJECT_DIR,
            check=True,
        )
    except subprocess.CalledProcessError:
        sys.exit("Could not fetch von-network. Is git installed and working?")

# Start von-network using its own start script.
print("Starting von-network (the Indy ledger) ...")
try:
    subprocess.run(["./manage", "start"], cwd=VON_NETWORK_DIR, check=True)
except subprocess.CalledProcessError:
    sys.exit("von-network could not be started. Check the output above for details.")

# Wait until the ledger answers. A completely fresh ledger (right after
# reset.py) has to open its pool connection and check the transaction
# author agreement before it reports ready, which can take a few minutes
# on a slower machine -- so this gets a generous budget.
#
# On a slow host the webserver's very first connection attempt to the
# four nodes can time out before they're actually ready (it only tries
# once, right after startup, and gives up for good if that fails -- it
# does not keep retrying on its own). That shows up as "init_error" in
# /status and "ready" staying false forever, not as "still starting".
# Waiting longer never fixes that; restarting the webserver container
# does, since the nodes have had time to start properly by then.
print("Waiting for the von-network ledger to answer (this can take a few minutes on a fresh start) ...")
ledger_ready = False
attempts = 180
restarted_webserver = False

for i in range(attempts):
    try:
        response = requests.get("http://localhost:9000/status", timeout=2)

        if response.ok:
            status = response.json()

            if status.get("ready"):
                ledger_ready = True
                break

            if status.get("init_error") and not restarted_webserver:
                print(
                    "von-network's webserver failed to connect to the ledger "
                    "pool on its first try; restarting it ..."
                )
                names = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.splitlines()
                webserver_name = next((n for n in names if "webserver" in n), None)

                if webserver_name:
                    subprocess.run(["docker", "restart", webserver_name], check=True)

                restarted_webserver = True
    except (requests.RequestException, ValueError):
        pass

    if i > 0 and i % 15 == 0:
        print(f"Still waiting ({i * 2} seconds so far) ...")

    time.sleep(2)

if not ledger_ready:
    sys.exit("The von-network ledger did not answer in time.")

# Download the current genesis file so the ACA-Py agents can use it.
print("Fetching the current genesis transactions ...")
response = requests.get("http://localhost:9000/genesis", timeout=10)
response.raise_for_status()
GENESIS_FILE.write_text(response.text)

# Find the Docker network von-network just created, and save its name in
# .env so docker-compose.yml can use it.
result = subprocess.run(
    ["docker", "network", "ls", "--format", "{{.Name}}"],
    capture_output=True,
    text=True,
    check=True,
)

von_network_name = None

for name in result.stdout.splitlines():
    if name.endswith("_von"):
        von_network_name = name
        break

if von_network_name is None:
    sys.exit("Could not find the von-network Docker network.")

set_key(str(ENV_FILE), "VON_NETWORK_NAME", von_network_name)

# Now start the SSI prototype itself.
print("Starting the SSI prototype ...")
subprocess.run([sys.executable, "main.py"], cwd=PROJECT_DIR, check=True)
