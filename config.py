"""Configuration for the SSI rental prototype.

Copy .env.example to .env before the first start. Values in .env can be changed
without editing the Python files.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GOVERNMENT_URL = os.getenv("GOVERNMENT_URL", "http://localhost:8032")
EMPLOYER_URL = os.getenv("EMPLOYER_URL", "http://localhost:8022")
TENANT_URL = os.getenv("TENANT_URL", "http://localhost:8042")
LANDLORD_URL = os.getenv("LANDLORD_URL", "http://localhost:8052")

AGENT_URLS = {
    "Government": GOVERNMENT_URL,
    "Employer": EMPLOYER_URL,
    "Tenant": TENANT_URL,
    "Landlord": LANDLORD_URL,
}

VON_NETWORK_NAME = os.getenv("VON_NETWORK_NAME", "von-network")
LEDGER_REGISTER_URL = os.getenv("LEDGER_REGISTER_URL", "http://localhost:9000/register")

GOVERNMENT_SEED = os.getenv("GOVERNMENT_SEED", "gov_agent_seed_32_characters_01!")
EMPLOYER_SEED = os.getenv("EMPLOYER_SEED", "emp_agent_seed_32_characters_02!")
TENANT_SEED = os.getenv("TENANT_SEED", "tenant_agent_seed_32_characters0")
LANDLORD_SEED = os.getenv("LANDLORD_SEED", "landlord_agent_seed_32_chars0040")

REQUEST_TIMEOUT = 10
WAIT_SECONDS = 60
CHECK_INTERVAL = 2

PROJECT_DIR = Path(__file__).resolve().parent
STATE_FILE = PROJECT_DIR / "runtime" / "state.json"

GOVERNMENT_ID_SCHEMA = {
    "name": "GovernmentID",
    "version": "1.0",
    "attributes": ["full_name", "date_of_birth", "residency_status"],
}

EMPLOYMENT_SCHEMA = {
    "name": "EmploymentCredential",
    "version": "1.0",
    "attributes": ["employer_name", "employment_status", "monthly_net_income"],
}
