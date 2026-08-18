"""Tests the running prototype, python3 main.py must be started."""

import builtins
import os

import pytest

pytestmark = pytest.mark.integration

RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS") == "1"

if not RUN_INTEGRATION_TESTS:
    pytest.skip(
        "Set RUN_INTEGRATION_TESTS=1 to run this against a live prototype.",
        allow_module_level=True,
    )


from scripts.ledger import ledger_is_ready
from scripts.state_store import load_state
from scripts import workflows
import aca_client


def skip_if_not_running():
    if not ledger_is_ready():
        pytest.skip("von-network is not up. Run 'python3 main.py' first.")

    agent_urls = {
        "Government": workflows.GOVERNMENT_URL,
        "Employer": workflows.EMPLOYER_URL,
        "Tenant": workflows.TENANT_URL,
        "Landlord": workflows.LANDLORD_URL,
    }
    for name, url in agent_urls.items():
        if not aca_client.ACAClient(name, url).is_ready():
            pytest.skip(f"{name} agent is not reachable at {url}.")


def always_yes(prompt=""):
    return "Y"


def test_state_has_required_ids():
    skip_if_not_running()
    state = load_state()

    required_keys = [
        "government_cred_def_id",
        "employment_cred_def_id",
        "government_tenant",
        "employer_tenant",
        "landlord_tenant",
    ]
    for key in required_keys:
        assert key in state


def test_government_id_issued():
    skip_if_not_running()
    workflows.issue_government_id()

    tenant = aca_client.ACAClient("Tenant", workflows.TENANT_URL)
    cred_def_id = load_state()["government_cred_def_id"]
    assert workflows.has_credential(tenant, cred_def_id)


def test_employment_credential_issued():
    skip_if_not_running()
    workflows.issue_employment_credential()

    tenant = aca_client.ACAClient("Tenant", workflows.TENANT_URL)
    cred_def_id = load_state()["employment_cred_def_id"]
    assert workflows.has_credential(tenant, cred_def_id)


def test_proof_can_be_verified():
    skip_if_not_running()
    builtins.input = always_yes

    workflows.generate_proof()

    state = load_state()
    assert "rental_proof_submission" in state


def test_disclosed_attrs_stay_minimal():
    skip_if_not_running()
    state = load_state()
    submission = state.get("rental_proof_submission")

    if submission is None:
        pytest.skip("No proof has been submitted yet in this session.")

    revealed_names = set()
    for attribute in submission["attributes"].values():
        revealed_names.add(attribute["name"])

    assert revealed_names == {"employment_status"}
