"""Create the Indy artifacts and DIDComm connections for the prototype."""

import time

from aca_client import ACAClient, ACAClientError, ACATimeoutError
from config import (
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


def ensure_schema(client, schema):
    public_did = client.get_public_did()
    schema_id = f"{public_did}:2:{schema['name']}:{schema['version']}"

    ledger_schema = client.fetch_schema(schema_id)

    if ledger_schema:
        existing = sorted(ledger_schema.get("attrNames", []))
        wanted = sorted(schema["attributes"])
        if existing != wanted:
            raise ACAClientError(
                f"Schema {schema_id} already exists with different "
                f"attributes ({existing}) than requested ({wanted})."
            )
        return schema_id

    print(f"Creating schema: {schema['name']} {schema['version']}")

    response = client.create_schema(public_did, schema)
    return response["schema_state"]["schema_id"]


def ensure_credential_definition(client, schema_id, cached_id=None, base_tag="default"):
    if cached_id and cached_id in client.created_credential_definitions():
        return cached_id
    for cred_def_id in client.created_credential_definitions():
        details = client.fetch_credential_definition(cred_def_id)
        if details and details.get("schemaId") == schema_id:
            return cred_def_id

    public_did = client.get_public_did()
    return create_cred_def(client, public_did, schema_id, base_tag)


def create_cred_def(client, public_did, schema_id, base_tag):
    tag = base_tag
    attempt = 1

    while True:
        print("Creating credential definition (this can take a moment) ...")

        try:
            response = client.create_credential_definition(public_did, schema_id, tag)
            return response["credential_definition_state"]["credential_definition_id"]
        except ACATimeoutError:
            cred_def_id = wait_for_cred_def(client, schema_id)
            if cred_def_id:
                return cred_def_id
            raise
        except ACAClientError:
            attempt += 1
            if attempt > 20:
                raise
            tag = f"{base_tag}-{attempt}"


def wait_for_cred_def(client, schema_id):
    start = time.time()

    while time.time() - start < WAIT_SECONDS:
        for cred_def_id in client.created_credential_definitions():
            details = client.fetch_credential_definition(cred_def_id)
            if details and details.get("schemaId") == schema_id:
                return cred_def_id
        time.sleep(CHECK_INTERVAL)

    return None


def wait_for_issuer_connection(issuer, invi_msg_id):
    start = time.time()

    while time.time() - start < WAIT_SECONDS:
        connection_id = issuer.find_connection_by_invitation(invi_msg_id)
        if connection_id:
            return connection_id
        time.sleep(CHECK_INTERVAL)

    raise ACAClientError("No connection was created from the invitation in time.")


def wait_for_connection(client, connection_id):
    start = time.time()

    while time.time() - start < WAIT_SECONDS:
        connection = client.connection(connection_id)
        state = connection.get("state")
        if state in ("completed", "active"):
            return
        if state == "abandoned":
            raise ACAClientError("Connection was abandoned.")
        time.sleep(CHECK_INTERVAL)

    raise ACAClientError("Connection was not completed in time.")


def connect(issuer, tenant, name):
    invitation_response = issuer.create_invitation(name)
    invitation = invitation_response.get("invitation")

    if not invitation:
        raise ACAClientError("ACA-Py did not return an invitation.")
    invi_msg_id = invitation_response.get("invi_msg_id") or invitation.get("@id")
    if not invi_msg_id:
        raise ACAClientError(
            "ACA-Py response does not contain an invitation message ID."
        )

    tenant_response = tenant.receive_invitation(invitation, name)

    tenant_connection_id = get_id(tenant_response, "connection_id")
    issuer_connection_id = wait_for_issuer_connection(issuer, invi_msg_id)

    wait_for_connection(issuer, issuer_connection_id)
    wait_for_connection(tenant, tenant_connection_id)

    return {
        "issuer": issuer_connection_id,
        "tenant": tenant_connection_id,
    }


def ensure_connection(state, key, issuer, tenant, alias):
    cached = state.get(key)

    if (
        cached
        and issuer.connection_is_usable(cached.get("issuer"))
        and tenant.connection_is_usable(cached.get("tenant"))
    ):
        return cached
    issuer_connection_id = issuer.find_usable_connection_by_alias(alias)
    tenant_connection_id = tenant.find_usable_connection_by_alias(alias)
    if issuer_connection_id and tenant_connection_id:
        return {
            "issuer": issuer_connection_id,
            "tenant": tenant_connection_id,
        }

    return connect(issuer, tenant, alias)


def bootstrap():
    """Create everything that is missing and save its IDs locally."""
    state = load_state()

    government = ACAClient("Government", GOVERNMENT_URL)
    employer = ACAClient("Employer", EMPLOYER_URL)
    tenant = ACAClient("Tenant", TENANT_URL)
    landlord = ACAClient("Landlord", LANDLORD_URL)

    government_schema_id = ensure_schema(government, GOVERNMENT_ID_SCHEMA)
    government_cred_def_id = ensure_credential_definition(
        government, government_schema_id, state.get("government_cred_def_id")
    )

    state["government_schema_id"] = government_schema_id
    state["government_cred_def_id"] = government_cred_def_id
    save_state(state)

    print("Government credential definition ready.")

    employment_schema_id = ensure_schema(employer, EMPLOYMENT_SCHEMA)
    employment_cred_def_id = ensure_credential_definition(
        employer,
        employment_schema_id,
        state.get("employment_cred_def_id"),
    )

    state["employment_schema_id"] = employment_schema_id
    state["employment_cred_def_id"] = employment_cred_def_id
    save_state(state)

    print("Employment credential definition ready.")

    # Connections
    state["government_tenant"] = ensure_connection(
        state, "government_tenant", government, tenant, "government-tenant"
    )
    save_state(state)

    state["employer_tenant"] = ensure_connection(
        state, "employer_tenant", employer, tenant, "employer-tenant"
    )
    save_state(state)

    state["landlord_tenant"] = ensure_connection(
        state, "landlord_tenant", landlord, tenant, "landlord-tenant"
    )
    save_state(state)

    print("Connections ready.")
    print("SSI setup completed.")


if __name__ == "__main__":
    bootstrap()
