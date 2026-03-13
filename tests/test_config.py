import pytest
import time
import sys
from pathlib import Path
from core.config import ScraperSettings

# ==========================================
# FIXTURE: VIRTUAL FILESYSTEM SETUP
# ==========================================
@pytest.fixture
def mock_filesystem(tmp_path, monkeypatch):
    """
    Mocks Path.home() and initializes the Enterprise Shared Drive directory structure 
    within a temporary directory. This ensures unit tests never overwrite or interact 
    with actual production data files.
    """
    # Force Path.home() to return our temporary test directory
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    # Create the abstracted ETL base directory structure
    base_dir = (tmp_path / "OneDrive - Corporate" / 
                "Enterprise_Data_Integration" / 
                "Automated_Sources")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    return base_dir


# ==========================================
# TEST 1: PATH GENERATION LOGIC
# ==========================================
def test_output_and_archive_paths(mock_filesystem):
    """Validates that ETL output and archive paths are constructed with correct regional subdirectories."""
    settings = ScraperSettings(region_code="REGION_A")
    
    output_path = settings.get_output_file("processed_data.xlsx")
    archive_path = settings.get_archive_file("historical_data.xlsx")
    
    # Assert path components for output
    assert "REGION_A" in str(output_path)
    assert "03_WEB_OUTPUT" in str(output_path)
    assert output_path.name == "processed_data.xlsx"
    
    # Assert path components for archive
    assert "REGION_A" in str(archive_path)
    assert "_ARCHIVE" in str(archive_path)


# ==========================================
# TEST 2: MISSING FILE HANDLING
# ==========================================
def test_get_input_file_exits_if_not_found(mock_filesystem):
    """
    Verifies pipeline resilience: the application should trigger sys.exit(1) 
    and halt gracefully when a required ingestion file is missing.
    """
    settings = ScraperSettings(region_code="REGION_B")
    
    # Expecting SystemExit due to file non-existence in the mocked filesystem
    with pytest.raises(SystemExit) as exc_info:
        settings.get_input_file("missing_ingestion_file.xlsx")
    
    assert exc_info.value.code == 1


# ==========================================
# TEST 3: LATEST FILE DETECTION
# ==========================================
def test_get_newest_input_file(mock_filesystem):
    """Tests the logic for identifying the most recently modified extraction queue."""
    settings = ScraperSettings(region_code="REGION_C")
    
    # Set up region-specific input directory
    input_dir = mock_filesystem / "REGION_C" / "01_WEB_INPUT"
    input_dir.mkdir(parents=True)
    
    # Create an older file
    old_file = input_dir / "old_queue.xlsx"
    old_file.write_text("historical queue data")
    
    # Small delay to ensure distinct OS modification timestamps
    time.sleep(0.1) 
    
    # Create a newer file
    new_file = input_dir / "latest_queue.xlsx"
    new_file.write_text("current queue data")
    
    # Execute detection
    result = settings.get_newest_input_file()
    
    # Verify the most recent file was returned
    assert result == new_file
    assert result.name == "latest_queue.xlsx"