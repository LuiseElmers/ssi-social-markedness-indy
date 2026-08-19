import pytest
import config


def test_schema_with_marked_attribute_is_rejected():
    schema = {"name": "Bad", "version": "1.0", "attributes": ["full_name", "gender"]}
    with pytest.raises(ValueError):
        config.check_marked_attributes(schema)


def test_schema_without_marked_attributes_is_accepted():
    schema = {
        "name": "Good",
        "version": "1.0",
        "attributes": ["full_name", "date_of_birth"],
    }
    config.check_marked_attributes(schema)


def test_real_government_id_schema_passes_its_own_check():
    config.check_marked_attributes(config.GOVERNMENT_ID_SCHEMA)


def test_real_employment_schema_passes_its_own_check():
    config.check_marked_attributes(config.EMPLOYMENT_SCHEMA)


def test_each_marked_attribute_is_rejected_on_its_own():
    for attribute in sorted(config.MARKED_ATTRIBUTES):
        schema = {"name": "Probe", "version": "1.0", "attributes": [attribute]}
        with pytest.raises(ValueError):
            config.check_marked_attributes(schema)


def test_out_of_scope_attribute_is_rejected():
    attributes = {"full_name": {"name": "full_name"}}
    with pytest.raises(ValueError):
        config.check_use_case_scope(attributes, {})


def test_out_of_scope_predicate_is_rejected():
    predicates = {"monthly_net_income": {"name": "monthly_net_income_gross"}}
    with pytest.raises(ValueError):
        config.check_use_case_scope({}, predicates)


def test_in_scope_attribute_and_predicate_are_accepted():
    attributes = {"monthly_net_income": {"name": "monthly_net_income"}}
    predicates = {
        "currently_employed": {
            "name": "is_employed",
            "p_type": ">=",
            "p_value": 1,
        }
    }
    config.check_use_case_scope(attributes, predicates)


def test_predicate_only_attribute_cannot_be_revealed():
    attributes = {"date_of_birth": {"name": "date_of_birth"}}
    with pytest.raises(ValueError):
        config.check_disclosure(attributes)


def test_marked_attribute_cannot_be_revealed():
    attributes = {"residency_status": {"name": "residency_status"}}
    with pytest.raises(ValueError):
        config.check_disclosure(attributes)
        

def test_is_employed_cannot_be_revealed():
    attributes = {"is_employed": {"name": "is_employed"}}
    with pytest.raises(ValueError):
        config.check_disclosure(attributes)


def test_allowed_attribute_can_be_revealed():
    attributes = {"monthly_net_income": {"name": "monthly_net_income"}}
    config.check_disclosure(attributes)
