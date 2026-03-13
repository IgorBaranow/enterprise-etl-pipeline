import pytest
import json
from pathlib import Path
from core.settings_manager import SettingsManager

# ==========================================
# FIXTURE: ISOLATED TEST ENVIRONMENT
# ==========================================
@pytest.fixture
def manager(monkeypatch, tmp_path):
    """
    Mocks Path.home() to point to an ephemeral temporary directory.
    This strictly ensures that local credential vaults (system_secrets.json) 
    are isolated and never overwritten during CI/CD test runs.
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return SettingsManager()

# ==========================================
# TEST 1: INITIALIZATION (FILE NOT FOUND)
# ==========================================
def test_load_secrets_when_file_does_not_exist(manager):
    """
    Verifies that the Vault Manager returns an empty dictionary 
    if the secrets file does not exist yet (first-run scenario/clean environment).
    """
    data = manager._load_secrets()
    assert data == {}

# ==========================================
# TEST 2: DATA PERSISTENCE (SAVE & LOAD)
# ==========================================
def test_save_and_load_secrets(manager):
    """
    Tests the integrity of the save/load cycle for local credentials.
    Ensures data serialization to JSON and correct deserialization back to dict.
    """
    # Arrange: Define mock credential payload for an abstracted endpoint
    fake_data = {
        "https://example-compliance-gateway.com/records": {
            "login": "system_admin@enterprise-corp.com",
            "password": "MockedPassword2026!"
        }
    }
    
    # Act: Persist data to the mocked filesystem and read it back
    manager._save_secrets(fake_data)
    
    # Assert physical file existence in the tmp_path
    assert manager.secret_file.exists()
    
    # Assert data consistency to verify no data loss during I/O
    loaded_data = manager._load_secrets()
    assert loaded_data == fake_data
    assert loaded_data["https://example-compliance-gateway.com/records"]["login"] == "system_admin@enterprise-corp.com"

# ==========================================
# TEST 3: CORRUPTION HANDLING
# ==========================================
def test_load_secrets_with_corrupted_json(manager):
    """
    Validates that the Vault Manager handles malformed JSON files gracefully 
    by returning an empty dictionary instead of crashing the automation pipeline.
    """
    # Arrange: Manually write invalid JSON content to the secret file
    manager.secret_file.write_text("{ corrupted_json: 'missing_closing_brackets")
    
    # Act: Attempt to load the malformed file
    data = manager._load_secrets()
    
    # Assert: Ensure json.JSONDecodeError is intercepted and handled safely
    assert data == {}