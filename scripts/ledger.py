"""Start (or resume) the von-network Indy ledger and check if it's ready."""

import subprocess
import sys
import time

import requests
from dotenv import dotenv_values, set_key

from scripts.common import ENV_FILE, PROJECT_DIR, check_docker, ensure_env_file

VON_NETWORK_DIR = PROJECT_DIR / "von-network"
GENESIS_FILE = PROJECT_DIR / "genesis.txn"


def _ensure_von_network_submodule():
    if not (VON_NETWORK_DIR / "manage").exists():
        print("Fetching von-network (only on first run) ...")
        try:
            subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=PROJECT_DIR,
                check=True,
            )
        except subprocess.CalledProcessError:
            sys.exit("Could not fetch von-network.")


def _ensure_von_network_image():
    image_check = subprocess.run(
        ["docker", "images", "-q", "von-network-base"], capture_output=True, text=True
    )

    if not image_check.stdout.strip():
        print(
            "Building the von-network image (only on first run), this can take a while) ..."
        )
        try:
            subprocess.run(["./manage", "build"], cwd=VON_NETWORK_DIR, check=True)
        except subprocess.CalledProcessError:
            sys.exit("Could not build the von-network image.")


def _resolve_dockerhost_ipv4():
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "alpine",
                "getent",
                "ahostsv4",
                "host.docker.internal",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None

    return result.stdout.split()[0]


def _start_von_network():
    dockerhost_ip = _resolve_dockerhost_ipv4()

    print("Starting von-network (the Indy ledger) ...")
    try:
        manage_command = ["./manage", "start"]
        if dockerhost_ip:
            print(
                f"Using {dockerhost_ip} (resolved from host.docker.internal) as the node address ..."
            )
            manage_command.append(dockerhost_ip)
        subprocess.run(manage_command, cwd=VON_NETWORK_DIR, check=True)
    except subprocess.CalledProcessError:
        sys.exit("von-network could not be started.")


def get_own_ip():
    try:
        result = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=10
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None

    return result.stdout.split()[0]


def get_webserver_container_name():
    names = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return next((n for n in names if "webserver" in n), None)


def _restart_webserver():
    webserver_name = get_webserver_container_name()
    if webserver_name:
        subprocess.run(
            ["docker", "restart", webserver_name], check=True, capture_output=True
        )
    return webserver_name is not None


def _wait_for_ledger_ready():
    print(
        "Waiting for the von-network ledger to answer (this can take several minutes on a fresh start) ..."
    )
    ledger_ready = False
    attempts = 900  # 30 minutes, 2s for each iteration
    RESTART_AFTER = 90
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
            print(
                f"Still starting after {RESTART_AFTER * 2}s, restarting the ledger webserver once ..."
            )
            _restart_webserver()
            webserver_restarted = True
        if i > 0 and i % 30 == 0:
            print(f"Still waiting ({i * 2} seconds so far) ...")
        time.sleep(2)
    if not ledger_ready:
        sys.exit("The ledger did not answer in time.")

    return webserver_restarted


def _check_browser_page(webserver_already_restarted):
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

    if not browser_page_ok and not webserver_already_restarted:
        print("Browser page not responding yet, restarting the webserver ...")
        if _restart_webserver():
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
            "The ledger browser page at http://localhost:9000 is not responding, even after a webserver restart."
        )


def _fetch_genesis():
    print("Fetching the current genesis transactions ...")
    response = requests.get("http://localhost:9000/genesis", timeout=10)
    response.raise_for_status()
    GENESIS_FILE.write_text(response.text)


def _save_von_network_name():
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
    return von_network_name


def ledger_is_ready():
    von_network_name = None
    if ENV_FILE.exists():
        von_network_name = dotenv_values(ENV_FILE).get("VON_NETWORK_NAME")
    von_network_name = von_network_name or "von_von"

    network_exists = (
        subprocess.run(
            ["docker", "network", "inspect", von_network_name], capture_output=True
        ).returncode
        == 0
    )
    if not network_exists:
        return False

    try:
        response = requests.get("http://localhost:9000/status", timeout=3)
        ready = response.ok and response.json().get("ready", False)
    except (requests.RequestException, ValueError):
        ready = False

    return bool(ready) and GENESIS_FILE.exists()


def ensure_ledger_up():
    check_docker()
    ensure_env_file()
    _ensure_von_network_submodule()
    _ensure_von_network_image()
    _start_von_network()

    webserver_restarted = _wait_for_ledger_ready()
    _check_browser_page(webserver_restarted)
    _fetch_genesis()
    _save_von_network_name()

    print("\nvon-network is up and ready.")

    own_ip = get_own_ip()
    print("\nThe ledger browser page can be reached at: ")
    print("http://localhost:9000")

    if own_ip and own_ip != "127.0.0.1":
        print(f"  http://{own_ip}:9000")
