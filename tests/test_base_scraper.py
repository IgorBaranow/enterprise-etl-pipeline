import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.config import ScraperSettings
from core.base_scraper import BaseScraper

# ==========================================
# FIXTURES
# ==========================================
@pytest.fixture
def base_scraper(monkeypatch, tmp_path):
    """
    Fixture to initialize the BaseScraper with an isolated temporary directory.
    Overrides the home directory to prevent tests from modifying actual user data.
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    # Abstracted region code for testing environment (Synchronized with global config)
    settings = ScraperSettings(region_code="REGION_TEST")
    return BaseScraper(settings, "TEST_ETL_PIPELINE")

# ==========================================
# TEST CASES
# ==========================================
def test_run_raises_not_implemented(base_scraper):
    """
    Ensures the base class enforces the implementation of the run() method
    in all child pipeline classes.
    """
    # Act & Assert
    with pytest.raises(NotImplementedError) as exc_info:
        base_scraper.run()
    
    assert "must be overridden" in str(exc_info.value)

def test_read_input_data_exits_on_error(base_scraper, monkeypatch):
    """
    Validates that the pipeline aborts gracefully (SystemExit) rather than
    crashing unpredictably when the input data source is missing or corrupted.
    """
    # Arrange: Force the settings to return a non-existent file path
    monkeypatch.setattr(ScraperSettings, "get_input_file", lambda self, x: Path("non_existent_dummy_file.xlsx"))
    
    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        base_scraper.read_input_data("dummy.xlsx")
        
    assert exc_info.value.code == 1

@patch("core.base_scraper.sync_playwright")
def test_browser_lifecycle_without_profile(mock_sync_playwright, base_scraper):
    """
    Tests the full lifecycle of the headless browser engine (Playwright).
    Uses MagicMock to verify that start, launch, and close methods are called
    correctly without actually spinning up a real browser during CI/CD tests.
    """
    # Arrange: Set up the Playwright mock chain
    mock_pw_instance = MagicMock()
    mock_sync_playwright.return_value.start.return_value = mock_pw_instance
    
    # Act: Initialize the browser
    base_scraper.start_browser()
    
    # Assert: Verify initialization calls and state
    mock_pw_instance.chromium.launch.assert_called_once()
    assert base_scraper.browser is not None
    assert base_scraper.context is not None
    assert base_scraper.page is not None
    
    # Act: Tear down the browser
    base_scraper.close_browser()
    
    # Assert: Verify teardown calls to prevent memory leaks
    base_scraper.context.close.assert_called_once()
    base_scraper.browser.close.assert_called_once()
    mock_pw_instance.stop.assert_called_once()