"""Start the ACA-Py containers and initialize the SSI infrastructure."""

import subprocess
import time

from aca_client import ACAClient, ACAClientError
from config import AGENT_URLS, CHECK_INTERVAL, VON_NETWORK_NAME, WAIT_SECONDS
from scripts.register_seeds import register_issuer_seeds
from scripts.setup_schemas_and_connections import bootstrap


SERVICES = [
    "issuer_government",
    "issuer_employer",
    "holder_tenant",
    "verifier_landlord",
]


def check_von_network():
    """Check that the external von-network already exists."""
    try:
        subprocess.run(
            ["docker", "network", "inspect", VON_NETWORK_NAME],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        raise ACAClientError(
            f"Docker network '{VON_NETWORK_NAME}' was not found."
        )
    except FileNotFoundError:
        raise ACAClientError(
            "Docker is not installed or not available in PATH."
        )


def start_containers():
    """Start all ACA-Py containers."""
    print("Starting ACA-Py containers ...")

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", *SERVICES],
            check=True,
        )
    except subprocess.CalledProcessError:
        raise ACAClientError("Docker Compose could not start the ACA-Py containers.")


def wait_for_all_agents():
    """Wait until all four ACA-Py Admin APIs are reachable."""
    print("Waiting for ACA-Py agents ...")

    start = time.time()

    while time.time() - start < WAIT_SECONDS:
        all_ready = True

        for name, url in AGENT_URLS.items():
            agent = ACAClient(name, url)

            if not agent.is_ready():
                print(f"Waiting for {name} ...")
                all_ready = False

        if all_ready:
            print("All ACA-Py agents are ready.")
            return

        time.sleep(CHECK_INTERVAL)

    raise ACAClientError(
        "Not all ACA-Py agents became ready within the timeout."
    )


def run_full_initialization():
    """Run the startup steps in the correct order."""
    check_von_network()
    start_containers()
    wait_for_all_agents()
    register_issuer_seeds()
    bootstrap()


if __name__ == "__main__":
    run_full_initialization()
