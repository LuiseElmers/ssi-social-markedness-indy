"""SSI workflows used by the console menu."""

from datetime import date

from aca_client import ACAClient, ACAClientError
from config import (
    EMPLOYER_URL,
    GOVERNMENT_URL,
    LANDLORD_URL,
    TENANT_URL,
    assert_request_does_not_reveal_marked_attributes,
    assert_request_is_use_case_appropriate,
)
from scripts.state_store import load_state, save_state

CREDENTIAL_LABELS = {
    "government_schema_id": ("Digital ID", "Government Agency"),
    "employment_schema_id": ("Employment", "Employer"),
}

ATTRIBUTE_LABELS = {
    "full_name": "Full Name",
    "date_of_birth": "Date of Birth",
    "expiry_date": "Expiry Date",
    "employer_name": "Employer",
    "employment_status": "Employment Status",
    "monthly_net_income": "Monthly Net Income",
    "employed_since": "Employed Since",
}

# Human-readable descriptions for predicates
PREDICATE_DESCRIPTIONS = {
    "income_at_least_2500": "Monthly Net Income >= 2500",
    "of_legal_age": "Is of legal age (18+)",
    "id_not_expired": "Digital ID is still valid",
}


def get_value(response, name):
    if response.get(name):
        return response[name]
    raise ACAClientError(f"ACA-Py response does not contain '{name}'.")


def require_connection(state, key, party):
    connection = state.get(key)
    if not connection or not connection.get("issuer"):
        raise ACAClientError(
            f"No connection to the {party} exists yet. Restart the application."
        )
    return connection


def require_cred_def(state, key, party):
    cred_def_id = state.get(key)
    if not cred_def_id:
        raise ACAClientError(
            f"The {party} credential definition is missing. Restart the application."
        )

    return cred_def_id


def today_as_int():
    return int(date.today().strftime("%Y%m%d"))


def legal_age_cutoff():
    today = date.today()
    try:
        cutoff = today.replace(year=today.year - 18)
    except ValueError:
        # For leap year
        cutoff = today.replace(year=today.year - 18, day=28)
    return int(cutoff.strftime("%Y%m%d"))


def format_date_for_display(value):
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    return value


def find_credential_by_cred_def(tenant, cred_def_id):
    for credential in tenant.wallet_credentials():
        info = credential.get("cred_info", credential)
        if info.get("cred_def_id") == cred_def_id:
            return info
    return None


def has_credential(tenant, cred_def_id):
    return find_credential_by_cred_def(tenant, cred_def_id) is not None


def issue_credential(
    issuer, tenant, connection_id, cred_def_id, attributes, description
):
    offer = issuer.send_credential_offer(
        connection_id, cred_def_id, attributes, description
    )
    issuer_record_id = get_value(offer, "cred_ex_id")
    thread_id = get_value(offer, "thread_id")
    tenant_offer = tenant.wait_for_record(
        tenant.credential_records, thread_id, "offer-received"
    )
    tenant.send_credential_request(get_value(tenant_offer, "cred_ex_id"))
    issuer.wait_for_record(issuer.credential_records, thread_id, "request-received")
    issuer.issue_credential(issuer_record_id)
    tenant_credential = tenant.wait_for_record(
        tenant.credential_records, thread_id, "credential-received"
    )
    tenant.store_credential(get_value(tenant_credential, "cred_ex_id"))
    print(f"\nCredential issued: {description}")


def credential_label(state, schema_id):
    for state_key, label in CREDENTIAL_LABELS.items():
        if schema_id and schema_id == state.get(state_key):
            return label

    return "Unknown credential", "Unknown issuer"


def check_wallet():
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
            print(f"    {label}: {format_date_for_display(value)}")


def issue_employment_credential():
    state = load_state()
    connection = require_connection(state, "employer_tenant", "Employer")
    cred_def_id = require_cred_def(state, "employment_cred_def_id", "Employer")
    tenant = ACAClient("Tenant", TENANT_URL)

    if has_credential(tenant, cred_def_id):
        print("\nAn Employment credential has already been issued to the Tenant.")
        return

    issue_credential(
        ACAClient("Employer", EMPLOYER_URL),
        tenant,
        connection["issuer"],
        cred_def_id,
        {
            "employer_name": "Example GmbH",
            "employment_status": "permanent",
            "monthly_net_income": "3200",
            "employed_since": "2023-01-01",
        },
        "Employment credential",
    )


def issue_government_id():
    state = load_state()
    connection = require_connection(state, "government_tenant", "Government")
    cred_def_id = require_cred_def(state, "government_cred_def_id", "Government")
    tenant = ACAClient("Tenant", TENANT_URL)

    if has_credential(tenant, cred_def_id):
        print("\nA Digital ID credential has already been issued to the Tenant.")
        return

    issue_credential(
        ACAClient("Government", GOVERNMENT_URL),
        tenant,
        connection["issuer"],
        cred_def_id,
        {
            "full_name": "Jane Doe",
            "date_of_birth": "19950514",
            "expiry_date": "20300101",
        },
        "Digital ID credential",
    )


def landlord_proof_criteria(employment_cred_def_id, government_cred_def_id):
    employment_restriction = [{"cred_def_id": employment_cred_def_id}]
    government_restriction = [{"cred_def_id": government_cred_def_id}]

    attributes = {
        "employment_status": {
            "name": "employment_status",
            "restrictions": employment_restriction,
        },
    }
    predicates = {
        "income_at_least_2500": {
            "name": "monthly_net_income",
            "p_type": ">=",
            "p_value": 2500,
            "restrictions": employment_restriction,
        },
        "of_legal_age": {
            "name": "date_of_birth",
            "p_type": "<=",
            "p_value": legal_age_cutoff(),
            "restrictions": government_restriction,
        },
        "id_not_expired": {
            "name": "expiry_date",
            "p_type": ">=",
            "p_value": today_as_int(),
            "restrictions": government_restriction,
        },
    }

    assert_request_is_use_case_appropriate(attributes, predicates)
    assert_request_does_not_reveal_marked_attributes(attributes)
    return attributes, predicates


def print_request_labels(attributes, predicates):
    print("\nAttributes that will be revealed to the Landlord:")
    for attribute in attributes.values():
        label = ATTRIBUTE_LABELS.get(attribute["name"], attribute["name"])
        print(f"  - {label}")

    print("\nPredicates that will be proven, but not revealed as an exact value:")
    for key, predicate in predicates.items():
        description = PREDICATE_DESCRIPTIONS.get(key, predicate["name"])
        print(f"  - {description}")


def print_disclosure_preview(attributes, predicates, attrs):
    print("\nAttributes that will be revealed to the Landlord:")
    for attribute in attributes.values():
        label = ATTRIBUTE_LABELS.get(attribute["name"], attribute["name"])
        value = format_date_for_display(attrs.get(attribute["name"], "not available"))
        print(f"  - {label}: {value}")

    print("\nPredicates that will be proven, but not revealed as an exact value:")
    for key, predicate in predicates.items():
        description = PREDICATE_DESCRIPTIONS.get(key, predicate["name"])
        value = format_date_for_display(attrs.get(predicate["name"], "not available"))
        print(f"  - {description} (your value: {value}, not disclosed)")


def show_landlord_proof_request():
    state = load_state()
    employment_cred_def_id = require_cred_def(
        state, "employment_cred_def_id", "Employer"
    )
    government_cred_def_id = require_cred_def(
        state, "government_cred_def_id", "Government"
    )
    attributes, predicates = landlord_proof_criteria(
        employment_cred_def_id, government_cred_def_id
    )

    print("\nLANDLORD'S PROOF REQUEST")
    print_request_labels(attributes, predicates)


def check_proof_eligibility(employment_info, government_info):

    problems = []

    if not employment_info:
        problems.append("No Employment credential yet -- request one first.")
    if not government_info:
        problems.append("No Digital ID credential yet -- request one first.")

    if employment_info:
        income = int(employment_info["attrs"].get("monthly_net_income", 0))
        if income < 2500:
            problems.append(f"Monthly net income is {income}, below the required 2500.")

    if government_info:
        birth_date = int(government_info["attrs"].get("date_of_birth", 0))
        if birth_date > legal_age_cutoff():
            problems.append("Not yet of legal age (18+).")
        expiry_date = int(government_info["attrs"].get("expiry_date", 0))
        if expiry_date < today_as_int():
            problems.append("Digital ID has expired.")

    return problems


def landlord_decision(verified):
    if verified:
        message = (
            "Application accepted. All required criteria were proven and verified."
        )
    else:
        message = "Application not accepted. The proof could not be verified against the required criteria."

    print(f"\nDecision: {message}")
    return message


def generate_proof():
    state = load_state()
    landlord = ACAClient("Landlord", LANDLORD_URL)
    tenant = ACAClient("Tenant", TENANT_URL)
    connection = require_connection(state, "landlord_tenant", "Landlord")
    employment_cred_def_id = require_cred_def(
        state, "employment_cred_def_id", "Employer"
    )
    government_cred_def_id = require_cred_def(
        state, "government_cred_def_id", "Government"
    )
    attributes, predicates = landlord_proof_criteria(
        employment_cred_def_id, government_cred_def_id
    )

    employment_info = find_credential_by_cred_def(tenant, employment_cred_def_id)
    government_info = find_credential_by_cred_def(tenant, government_cred_def_id)

    problems = check_proof_eligibility(employment_info, government_info)
    if problems:
        print("\nThis proof cannot be sent yet:")
        for problem in problems:
            print(f"  - {problem}")
        return

    submitted = state.get("rental_proof_submission")
    if submitted:
        print("\nA rental proof was already submitted to the Landlord:")
        print_disclosure_preview(
            submitted["attributes"], submitted["predicates"], submitted["attrs"]
        )
        return

    attrs = {}
    attrs.update(employment_info.get("attrs", {}))
    attrs.update(government_info.get("attrs", {}))

    print("\nThe following will be sent to the Landlord:")
    print_disclosure_preview(attributes, predicates, attrs)
    confirm = input("\nSend this proof? [Y/N]: ").strip().upper()

    if confirm != "Y":
        print("\nCancelled. Nothing was sent.")
        return

    request = landlord.send_proof_request(connection["issuer"], attributes, predicates)
    landlord_record_id = get_value(request, "pres_ex_id")
    thread_id = get_value(request, "thread_id")
    tenant_request = tenant.wait_for_record(
        tenant.proof_records, thread_id, "request-received"
    )
    tenant_record_id = tenant_request["pres_ex_id"]

    employment = tenant.proof_credentials(tenant_record_id, "employment_status")
    income = tenant.proof_credentials(tenant_record_id, "income_at_least_2500")
    legal_age = tenant.proof_credentials(tenant_record_id, "of_legal_age")
    id_valid = tenant.proof_credentials(tenant_record_id, "id_not_expired")

    if not employment or not income or not legal_age or not id_valid:
        raise ACAClientError(
            "The tenant does not have all the credentials needed for this proof."
        )

    tenant.send_presentation(
        tenant_record_id,
        {
            "self_attested_attributes": {},
            "requested_attributes": {
                "employment_status": {
                    "cred_id": employment[0]["cred_info"]["referent"],
                    "revealed": True,
                },
            },
            "requested_predicates": {
                "income_at_least_2500": {"cred_id": income[0]["cred_info"]["referent"]},
                "of_legal_age": {"cred_id": legal_age[0]["cred_info"]["referent"]},
                "id_not_expired": {"cred_id": id_valid[0]["cred_info"]["referent"]},
            },
        },
    )
    landlord.wait_for_record(landlord.proof_records, thread_id, "presentation-received")
    result = landlord.verify_presentation(landlord_record_id)
    decision_message = landlord_decision(result.get("verified") in (True, "true"))
    landlord.send_basic_message(connection["issuer"], decision_message)

    state["rental_proof_submission"] = {
        "attributes": attributes,
        "predicates": predicates,
        "attrs": attrs,
    }
    save_state(state)
