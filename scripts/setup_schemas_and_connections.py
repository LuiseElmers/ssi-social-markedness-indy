"""Create the Indy artefacts and DIDComm connections for the prototype."""

import time

from scripts.aca_client import ACAClient, ACAClientError
from scripts.config import (
    CHECK_INTERVAL,
    EMPLOYER_URL,
    EMPLOYMENT_SCHEMA,
    GOVERNMENT_ID_SCHEMA,
    GOVERNMENT_URL,
    LANDLORD_URL,
    TENANT_URL,
    WAIT_SECONDS,
)
from scripts.state_store import load_state, save_state


def get_id(response, key):
    """Read an ID from an ACA-Py response."""
    if response.get(key):
        return response[key]
    if response.get("connection_record", {}).get(key):
        return response["connection_record"][key]
    raise ACAClientError(f"ACA-Py response does not contain '{key}'.")


def wait_for_connection(client, connection_id):
    start = time.time()
    while time.time() - start < WAIT_SECONDS:
        if client.connection(connection_id).get("state") == "completed":
            return
        time.sleep(CHECK_INTERVAL)
    raise ACAClientError("Connection was not completed in time.")


def connect(issuer, tenant, name):
    """Create one invitation and let the tenant accept it."""
    invitation_response = issuer.create_invitation(name)
    invitation = invitation_response.get("invitation")
    if not invitation:
        raise ACAClientError("ACA-Py did not return an invitation.")

    issuer_connection_id = get_id(invitation_response, "connection_id")
    tenant_response = tenant.receive_invitation(invitation, name)
    tenant_connection_id = get_id(tenant_response, "connection_id")

    wait_for_connection(issuer, issuer_connection_id)
    wait_for_connection(tenant, tenant_connection_id)
    return {"issuer": issuer_connection_id, "tenant": tenant_connection_id}


def bootstrap():
    """Create everything that is missing and save its IDs locally."""
    state = load_state()

    government = ACAClient("Government", GOVERNMENT_URL)
    employer = ACAClient("Employer", EMPLOYER_URL)
    tenant = ACAClient("Tenant", TENANT_URL)
    landlord = ACAClient("Landlord", LANDLORD_URL)

    if "government_cred_def_id" not in state:
        response = government.create_schema(GOVERNMENT_ID_SCHEMA)
        schema_id = get_id(response, "schema_id")
        response = government.create_credential_definition(schema_id)
        state["government_cred_def_id"] = get_id(response, "credential_definition_id")
        print("Government schema and credential definition created.")

    if "employment_cred_def_id" not in state:
        response = employer.create_schema(EMPLOYMENT_SCHEMA)
        schema_id = get_id(response, "schema_id")
        response = employer.create_credential_definition(schema_id)
        state["employment_cred_def_id"] = get_id(response, "credential_definition_id")
        print("Employment schema and credential definition created.")

    if "government_tenant" not in state:
        state["government_tenant"] = connect(government, tenant, "government-tenant")
        print("Government and Tenant connected.")

    if "employer_tenant" not in state:
        state["employer_tenant"] = connect(employer, tenant, "employer-tenant")
        print("Employer and Tenant connected.")

    if "landlord_tenant" not in state:
        state["landlord_tenant"] = connect(landlord, tenant, "landlord-tenant")
        print("Landlord and Tenant connected.")

    save_state(state)
    print("SSI setup completed.")


if __name__ == "__main__":
    bootstrap()
