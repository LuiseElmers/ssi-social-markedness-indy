"""Start the ACA-Py containers and initialize the SSI infrastructure."""

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
            timeout=COMPOSE_UP_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise ACAClientError(
            "'docker compose up' did not finish within "
            f"{COMPOSE_UP_TIMEOUT} seconds. The Docker daemon may be busy "
            "or stuck; check 'docker compose ps' and try again."
        )
    except subprocess.CalledProcessError:
        raise ACAClientError("Docker Compose could not start the ACA-Py containers.")


def check_one_agent(agent, name, ready):
    """Check one agent's /status and record the result under its name.

    Runs in its own thread so the four agents can be checked at the same
    time instead of one after another. This is a cheap, read-only call
    (not the CPU-heavy credential definition work), so checking all four
    at once doesn't compete for resources the way that did.
    """
    ready[name] = agent.is_ready()


def wait_for_all_agents():
    """Wait until all four ACA-Py Admin APIs are reachable."""
    print("Waiting for ACA-Py agents (this can take a while on first start) ...")

    start = time.time()
    announced = set()

    while time.time() - start < AGENT_READY_TIMEOUT:
        ready = {}
        threads = []

        for name, url in AGENT_URLS.items():
            agent = ACAClient(name, url)
            thread = threading.Thread(target=check_one_agent, args=(agent, name, ready))
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
                print(f"Waiting for {name} ...")
                announced.add(name)

        if all_ready:
            print("All ACA-Py agents are ready.")
            return

        time.sleep(CHECK_INTERVAL)

    raise ACAClientError(
        "Not all ACA-Py agents became ready within the timeout."
    )


def run_full_initialization():
    """Run the startup steps in the correct order.

    Registering the issuer DIDs has to happen before the containers even
    start, not after: with a --seed (and no --wallet-local-did), ACA-Py
    treats the DID as public and tries to publish its own endpoint to the
    ledger right at startup, which fails if that DID isn't registered on
    the ledger yet. This step only talks to von-network directly, not to
    the agents, so it doesn't need them running anyway.

    Each step is timed and the breakdown is printed at the end, so a slow
    run shows exactly which step ate the time instead of leaving that to
    guesswork from the docker logs.
    """
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
    run_full_initialization()
