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
#
# start.py resolves a free host port per agent (falling back to the
# next free one if the default is busy) and writes it into .env as
# e.g. GOVERNMENT_ADMIN_PORT. The URL is built from that port here, so
# a busy default port on the machine actually takes effect instead of
# silently being ignored. An explicit GOVERNMENT_URL etc. in .env still
# overrides this completely, for the manual/advanced setup path.

GOVERNMENT_URL = get_env(
    "GOVERNMENT_URL",
    f"http://localhost:{get_env('GOVERNMENT_ADMIN_PORT', '8032')}",
)

EMPLOYER_URL = get_env(
    "EMPLOYER_URL",
    f"http://localhost:{get_env('EMPLOYER_ADMIN_PORT', '8022')}",
)

TENANT_URL = get_env(
    "TENANT_URL",
    f"http://localhost:{get_env('TENANT_ADMIN_PORT', '8042')}",
)

LANDLORD_URL = get_env(
    "LANDLORD_URL",
    f"http://localhost:{get_env('LANDLORD_ADMIN_PORT', '8052')}",
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
# take a few minutes, and longer still under emulation, where the Indy
# pool's own constant CPU use competes with agent startup for the same
# limited cores.
AGENT_READY_TIMEOUT = 600

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
#
# Governance layer: no issuer schema in this project may include a
# "marked" attribute -- a category that anti-discrimination frameworks
# treat as protected (e.g. Fair Housing Act: race, color, national
# origin, religion, sex, familial status, disability), or a close proxy
# for one (residency status -> national origin/immigration status,
# current address -> neighborhood/redlining proxy). This is enforced
# below, not just followed by convention: a schema containing a marked
# attribute makes the program refuse to start.
#
# date_of_birth is a special case: it's a proxy for age (also a marked
# category), but unlike gender/nationality/etc. it's numeric and
# ordinal, so AnonCreds predicate proofs can use it for a threshold
# check (e.g. "born on/before X" for a legal-age proof) without ever
# revealing the actual date. It's therefore allowed in a schema, but a
# separate rule below (assert_request_does_not_reveal_marked_attributes)
# ensures no proof request may ever place it in requested_attributes
# (a cleartext reveal) -- only in requested_predicates.

MARKED_ATTRIBUTES = {
    "race",
    "ethnicity",
    "nationality",
    "national_origin",
    "gender",
    "sex",
    "religion",
    "disability",
    "marital_status",
    "familial_status",
    "sexual_orientation",
    "age",
    "residency_status",
    "current_address",
}

# Marked-adjacent attributes that may appear in a schema because they
# have a legitimate predicate-only use (see comment above). Everything
# in MARKED_ATTRIBUTES itself may never appear in any schema at all.
PREDICATE_ONLY_ATTRIBUTES = {
    "date_of_birth",
}


def assert_no_marked_attributes(schema):
    """Refuse to start if a schema definition includes a marked attribute."""
    marked = set(schema["attributes"]) & MARKED_ATTRIBUTES

    if marked:
        raise ValueError(
            f"Schema '{schema['name']}' includes marked attributes "
            f"{sorted(marked)}, which this project's governance rules "
            "do not allow."
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
assert_no_marked_attributes(GOVERNMENT_ID_SCHEMA)

EMPLOYMENT_SCHEMA = {
    "name": "EmploymentCredential",
    "version": "1.3",
    "attributes": [
        "employer_name",
        "employment_status",
        "monthly_net_income",
        "employed_since",
    ],
}
assert_no_marked_attributes(EMPLOYMENT_SCHEMA)

# Governance layer, continued: which attributes/predicates a Verifier's
# proof request is allowed to reference for the rental use case. This
# mirrors MARKED_ATTRIBUTES above, but restricts the Verifier side
# instead of the Issuer side -- even from the already-unmarked attribute
# pool across both schemas, only what's actually needed for a rental
# eligibility check is approved. full_name and employer_name, for
# example, exist in issued credentials, but a proof request that tries
# to reference them is rejected here before it's ever sent.
RENTAL_PROOF_ALLOWED_ATTRIBUTES = {
    "employment_status",
    "monthly_net_income",
    "date_of_birth",
    "expiry_date",
}


def assert_request_is_use_case_appropriate(attributes, predicates):
    """Refuse to build a proof request that exceeds the approved allowlist."""
    requested = {attribute["name"] for attribute in attributes.values()}
    requested |= {predicate["name"] for predicate in predicates.values()}
    disallowed = requested - RENTAL_PROOF_ALLOWED_ATTRIBUTES

    if disallowed:
        raise ValueError(
            f"Proof request asks for {sorted(disallowed)}, which are not "
            "approved for the rental use case."
        )


def assert_request_does_not_reveal_marked_attributes(attributes):
    """Refuse to build a proof request that reveals a marked attribute
    in cleartext -- date_of_birth (and anything else marked) may only
    ever be used inside requested_predicates, never requested_attributes.
    """
    revealed = {attribute["name"] for attribute in attributes.values()}
    disallowed = revealed & (MARKED_ATTRIBUTES | PREDICATE_ONLY_ATTRIBUTES)

    if disallowed:
        raise ValueError(
            f"Proof request would reveal {sorted(disallowed)} in "
            "cleartext, which this project's governance rules do not allow."
        )
