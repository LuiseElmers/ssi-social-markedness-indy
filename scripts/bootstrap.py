"""Create the Indy artefacts and DIDComm connections for the prototype."""

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
    """Return the schema ID, creating the schema on the ledger if needed.

    The schema ID is fixed by the issuer DID, name and version, so we can
    check the ledger for it directly instead of trusting the wallet's own
    list, which is empty after a wallet reset.
    """
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
    """Return a usable credential definition ID, creating one if needed.

    Checks the cached ID from state.json first. If this wallet still has
    it, that's immediately the answer. Otherwise look through what the
    wallet already created for one that matches this schema. If nothing
    usable is found, create a new one -- trying a fresh tag if the first
    one is already taken by a credential definition this wallet no longer
    holds the signing key for (e.g. after a wallet reset).
    """
    if cached_id and cached_id in client.created_credential_definitions():
        return cached_id

    for cred_def_id in client.created_credential_definitions():
        details = client.fetch_credential_definition(cred_def_id)

        if details and details.get("schemaId") == schema_id:
            return cred_def_id

    public_did = client.get_public_did()
    return create_cred_def(client, public_did, schema_id, base_tag)


def create_cred_def(client, public_did, schema_id, base_tag):
    """Create a credential definition, retrying under a new tag if needed.

    The ledger write can outlast the HTTP read timeout even though the
    agent finishes it. If that happens, check whether it actually landed
    before giving up. A tag can also simply already be taken by an old,
    now-inaccessible credential definition (e.g. after a wallet reset) --
    in that case the create call fails outright, so just try the next tag.
    """
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
    """Wait for a credential definition for this schema to show up, or None."""
    start = time.time()

    while time.time() - start < WAIT_SECONDS:
        for cred_def_id in client.created_credential_definitions():
            details = client.fetch_credential_definition(cred_def_id)
            if details and details.get("schemaId") == schema_id:
                return cred_def_id

        time.sleep(CHECK_INTERVAL)

    return None


def wait_for_issuer_connection(issuer, invi_msg_id):
    """Wait for the issuer's connection record for this invitation."""
    start = time.time()

    while time.time() - start < WAIT_SECONDS:
        connection_id = issuer.find_connection_by_invitation(invi_msg_id)

        if connection_id:
            return connection_id

        time.sleep(CHECK_INTERVAL)

    raise ACAClientError(
        "No connection was created from the invitation in time."
    )


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
    """Create one invitation and let the tenant accept it."""
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

    # The issuer only gets its connection once the tenant answers.
    issuer_connection_id = wait_for_issuer_connection(issuer, invi_msg_id)

    wait_for_connection(issuer, issuer_connection_id)
    wait_for_connection(tenant, tenant_connection_id)

    return {
        "issuer": issuer_connection_id,
        "tenant": tenant_connection_id,
    }


def ensure_connection(state, key, issuer, tenant, alias):
    """Return a usable connection, reusing one wherever possible.

    A connection only counts as a wallet's source of truth. state.json is
    just a cache of it, so a cached entry is used only after we've checked
    both wallets still agree it's usable. Three cases:

      1. state.json has an entry and both wallets confirm it's still
         usable -> reuse it as is.
      2. state.json is missing or stale, but a usable connection under
         this alias already exists in both wallets (e.g. state.json was
         lost, or this is a repeated run) -> reuse that one instead.
      3. Neither has anything usable -> create a fresh connection.
    """
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

    # Credential definition creation is CPU-heavy work that happens inside
    # the ACA-Py containers (key generation for the CL signature scheme).
    # Running Government's and Employer's setup at the same time made this
    # slower, not faster, since both containers ended up competing for the
    # same limited CPU instead of actually working in parallel. So this
    # part stays sequential; see setup_infrastructure.py for where
    # parallelism actually helps.

    government_schema_id = ensure_schema(
        government,
        GOVERNMENT_ID_SCHEMA,
    )

    government_cred_def_id = ensure_credential_definition(
        government,
        government_schema_id,
        state.get("government_cred_def_id"),
    )

    state["government_schema_id"] = government_schema_id
    state["government_cred_def_id"] = government_cred_def_id
    save_state(state)

    print("Government credential definition ready.")

    employment_schema_id = ensure_schema(
        employer,
        EMPLOYMENT_SCHEMA,
    )

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
        state,
        "government_tenant",
        government,
        tenant,
        "government-tenant",
    )
    save_state(state)

    state["employer_tenant"] = ensure_connection(
        state,
        "employer_tenant",
        employer,
        tenant,
        "employer-tenant",
    )
    save_state(state)

    state["landlord_tenant"] = ensure_connection(
        state,
        "landlord_tenant",
        landlord,
        tenant,
        "landlord-tenant",
    )
    save_state(state)

    print("Connections ready.")
    print("SSI setup completed.")


if __name__ == "__main__":
    bootstrap()
