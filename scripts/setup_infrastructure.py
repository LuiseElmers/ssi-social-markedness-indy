"""Start the ACA-Py containers and wait until they are ready."""

import subprocess
import time

from scripts.aca_client import ACAClient, ACAClientError
from scripts.config import AGENT_URLS, CHECK_INTERVAL, VON_NETWORK_NAME, WAIT_SECONDS
from scripts.register_seeds import register_issuer_seeds
from scripts.setup_schemas_and_connections import bootstrap

SERVICES = [
    "issuer_government",
    "issuer_employer",
    "holder_tenant",
    "verifier_landlord",
]


def check_von_network():
    """Check that the external von-network from .env already exists."""
    try:
        subprocess.run(["docker", "network", "inspect", VON_NETWORK_NAME], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        raise ACAClientError(f"Docker network '{VON_NETWORK_NAME}' was not found.")
    except FileNotFoundError:
        raise ACAClientError("Docker is not installed or not available in PATH.")


def start_containers():
    """Start one service after another to avoid a sudden load spike in the VM."""
    print("Starting ACA-Py containers ...")
    for service in SERVICES:
        try:
            subprocess.run(["docker", "compose", "up", "-d", service], check=True)
        except subprocess.CalledProcessError:
            raise ACAClientError(f"Docker Compose could not start '{service}'.")


def wait_for_all_agents():
    """Check /status repeatedly until all four Admin APIs respond."""
    print("Waiting for ACA-Py agents ...")
    start = time.time()

    while time.time() - start < WAIT_SECONDS:
        all_ready = True
        for name, url in AGENT_URLS.items():
            try:
                ACAClient(name, url).status()
            except ACAClientError:
                print(f"Waiting for {name} ...")
                all_ready = False

        if all_ready:
            print("All ACA-Py agents are ready.")
            return
        time.sleep(CHECK_INTERVAL)

    raise ACAClientError("Not all ACA-Py agents became ready in time.")


def run_full_initialization():
    """Run the startup steps in the same order on every machine."""
    check_von_network()
    register_issuer_seeds()
    start_containers()
    wait_for_all_agents()
    bootstrap()


if __name__ == "__main__":
    run_full_initialization()
