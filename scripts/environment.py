"""Prepare .env and resolve host ports for the SSI prototype's agents."""

import socket
import subprocess
import sys

from dotenv import dotenv_values, set_key
from scripts.common import (
    ENV_FILE,
    ENV_EXAMPLE_FILE,
    PROJECT_DIR,
    check_docker,
    ensure_env_file,
)

AGENT_SERVICES = [
    "issuer_government",
    "issuer_employer",
    "holder_tenant",
    "verifier_landlord",
]

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

REQUIRED_KEYS = [
    "GOVERNMENT_WALLET_KEY",
    "GOVERNMENT_SEED",
    "EMPLOYER_WALLET_KEY",
    "EMPLOYER_SEED",
    "TENANT_WALLET_KEY",
    "TENANT_SEED",
    "LANDLORD_WALLET_KEY",
    "LANDLORD_SEED",
]


def find_free_port(preferred):
    for port in range(preferred, preferred + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue

    sys.exit(f"Could not find a free port near {preferred}.")


def _fill_missing_values():
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

    current_values = dotenv_values(ENV_FILE)
    still_missing = [key for key in REQUIRED_KEYS if not current_values.get(key)]

    if still_missing:
        sys.exit(
            "These values are still missing from .env after trying to "
            f"fill them in: {', '.join(still_missing)}. Please open "
            ".env and check these lines directly."
        )


def _resolve_ports():
    running_services = subprocess.run(
        ["docker", "compose", "ps", "--services", "--filter", "status=running"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    ).stdout.split()

    if all(service in running_services for service in AGENT_SERVICES):
        print("ACA-Py containers are already running, keeping their current ports ...")
        return
    for key, default_port in AGENT_PORT_DEFAULTS.items():
        resolved_port = find_free_port(default_port)
        if resolved_port != default_port:
            print(
                f"Port {default_port} is busy, using {resolved_port} for {key} instead ..."
            )
        set_key(str(ENV_FILE), key, str(resolved_port))


def prepare_environment():
    check_docker()
    ensure_env_file()
    _fill_missing_values()
    _resolve_ports()
