from datetime import date

import pytest

import aca_client
from scripts import workflows


class FakeTenant:
    """Replaces ACAClient in tests, knows only wallet_credentials()."""

    def __init__(self, credentials):
        self.credentials = credentials

    def wallet_credentials(self):
        return self.credentials


def contains_text(problems, text):
    for problem in problems:
        if text in problem.lower():
            return True
    return False


def test_today_as_int_matches_the_real_date():
    expected = int(date.today().strftime("%Y%m%d"))
    assert workflows.today_as_int() == expected


def test_legal_age_cutoff_is_18_years_before_today():
    cutoff_year = int(str(workflows.legal_age_cutoff())[0:4])
    assert cutoff_year == date.today().year - 18


def test_format_date_converts_yyyymmdd_to_iso():
    assert workflows.format_date("19950514") == "1995-05-14"


def test_format_date_leaves_non_date_values_untouched():
    assert workflows.format_date("permanent") == "permanent"


def test_get_value_returns_present_field():
    assert workflows.get_value({"thread_id": "t1"}, "thread_id") == "t1"


def test_get_value_raises_when_field_is_missing():
    with pytest.raises(aca_client.ACAClientError):
        workflows.get_value({}, "thread_id")


def test_require_connection_raises_when_missing():
    with pytest.raises(aca_client.ACAClientError):
        workflows.require_connection({}, "landlord_tenant", "Landlord")


def test_require_connection_returns_cached_entry():
    state = {"landlord_tenant": {"issuer": "conn-1", "tenant": "conn-2"}}
    connection = workflows.require_connection(state, "landlord_tenant", "Landlord")
    assert connection["issuer"] == "conn-1"


def test_require_cred_def_raises_when_missing():
    with pytest.raises(aca_client.ACAClientError):
        workflows.require_cred_def({}, "employment_cred_def_id", "Employer")


def test_require_cred_def_returns_cached_id():
    state = {"employment_cred_def_id": "cd-1"}
    cred_def_id = workflows.require_cred_def(
        state, "employment_cred_def_id", "Employer"
    )
    assert cred_def_id == "cd-1"


def test_credential_label_resolves_known_schema():
    state = {"government_schema_id": "did:2:GovernmentID:1.3"}
    title, issuer = workflows.credential_label(state, "did:2:GovernmentID:1.3")
    assert title == "Digital ID"
    assert issuer == "Government Agency"


def test_credential_label_falls_back_for_unknown_schema():
    title, issuer = workflows.credential_label({}, "some-old-schema-id")
    assert title == "Unknown credential"
    assert issuer == "Unknown issuer"


def test_find_credential_by_cred_def_returns_matching_credential():
    tenant = FakeTenant(
        [
            {
                "cred_info": {
                    "cred_def_id": "cd-1",
                    "attrs": {"employment_status": "permanent"},
                }
            }
        ]
    )
    info = workflows.find_credential_by_cred_def(tenant, "cd-1")
    assert info["attrs"]["employment_status"] == "permanent"


def test_find_credential_by_cred_def_returns_none_when_absent():
    tenant = FakeTenant([])
    assert workflows.find_credential_by_cred_def(tenant, "cd-1") is None


def test_has_credential_true_and_false():
    tenant = FakeTenant([{"cred_info": {"cred_def_id": "cd-1"}}])
    assert workflows.has_credential(tenant, "cd-1") is True
    assert workflows.has_credential(tenant, "cd-2") is False


def test_landlord_proof_criteria_only_reveals_employment_status():
    attributes, predicates = workflows.landlord_proof_criteria("emp-cd", "gov-cd")
    assert list(attributes.keys()) == ["employment_status"]


def test_landlord_proof_criteria_contains_all_three_predicates():
    attributes, predicates = workflows.landlord_proof_criteria("emp-cd", "gov-cd")
    assert "income_at_least_2500" in predicates
    assert "of_legal_age" in predicates
    assert "id_not_expired" in predicates


def test_landlord_proof_criteria_restricts_predicates_to_the_right_cred_def():
    attributes, predicates = workflows.landlord_proof_criteria("emp-cd", "gov-cd")
    assert predicates["income_at_least_2500"]["restrictions"] == [
        {"cred_def_id": "emp-cd"}
    ]
    assert predicates["of_legal_age"]["restrictions"] == [{"cred_def_id": "gov-cd"}]
    assert predicates["id_not_expired"]["restrictions"] == [{"cred_def_id": "gov-cd"}]


def test_landlord_decision_wording_stays_generic_on_accept():
    message = workflows.landlord_decision(True)
    assert "income" not in message.lower()
    assert "age" not in message.lower()
    assert "accepted" in message.lower()


def test_landlord_decision_wording_stays_generic_on_reject():
    message = workflows.landlord_decision(False)
    assert "income" not in message.lower()
    assert "age" not in message.lower()
    assert "accepted" in message.lower()


def test_eligibility_reports_both_credentials_missing():
    problems = workflows.check_proof_eligibility(None, None)
    assert len(problems) == 2


def test_eligibility_flags_income_below_threshold():
    employment_info = {"attrs": {"monthly_net_income": "1000"}}
    government_info = {
        "attrs": {
            "date_of_birth": str(workflows.legal_age_cutoff() - 10000),
            "expiry_date": str(workflows.today_as_int() + 10000),
        }
    }
    problems = workflows.check_proof_eligibility(employment_info, government_info)
    assert contains_text(problems, "income")


def test_eligibility_flags_underage_applicant():
    employment_info = {"attrs": {"monthly_net_income": "3200"}}
    government_info = {
        "attrs": {
            "date_of_birth": str(workflows.today_as_int()),
            "expiry_date": str(workflows.today_as_int() + 10000),
        }
    }
    problems = workflows.check_proof_eligibility(employment_info, government_info)
    assert contains_text(problems, "legal age")


def test_eligibility_flags_expired_id():
    employment_info = {"attrs": {"monthly_net_income": "3200"}}
    government_info = {
        "attrs": {
            "date_of_birth": str(workflows.legal_age_cutoff() - 10000),
            "expiry_date": "20000101",
        }
    }
    problems = workflows.check_proof_eligibility(employment_info, government_info)
    assert contains_text(problems, "expired")


def test_eligibility_passes_with_no_problems():
    employment_info = {"attrs": {"monthly_net_income": "3200"}}
    government_info = {
        "attrs": {
            "date_of_birth": str(workflows.legal_age_cutoff() - 10000),
            "expiry_date": str(workflows.today_as_int() + 10000),
        }
    }
    problems = workflows.check_proof_eligibility(employment_info, government_info)
    assert problems == []


def test_eligibility_income_exactly_at_threshold_is_not_a_problem():
    employment_info = {"attrs": {"monthly_net_income": "2500"}}
    government_info = {
        "attrs": {
            "date_of_birth": str(workflows.legal_age_cutoff() - 10000),
            "expiry_date": str(workflows.today_as_int() + 10000),
        }
    }
    problems = workflows.check_proof_eligibility(employment_info, government_info)
    assert problems == []
