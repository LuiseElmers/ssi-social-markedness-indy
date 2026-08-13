"""Start (or resume) the von-network Indy ledger on its own.

Run this once per work session, after a reboot or the very first time.
Leave the containers running afterwards; don't run this again just to
start the SSI prototype. start.py checks that von-network is already up
instead of starting it itself, so repeated test/demo runs stay fast. The
slow part (the four Indy nodes finding consensus, which takes several
minutes under emulation on Apple Silicon) only has to happen here, once.

Use reset.py if you deliberately want to wipe the ledger and start over.
"""

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import set_key

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

# .env only needs to exist here so VON_NETWORK_NAME can be written into
# it below. The agent wallet keys and seeds are start.py's job.
if not ENV_FILE.exists():
    if not ENV_EXAMPLE_FILE.exists():
        sys.exit(
            f"{ENV_EXAMPLE_FILE} is missing. It should be part of this "
            "project's files; please restore it before running this script."
        )
    print("No .env found, creating one from .env.example ...")
    shutil.copy(ENV_EXAMPLE_FILE, ENV_FILE)

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

# von-network doesn't pull a pre-built image. It builds its own local
# image called "von-network-base" from its own Dockerfile, and that
# build has to happen once on every machine, otherwise "docker compose
# up" tries to pull "von-network-base" like a registry image and fails.
image_check = subprocess.run(
    ["docker", "images", "-q", "von-network-base"],
    capture_output=True,
    text=True,
)

if not image_check.stdout.strip():
    print("Building the von-network image (first run only, this can take a while) ...")
    try:
        subprocess.run(["./manage", "build"], cwd=VON_NETWORK_DIR, check=True)
    except subprocess.CalledProcessError:
        sys.exit("Could not build the von-network image. Check the output above for details.")

# von-network auto-detects the address containers should use to reach
# each other (DOCKERHOST). On Docker Desktop for Mac that's normally
# the hostname "host.docker.internal", which can resolve to both an
# IPv6 and an IPv4 address. If the IPv6 route doesn't actually work
# (common on a home or university network without IPv6), the Rust pool
# library the nodes use doesn't fall back to IPv4 the way curl does. It
# just fails the connection forever on a 10s retry loop. Resolving the
# IPv4 address ourselves, from inside a container the same way the
# nodes see it, and passing it explicitly avoids that problem entirely.
def resolve_dockerhost_ipv4():
    """Return the IPv4 address host.docker.internal resolves to from
    inside a container, or None if it can't be determined."""
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "alpine", "ping", "-c", "1", "host.docker.internal"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", result.stdout)
    return match.group(1) if match else None


dockerhost_ip = resolve_dockerhost_ipv4()

# Start von-network with its own start script. If it's already running
# unchanged, this is an instant no-op; it won't restart or recreate
# anything on its own. Passing the resolved IPv4 address only matters
# the first time a ledger volume is created. If von-network/tmp already
# has a genesis file from an earlier run (made with the plain hostname,
# say), this won't retroactively fix it; run reset.py and wipe the
# ledger first if that's needed.
print("Starting von-network (the Indy ledger) ...")
try:
    manage_command = ["./manage", "start"]
    if dockerhost_ip:
        print(f"Using {dockerhost_ip} (resolved from host.docker.internal) as the node address ...")
        manage_command.append(dockerhost_ip)
    subprocess.run(manage_command, cwd=VON_NETWORK_DIR, check=True)
except subprocess.CalledProcessError:
    sys.exit("von-network could not be started. Check the output above for details.")


def get_own_ip():
    """Return this machine's own LAN-facing IP address, or None.

    Only needed for the final "reachable under" message. On a plain
    host with no VM this is usually the same machine the browser runs
    on, so localhost already works there too. But if this script runs
    inside a VM (e.g. UTM on Apple Silicon), localhost in a browser on
    the host machine does not reach it, so printing this IP as a
    fallback saves looking it up by hand every time.
    """
    try:
        result = subprocess.run(
            ["hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    # "hostname -I" can list several addresses, Docker bridge networks
    # included. The first one is normally the machine's main LAN
    # address, which is the one that matters here.
    return result.stdout.split()[0]


def get_webserver_container_name():
    """Return the running von-network webserver container name, or None."""
    names = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return next((n for n in names if "webserver" in n), None)


def restart_webserver():
    """Restart the von-network webserver container quietly.

    Output is captured instead of printed; the caller decides what the
    person actually needs to see, not "docker restart"'s own echo of
    the container name.
    """
    webserver_name = get_webserver_container_name()
    if webserver_name:
        subprocess.run(["docker", "restart", webserver_name], check=True, capture_output=True)
    return webserver_name is not None


# A completely fresh ledger, right after reset.py or on the very first
# start, has to open its pool connection and check the transaction
# author agreement before it reports ready. On an emulated host that
# can take several minutes, so this gets a generous budget. This is the
# one place in the project allowed to be slow, since it only runs once
# per session (start.py just checks readiness instead of waiting).
#
# On a slow host, the webserver's first connection attempt to the four
# nodes can time out before they're actually ready. It only tries once
# right after startup and gives up for good if that fails, so this
# shows up as "init_error" in /status with "ready" staying false
# forever rather than "still starting". Waiting longer doesn't help;
# restarting the webserver does, since the nodes have had more time to
# come up by then. This restarts it once after a fixed grace period,
# then keeps waiting, matching what a manual restart during testing
# reliably fixed. Restarting repeatedly beyond that hasn't made a
# difference in practice, so this stays simple instead of retrying
# forever.
print("Waiting for the von-network ledger to answer (this can take several minutes on a fresh start) ...")
ledger_ready = False
attempts = 900  # 30 minutes at 2s per iteration
RESTART_AFTER = 90  # iterations (180s), give the nodes a real head start first
webserver_restarted = False

for i in range(attempts):
    try:
        response = requests.get("http://localhost:9000/status", timeout=2)

        if response.ok and response.json().get("ready"):
            ledger_ready = True
            break
    except (requests.RequestException, ValueError):
        pass

    if i == RESTART_AFTER and not webserver_restarted:
        print(f"Still starting after {RESTART_AFTER * 2}s, restarting the ledger webserver once ...")
        restart_webserver()
        webserver_restarted = True

    if i > 0 and i % 30 == 0:
        print(f"Still waiting ({i * 2} seconds so far) ...")

    time.sleep(2)

if not ledger_ready:
    sys.exit(
        "The von-network ledger did not answer in time, even after "
        "restarting the webserver once. If the webserver's own logs show "
        "repeated 'Pool timeout' errors and the node containers sit at "
        "0% CPU the whole time, this is likely the IPv6/IPv4 mismatch "
        "this script works around (see the 'Using ... as the node "
        "address' line above), but that only takes effect on a genuinely "
        "fresh ledger volume. If this happens on an existing volume "
        "created before that fix, wipe it once and retry:\n"
        "  python3 reset.py   (choose to also wipe the ledger)\n"
        "  python3 ledger_up.py\n"
        "To confirm the diagnosis directly:\n"
        "  docker logs von-webserver-1 --tail 30\n"
        "  docker stats --no-stream\n"
        "If that's not it, also worth checking: fully quitting and "
        "reopening Docker Desktop (not just the containers), and any "
        "active VPN. If containers are left in a broken state after "
        "this, clean up with:\n"
        "  docker compose down\n"
        "  cd von-network && ./manage down && cd ..\n"
        "  python3 ledger_up.py"
    )

# /status reporting "ready" only means the four nodes found consensus.
# It doesn't mean the webserver's own pool connection, which it uses to
# render the ledger browser page, is actually working. In testing that
# connection sometimes stayed broken even after /status turned ready,
# if it was first opened too early, and the browser page kept failing
# until the webserver container was restarted once more. So this checks
# the actual page too, not just /status, and restarts the webserver
# again if it's still broken; the same manual step that was needed
# during testing, just automatic now.
print("Checking that the ledger browser page is reachable ...")
browser_page_ok = False

for attempt in range(5):
    try:
        response = requests.get("http://localhost:9000/", timeout=5)
        if response.ok:
            browser_page_ok = True
            break
    except requests.RequestException:
        pass
    time.sleep(3)

if not browser_page_ok and not webserver_restarted:
    print("Browser page not responding yet, restarting the webserver ...")
    if restart_webserver():
        webserver_restarted = True
        time.sleep(10)

        for attempt in range(5):
            try:
                response = requests.get("http://localhost:9000/", timeout=5)
                if response.ok:
                    browser_page_ok = True
                    break
            except requests.RequestException:
                pass
            time.sleep(3)

if not browser_page_ok:
    print(
        "Warning: the ledger browser page at http://localhost:9000 is "
        "still not responding, even after a webserver restart. This "
        "doesn't affect the prototype itself (start.py and main.py only "
        "need the ledger to be ready, not the browser page), but if you "
        "need the browser page, try restarting it by hand:\n"
        "  docker restart von-webserver-1"
    )

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

print(
    "\nvon-network is up and ready. Leave it running; start.py will find "
    "it automatically from now on. You only need to run this script again "
    "after a reboot, or after reset.py."
)

# Print where the ledger browser page can actually be opened. On a
# plain host with no VM involved, http://localhost:9000 just works,
# since the browser and the containers are on the same machine. But if
# this script runs inside a VM, "localhost" in a browser on the host
# machine means the host itself, not the VM, so that URL won't work
# there and the VM's own IP has to be used instead. Printing both here
# saves figuring that out by hand every time.
own_ip = get_own_ip()

print("\nThe ledger browser page can be reached at:")
print("  http://localhost:9000")

if own_ip and own_ip != "127.0.0.1":
    print(f"  http://{own_ip}:9000")
    print(
        "If this script runs inside a VM, use the second URL from the "
        "host machine's browser. 'localhost' there points at the host "
        "itself, not the VM."
    )
