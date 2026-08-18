import socket

from scripts import environment


def test_free_port_can_be_bound():
    port = environment.find_free_port(48000)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("0.0.0.0", port))


def test_busy_port_is_skipped():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("0.0.0.0", 48100))
        port = environment.find_free_port(48100)
        assert port != 48100


def test_default_port_is_kept_when_free():
    assert environment.find_free_port(48200) == 48200
