import pytest

import aca_client

from scripts import bootstrap


class FakeClient:
    def __init__(self):
        self.did = "did:test:government"
        self.schemas = {}
        self.cred_defs = {}
        self.cred_def_ids = []
        self.blocked_tags = set()

    def get_public_did(self):
        return self.did

    def fetch_schema(self, schema_id):
        return self.schemas.get(schema_id)

    def create_schema(self, public_did, schema):
        schema_id = f"{public_did}:2:{schema['name']}:{schema['version']}"
        self.schemas[schema_id] = {"attrNames": schema["attributes"]}
        return {"schema_state": {"schema_id": schema_id}}

    def created_credential_definitions(self):
        return self.cred_def_ids

    def fetch_credential_definition(self, cred_def_id):
        return self.cred_defs.get(cred_def_id)

    def create_credential_definition(self, public_did, schema_id, tag):
        if tag in self.blocked_tags:
            raise aca_client.ACAClientError(f"tag {tag} already taken")
        cred_def_id = f"{public_did}:3:CL:{tag}"
        self.cred_defs[cred_def_id] = {"schemaId": schema_id}
        self.cred_def_ids.append(cred_def_id)
        return {
            "credential_definition_state": {"credential_definition_id": cred_def_id}
        }


class FakeParty:
    def __init__(self, usable_ids=None, alias_id=None):
        self.usable_ids = usable_ids or set()
        self.alias_id = alias_id

    def connection_is_usable(self, connection_id):
        return connection_id in self.usable_ids

    def find_usable_connection_by_alias(self, alias):
        return self.alias_id


def fail_if_called(*args, **kwargs):
    raise AssertionError("connect() should not have been called here")


TEST_SCHEMA = {"name": "Test", "version": "1.0", "attributes": ["a", "b"]}


def test_ensure_schema_creates_new_schema():
    client = FakeClient()
    schema_id = bootstrap.ensure_schema(client, TEST_SCHEMA)
    assert schema_id in client.schemas


def test_ensure_schema_reuses_matching_schema():
    client = FakeClient()
    first_id = bootstrap.ensure_schema(client, TEST_SCHEMA)
    second_id = bootstrap.ensure_schema(client, TEST_SCHEMA)
    assert second_id == first_id


def test_ensure_schema_raises_on_attribute_mismatch():
    client = FakeClient()
    schema_id = f"{client.did}:2:Test:1.0"
    client.schemas[schema_id] = {"attrNames": ["different_attribute"]}

    with pytest.raises(aca_client.ACAClientError):
        bootstrap.ensure_schema(client, TEST_SCHEMA)


def test_ensure_cred_def_reuses_cached_id():
    client = FakeClient()
    client.cred_def_ids.append("cached-id")

    cred_def_id = bootstrap.ensure_credential_definition(
        client, "schema-1", cached_id="cached-id"
    )
    assert cred_def_id == "cached-id"


def test_ensure_cred_def_finds_existing_match():
    client = FakeClient()
    client.cred_defs["existing-id"] = {"schemaId": "schema-1"}
    client.cred_def_ids.append("existing-id")

    cred_def_id = bootstrap.ensure_credential_definition(
        client, "schema-1", cached_id=None
    )
    assert cred_def_id == "existing-id"


def test_ensure_cred_def_creates_new_one():
    client = FakeClient()
    cred_def_id = bootstrap.ensure_credential_definition(
        client, "schema-1", cached_id=None
    )
    assert cred_def_id in client.cred_defs


def test_create_cred_def_retries_with_new_tag_when_blocked():
    client = FakeClient()
    client.blocked_tags.add("default")

    cred_def_id = bootstrap.create_cred_def(client, client.did, "schema-1", "default")
    assert cred_def_id in client.cred_defs
    assert "default-2" in cred_def_id


def test_ensure_connection_reuses_cached_entry():
    issuer = FakeParty(usable_ids={"conn-issuer"})
    tenant = FakeParty(usable_ids={"conn-tenant"})
    state = {"government_tenant": {"issuer": "conn-issuer", "tenant": "conn-tenant"}}
    bootstrap.connect = fail_if_called

    connection = bootstrap.ensure_connection(
        state, "government_tenant", issuer, tenant, "government-tenant"
    )
    assert connection == {"issuer": "conn-issuer", "tenant": "conn-tenant"}


def test_ensure_connection_finds_connection_by_alias():
    issuer = FakeParty(alias_id="conn-issuer-2")
    tenant = FakeParty(alias_id="conn-tenant-2")
    bootstrap.connect = fail_if_called

    connection = bootstrap.ensure_connection(
        {}, "government_tenant", issuer, tenant, "government-tenant"
    )
    assert connection == {"issuer": "conn-issuer-2", "tenant": "conn-tenant-2"}


def test_ensure_connection_creates_new_connection_as_last_resort():
    issuer = FakeParty()
    tenant = FakeParty()

    def fake_connect(issuer_arg, tenant_arg, name):
        return {"issuer": "new-issuer", "tenant": "new-tenant"}

    bootstrap.connect = fake_connect

    connection = bootstrap.ensure_connection(
        {}, "government_tenant", issuer, tenant, "government-tenant"
    )
    assert connection == {"issuer": "new-issuer", "tenant": "new-tenant"}
