"""Register the two issuer seeds on the ledger."""

import time

import requests

from aca_client import ACAClientError
from config import (
    CHECK_INTERVAL,
    EMPLOYER_SEED,
    GOVERNMENT_SEED,
    LEDGER_REGISTER_URL,
    REQUEST_TIMEOUT,
    WAIT_SECONDS,
)


def register_seed(name, seed):
    start = time.time()
    while time.time() - start < WAIT_SECONDS:
        try:
            response = requests.post(
                LEDGER_REGISTER_URL,
                json={"seed": seed, "role": "ENDORSER"},
                timeout=REQUEST_TIMEOUT,
            )
            if response.ok or "already" in response.text.lower():
                print(f"Ledger DID ready: {name}")
                return
            print(
                f"Waiting for ledger registration of {name}: HTTP {response.status_code}"
            )
        except requests.RequestException:
            print(f"Waiting for ledger registration service: {name}")
        time.sleep(CHECK_INTERVAL)
    raise ACAClientError(f"Could not register {name} at {LEDGER_REGISTER_URL}")


# Only issuers need a ledger write role
# Tenant and Landlord use DIDComm peer DIDs
def register_issuer_seeds():
    print("Registering issuer DIDs on von-network ...")
    register_seed("Government", GOVERNMENT_SEED)
    register_seed("Employer", EMPLOYER_SEED)


if __name__ == "__main__":
    register_issuer_seeds()
