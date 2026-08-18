import pytest
from dotenv import dotenv_values

from scripts import environment


def use_temp_files(tmp_path):
    environment.ENV_EXAMPLE_FILE = tmp_path / ".env.example"
    environment.ENV_FILE = tmp_path / ".env"


def write_example(path, value):
    lines = []
    for key in environment.REQUIRED_KEYS:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


def test_fills_missing_keys(tmp_path):
    use_temp_files(tmp_path)
    write_example(environment.ENV_EXAMPLE_FILE, "x")
    environment.ENV_FILE.write_text("")

    environment._fill_missing_values()

    content = environment.ENV_FILE.read_text()
    for key in environment.REQUIRED_KEYS:
        assert f"{key}=x" in content


def test_keeps_existing_value(tmp_path):
    use_temp_files(tmp_path)
    write_example(environment.ENV_EXAMPLE_FILE, "default")
    first_key = environment.REQUIRED_KEYS[0]
    environment.ENV_FILE.write_text(f"{first_key}=custom\n")

    environment._fill_missing_values()

    values = dotenv_values(environment.ENV_FILE)
    assert values[first_key] == "custom"


def test_exits_when_missing(tmp_path):
    use_temp_files(tmp_path)
    environment.ENV_EXAMPLE_FILE.write_text("")
    environment.ENV_FILE.write_text("")

    with pytest.raises(SystemExit):
        environment._fill_missing_values()
