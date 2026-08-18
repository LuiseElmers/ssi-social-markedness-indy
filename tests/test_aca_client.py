import requests
import pytest

import aca_client


class FakeResponse:
    def __init__(self, ok=True, status_code=200, content=b"{}", json_value=None):
        self.ok = ok
        self.status_code = status_code
        self.content = content
        self.text = content.decode() if isinstance(content, bytes) else content
        self.json_value = json_value

    def json(self):
        if self.json_value is None:
            raise ValueError("no JSON body")
        return self.json_value


def use_response(response):
    def fake_request(*args, **kwargs):
        return response

    aca_client.requests.request = fake_request


def use_error(error):
    def raise_error(*args, **kwargs):
        raise error

    aca_client.requests.request = raise_error


def use_connection_state(client, state):
    def fake_connection(cid):
        return {"state": state}

    client.connection = fake_connection


def test_get_returns_json():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_response(FakeResponse(content=b'{"ready": true}', json_value={"ready": True}))
    assert client.get("/status") == {"ready": True}


def test_get_raises_on_http_error():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_response(FakeResponse(ok=False, status_code=500, content=b"boom"))
    with pytest.raises(aca_client.ACAClientError):
        client.get("/status")


def test_get_raises_on_timeout():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_error(requests.Timeout())
    with pytest.raises(aca_client.ACATimeoutError):
        client.get("/status")


def test_is_ready_false_when_unreachable():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_error(requests.ConnectionError())
    assert client.is_ready() is False


def test_empty_body_becomes_empty_dict():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_response(FakeResponse(content=b""))
    assert client.post("/present-proof-2.0/records/x/send-presentation") == {}


def test_invalid_json_raises_error():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_response(FakeResponse(content=b"not json"))
    with pytest.raises(aca_client.ACAClientError):
        client.get("/status")


def test_connection_usable_false_without_id():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    assert client.connection_is_usable(None) is False


def test_connection_usable_true_when_active():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_connection_state(client, "active")
    assert client.connection_is_usable("conn-1") is True


def test_connection_usable_false_when_abandoned():
    client = aca_client.ACAClient("Tenant", "http://localhost:9999")
    use_connection_state(client, "abandoned")
    assert client.connection_is_usable("conn-1") is False
