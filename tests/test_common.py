import pytest

from scripts import common


def use_temp_files(tmp_path):
    common.ENV_FILE = tmp_path / ".env"
    common.ENV_EXAMPLE_FILE = tmp_path / ".env.example"


def test_creates_env(tmp_path):
    use_temp_files(tmp_path)
    common.ENV_EXAMPLE_FILE.write_text("KEY=value\n")

    common.ensure_env_file()

    assert common.ENV_FILE.read_text() == "KEY=value\n"


def test_keeps_existing_env(tmp_path):
    use_temp_files(tmp_path)
    common.ENV_FILE.write_text("KEY=custom\n")

    common.ensure_env_file()

    assert common.ENV_FILE.read_text() == "KEY=custom\n"


def test_exits_without_example(tmp_path):
    use_temp_files(tmp_path)

    with pytest.raises(SystemExit):
        common.ensure_env_file()
