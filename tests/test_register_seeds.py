import requests
import pytest

import aca_client
from scripts import register_seeds


class FakeResponse:
    def __init__(self, ok=True, status_code=200, text=""):
        self.ok = ok
        self.status_code = status_code
        self.text = text


def use_response(response):
    def fake_post(*args, **kwargs):
        return response

    register_seeds.requests.post = fake_post


def test_seed_registers_when_ok():
    use_response(FakeResponse(ok=True))
    register_seeds.register_seed("Government", "seed-1")


def test_seed_registers_when_already_done():
    use_response(FakeResponse(ok=False, status_code=400, text="DID already on ledger"))
    register_seeds.register_seed("Government", "seed-1")


def test_seed_raises_on_timeout():
    register_seeds.WAIT_SECONDS = 0.05
    register_seeds.CHECK_INTERVAL = 0.01
    use_response(FakeResponse(ok=False, status_code=500, text="nope"))

    with pytest.raises(aca_client.ACAClientError):
        register_seeds.register_seed("Government", "seed-1")
