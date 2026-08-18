from scripts import state_store


def test_load_missing_file_returns_empty_dict(tmp_path):
    state_store.STATE_FILE = tmp_path / "state.json"
    assert state_store.load_state() == {}


def test_save_and_load_round_trip(tmp_path):
    state_store.STATE_FILE = tmp_path / "state.json"
    state_store.save_state({"government_cred_def_id": "cd-1"})
    assert state_store.load_state() == {"government_cred_def_id": "cd-1"}


def test_save_creates_runtime_directory(tmp_path):
    state_store.STATE_FILE = tmp_path / "runtime" / "state.json"
    state_store.save_state({"a": 1})
    assert state_store.STATE_FILE.exists()


def test_save_overwrites_old_content(tmp_path):
    state_store.STATE_FILE = tmp_path / "state.json"
    state_store.save_state({"a": 1})
    state_store.save_state({"b": 2})
    assert state_store.load_state() == {"b": 2}
