"""Configuration for the SSI prototype."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def get_env(name, default):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value


GOVERNMENT_URL = get_env(
    "GOVERNMENT_URL", f"http://localhost:{get_env('GOVERNMENT_ADMIN_PORT', '8032')}"
)

EMPLOYER_URL = get_env(
    "EMPLOYER_URL", f"http://localhost:{get_env('EMPLOYER_ADMIN_PORT', '8022')}"
)

TENANT_URL = get_env(
    "TENANT_URL", f"http://localhost:{get_env('TENANT_ADMIN_PORT', '8042')}"
)

LANDLORD_URL = get_env(
    "LANDLORD_URL", f"http://localhost:{get_env('LANDLORD_ADMIN_PORT', '8052')}"
)

AGENT_URLS = {
    "Government": GOVERNMENT_URL,
    "Employer": EMPLOYER_URL,
    "Tenant": TENANT_URL,
    "Landlord": LANDLORD_URL,
}

# von-network

VON_NETWORK_NAME = get_env("VON_NETWORK_NAME", "von-network")

LEDGER_REGISTER_URL = get_env("LEDGER_REGISTER_URL", "http://localhost:9000/register")

# Agent seeds

GOVERNMENT_SEED = get_env("GOVERNMENT_SEED", "gov_agent_seed_32_characters_01!")

EMPLOYER_SEED = get_env("EMPLOYER_SEED", "emp_agent_seed_32_characters_02!")

TENANT_SEED = get_env("TENANT_SEED", "tenant_agent_seed_32_characters0")

LANDLORD_SEED = get_env("LANDLORD_SEED", "landlord_agent_seed_32_chars0040")

# Runtime settings

REQUEST_TIMEOUT = 10

LEDGER_WRITE_TIMEOUT = 120

AGENT_READY_TIMEOUT = 1200

COMPOSE_UP_TIMEOUT = 400

WAIT_SECONDS = 60

CHECK_INTERVAL = 2

PROJECT_DIR = Path(__file__).resolve().parent
STATE_FILE = PROJECT_DIR / "runtime" / "state.json"

# Schemas

MARKED_ATTRIBUTES = {
    # Categories of personal data, Regulation (EU) 2016/679, Art. 9(1)
    "race",
    "ethnicity",
    "political_opinion",
    "religion",
    "philosophical_belief",
    "tade_union_membership",
    "genetic_data",
    "biometric_data",
    "health",
    "sexual_orientation",
    # Marked attributes documented in rental housing (Section 4.3)
    "nationality",
    "national_origin",
    "gender",
    "sex",
    "photo",
    "photograph",
    "appearance"
    "disability"
    # Proxies and attributes restricted to predicate disclosure (Section 4.4.3.1)
    "age",
    "residency_status",
    "current_address",
}

PREDICATE_ONLY_ATTRIBUTES = {
    "date_of_birth",
    "is_employed",
}


def check_marked_attributes(schema):
    marked = {
        attribute for attribute in schema["attributes"]
        if attribute.lower() in MARKED_ATTRIBUTES
    }

    if marked:
        raise ValueError(
            f"Schema '{schema['name']}' includes marked attributes "
            f"{sorted(marked)}, which this prototype's governance rules do not allow."
        )


GOVERNMENT_ID_SCHEMA = {
    "name": "GovernmentID",
    "version": "1.3",
    "attributes": [
        "full_name",
        "date_of_birth",
        "expiry_date",
    ],
}
check_marked_attributes(GOVERNMENT_ID_SCHEMA)

EMPLOYMENT_SCHEMA = {
    "name": "EmploymentCredential",
    "version": "1.4",
    "attributes": [
        "employer_name",
        "is_employed",
        "monthly_net_income",
        "employed_since",
    ],
}
check_marked_attributes(EMPLOYMENT_SCHEMA)

RENTAL_MIN_MONTHLY_NET_INCOME = 2500
RENTAL_MIN_AGE_YEARS = 18

RENTAL_PROOF_ALLOWED_ATTRIBUTES = {
    "is_employed",
    "monthly_net_income",
    "date_of_birth",
    "expiry_date",
}


def check_use_case_scope(attributes, predicates):
    requested = set()
    for attribute in attributes.values():
        requested.add(attribute["name"])
    for predicate in predicates.values():
        requested.add(predicate["name"])
    not_allowed = requested - RENTAL_PROOF_ALLOWED_ATTRIBUTES

    if not_allowed:
        raise ValueError(
            f"Proof request asks for {sorted(not_allowed)}, which are not "
            "approved for the rental use case."
        )


def check_disclosure(attributes):
    revealed = set()
    for attribute in attributes.values():
        revealed.add(attribute["name"])
    not_allowed = revealed & (MARKED_ATTRIBUTES | PREDICATE_ONLY_ATTRIBUTES)

    if not_allowed:
        raise ValueError(
            f"Proof request would reveal {sorted(not_allowed)} in cleartext, "
            "which this prototype's governance rules do not allow."
        )
