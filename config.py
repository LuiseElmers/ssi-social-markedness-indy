"""Configuration for the SSI rental prototype.

Copy .env.example to .env before the first start. Values in .env can be changed
without editing the Python files.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

def get_env(name, default):
    """
    Read environment variable.
    Use default when value is missing or empty.
    """
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value

# ACA-Py Admin APIs

GOVERNMENT_URL = get_env(
    "GOVERNMENT_URL",
    "http://localhost:8032",
)

EMPLOYER_URL = get_env(
    "EMPLOYER_URL",
    "http://localhost:8022",
)

TENANT_URL = get_env(
    "TENANT_URL",
    "http://localhost:8042",
)

LANDLORD_URL = get_env(
    "LANDLORD_URL",
    "http://localhost:8052",
)

AGENT_URLS = {
    "Government": GOVERNMENT_URL,
    "Employer": EMPLOYER_URL,
    "Tenant": TENANT_URL,
    "Landlord": LANDLORD_URL,
}

# VON-network

VON_NETWORK_NAME = os.getenv(
    "VON_NETWORK_NAME",
    "von-network",
)

LEDGER_REGISTER_URL = os.getenv(
    "LEDGER_REGISTER_URL",
    "http://localhost:9000/register",
)

# Agent seeds

GOVERNMENT_SEED = os.getenv(
    "GOVERNMENT_SEED",
    "gov_agent_seed_32_characters_01!",
)

EMPLOYER_SEED = os.getenv(
    "EMPLOYER_SEED",
    "emp_agent_seed_32_characters_02!",
)

TENANT_SEED = os.getenv(
    "TENANT_SEED",
    "tenant_agent_seed_32_characters0",
)

LANDLORD_SEED = os.getenv(
    "LANDLORD_SEED",
    "landlord_agent_seed_32_chars0040",
)

# Runtime settings

REQUEST_TIMEOUT = 10

# Writing a schema or credential definition to the Indy ledger is slow,
# especially the first ones after a fresh start, so they get more time.
LEDGER_WRITE_TIMEOUT = 120

# On a cold start each agent provisions its wallet and may run an internal
# upgrade before its Admin API answers. With four agents at once this can
# take a few minutes.
AGENT_READY_TIMEOUT = 300

# Upper bound for "docker compose up" so a stuck daemon can't hang forever.
# On slower or emulated hosts, plain container startup (before any agent
# work even begins) has been observed to take well over four minutes, so
# this needs real headroom above that, not just above a typical run.
COMPOSE_UP_TIMEOUT = 400

WAIT_SECONDS = 60
CHECK_INTERVAL = 2

PROJECT_DIR = Path(__file__).resolve().parent
STATE_FILE = PROJECT_DIR / "runtime" / "state.json"

# Schemas

GOVERNMENT_ID_SCHEMA = {
    "name": "GovernmentID",
    "version": "1.0",
    "attributes": [
        "full_name",
        "date_of_birth",
        "residency_status",
    ],
}

EMPLOYMENT_SCHEMA = {
    "name": "EmploymentCredential",
    "version": "1.0",
    "attributes": [
        "employer_name",
        "employment_status",
        "monthly_net_income",
    ],
}
