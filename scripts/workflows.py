"""SSI workflows used by the console menu."""

from aca_client import ACAClient, ACAClientError
from config import EMPLOYER_URL, GOVERNMENT_URL, LANDLORD_URL, TENANT_URL
from scripts.state_store import load_state


# Human-readable labels for the two credential types, keyed by the
# state.json field that stores their schema_id. Falls back to "Unknown"
# for anything not in state.json (e.g. a leftover credential from an
# older schema version).
CREDENTIAL_LABELS = {
    "government_schema_id": ("Government ID", "Government"),
    "employment_schema_id": ("Employment", "Employer"),
}

# Friendly names for the raw attribute names as they come back from the
# wallet, so the demo doesn't show snake_case field names.
ATTRIBUTE_LABELS = {
    "full_name": "Full Name",
    "date_of_birth": "Date of Birth",
    "residency_status": "Residency Status",
    "employer_name": "Employer",
    "employment_status": "Employment Status",
    "monthly_net_income": "Monthly Net Income",
}


def get_value(response, name):
    if response.get(name):
        return response[name]
    raise ACAClientError(f"ACA-Py response does not contain '{name}'.")


def get_state():
    state = load_state()
    required = ["government_cred_def_id", "employment_cred_def_id", "government_tenant", "employer_tenant", "landlord_tenant"]
    for item in required:
        if item not in state:
            raise ACAClientError("Initial setup is missing. Restart the program and run setup first.")
    return state


def issue_credential(issuer, tenant, connection_id, cred_def_id, attributes, description):
    """Run offer, request, issue and store as separate ACA-Py steps."""
    offer = issuer.send_credential_offer(connection_id, cred_def_id, attributes, description)
    issuer_record_id = get_value(offer, "cred_ex_id")
    thread_id = get_value(offer, "thread_id")
    tenant_offer = tenant.wait_for_record(tenant.credential_records, thread_id, "offer-received")
    tenant.send_credential_request(get_value(tenant_offer, "cred_ex_id"))
    issuer.wait_for_record(issuer.credential_records, thread_id, "request-received")
    issuer.issue_credential(issuer_record_id)
    tenant_credential = tenant.wait_for_record(tenant.credential_records, thread_id, "credential-received")
    tenant.store_credential(get_value(tenant_credential, "cred_ex_id"))
    print(f"\nCredential issued: {description}")


def credential_label(state, schema_id):
    """Return a (title, issuer) pair for a credential's schema_id.

    Falls back to a generic label if the schema isn't one we recognize
    from state.json (e.g. state.json is missing or the credential is from
    an older schema version).
    """
    for state_key, label in CREDENTIAL_LABELS.items():
        if schema_id and schema_id == state.get(state_key):
            return label

    return "Unknown credential", "Unknown issuer"


def check_wallet():
    """Show the credentials currently stored in the tenant's wallet."""
    state = load_state()
    tenant = ACAClient("Tenant", TENANT_URL)
    credentials = tenant.wallet_credentials()

    print("\n" + "=" * 57)
    print("                     TENANT WALLET")
    print("=" * 57)

    if not credentials:
        print("\nWallet is currently empty.")
        print("No credentials have been issued to the Tenant yet.")
        return

    print("\nCredentials:")

    for number, credential in enumerate(credentials, start=1):
        info = credential.get("cred_info", credential)
        title, issuer = credential_label(state, info.get("schema_id"))

        print(f"\n[{number}] {title}")
        print(f"    Issuer: {issuer}")

        for name, value in info.get("attrs", {}).items():
            label = ATTRIBUTE_LABELS.get(name, name)
            print(f"    {label}: {value}")


def issue_employment_credential():
    state = get_state()
    issue_credential(
        ACAClient("Employer", EMPLOYER_URL), ACAClient("Tenant", TENANT_URL),
        state["employer_tenant"]["issuer"], state["employment_cred_def_id"],
        {"employer_name": "Example GmbH", "employment_status": "permanent", "monthly_net_income": "3200"},
        "Employment credential",
    )


def issue_government_id():
    state = get_state()
    issue_credential(
        ACAClient("Government", GOVERNMENT_URL), ACAClient("Tenant", TENANT_URL),
        state["government_tenant"]["issuer"], state["government_cred_def_id"],
        {"full_name": "Alex Example", "date_of_birth": "1990-01-01", "residency_status": "valid"},
        "Government ID credential",
    )


def show_landlord_proof_request():
    print("\nLANDLORD'S PROOF REQUEST")
    print("The landlord requests:")
    print("  - employment_status: revealed")
    print("  - monthly_net_income >= 2500: proven, but not revealed")
    print("\nThe Government ID, name, date of birth, employer name and exact income")
    print("are not part of this proof request.")


def generate_proof():
    """Create, answer and verify the minimal rental proof."""
    state = get_state()
    landlord = ACAClient("Landlord", LANDLORD_URL)
    tenant = ACAClient("Tenant", TENANT_URL)
    restriction = [{"cred_def_id": state["employment_cred_def_id"]}]
    request = landlord.send_proof_request(
        state["landlord_tenant"]["issuer"],
        {"employment_status": {"name": "employment_status", "restrictions": restriction}},
        {"income_at_least_2500": {"name": "monthly_net_income", "p_type": ">=", "p_value": 2500, "restrictions": restriction}},
    )
    landlord_record_id = get_value(request, "pres_ex_id")
    thread_id = get_value(request, "thread_id")
    tenant_request = tenant.wait_for_record(tenant.proof_records, thread_id, "request-received")
    tenant_record_id = get_value(tenant_request, "pres_ex_id")
    employment = tenant.proof_credentials(tenant_record_id, "employment_status")
    income = tenant.proof_credentials(tenant_record_id, "income_at_least_2500")
    if not employment or not income:
        raise ACAClientError("The tenant has no suitable employment credential.")
    tenant.send_presentation(
        tenant_record_id,
        {
            "self_attested_attributes": {},
            "requested_attributes": {"employment_status": {"cred_id": employment[0]["cred_info"]["referent"], "revealed": True}},
            "requested_predicates": {"income_at_least_2500": {"cred_id": income[0]["cred_info"]["referent"]}},
        },
    )
    landlord.wait_for_record(landlord.proof_records, thread_id, "presentation-received")
    result = landlord.verify_presentation(landlord_record_id)
    if result.get("verified") in (True, "true"):
        print("\nProof verified.")
        print("The landlord receives the employment status and the confirmed income threshold.")
    else:
        print("\nThe landlord could not verify the proof.")
