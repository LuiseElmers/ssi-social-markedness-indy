"""Starts the ACA-Py containers and initializes the SSI infrastructure."""

import subprocess
import threading
import time

from aca_client import ACAClient, ACAClientError
from config import (
    AGENT_READY_TIMEOUT,
    AGENT_URLS,
    CHECK_INTERVAL,
    COMPOSE_UP_TIMEOUT,
    VON_NETWORK_NAME,
)
from scripts.register_seeds import register_issuer_seeds
from scripts.bootstrap import bootstrap

SERVICES = [
    "issuer_government",
    "issuer_employer",
    "holder_tenant",
    "verifier_landlord",
]


def check_von_network():
    try:
        subprocess.run(
            ["docker", "network", "inspect", VON_NETWORK_NAME],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        raise ACAClientError(f"Docker network '{VON_NETWORK_NAME}' was not found.")
    except FileNotFoundError:
        raise ACAClientError("Docker is not installed or not available in PATH.")


def start_containers():
    print("Starting ACA-Py containers...")

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", *SERVICES],
            check=True,
            timeout=COMPOSE_UP_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise ACAClientError(
            f"'docker compose up' did not finish within {COMPOSE_UP_TIMEOUT} seconds."
        )
    except subprocess.CalledProcessError:
        raise ACAClientError("Docker Compose could not start the ACA-Py containers.")


def check_agent(agent, name, ready):
    ready[name] = agent.is_ready()


def wait_for_all_agents():
    print("Waiting for ACA-Py agents. This can take a while on the first run...")

    start = time.time()
    announced = set()

    while time.time() - start < AGENT_READY_TIMEOUT:
        ready = {}
        threads = []
        for name, url in AGENT_URLS.items():
            agent = ACAClient(name, url)
            thread = threading.Thread(target=check_agent, args=(agent, name, ready))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

        all_ready = True

        for name in AGENT_URLS:
            if ready.get(name):
                continue
            all_ready = False
            if name not in announced:
                print(f"Waiting for {name}...")
                announced.add(name)
        if all_ready:
            print("All ACA-Py agents are ready.")
            return

        time.sleep(CHECK_INTERVAL)

    raise ACAClientError("Not all ACA-Py agents became ready within the timeout.")


def run_initialization():
    steps = [
        ("Checking von-network", check_von_network),
        ("Registering issuer DIDs", register_issuer_seeds),
        ("Starting containers", start_containers),
        ("Waiting for agents", wait_for_all_agents),
        ("Bootstrap (schemas, cred defs, connections)", bootstrap),
    ]

    timings = []

    for label, step in steps:
        start = time.time()
        step()
        timings.append((label, time.time() - start))

    print("\nSetup step timings:")
    for label, elapsed in timings:
        print(f"  {label}: {elapsed:.1f}s")


if __name__ == "__main__":
    run_initialization()
