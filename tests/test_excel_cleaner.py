import pytest
import pandas as pd
from core.config import ScraperSettings
from core.excel_cleaner import ExcelCleaner

# ==========================================
# FIXTURE: INITIALIZE TEST CLEANER
# ==========================================
@pytest.fixture
def cleaner(monkeypatch, tmp_path):
    """
    Sets up a sandboxed environment and initializes the Data Transformation utility (ExcelCleaner)
    with isolated settings for a mock region.
    """
    # Mock Path.home to strictly prevent tests from touching actual corporate network drives
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    
    # FIXED: Aligned with the Pydantic model requirement (region_code)
    settings = ScraperSettings(region_code="REGION_TEST")
    return ExcelCleaner(settings, target_folder_name="DUMMY_INGESTION", target_sheet_name="Sheet1")

# ==========================================
# TEST 1: SUCCESSFUL HEADER DETECTION & NOISE REDUCTION
# ==========================================
def test_find_header_and_fix_success(cleaner):
    """
    Tests the ETL transformation logic for identifying the 'Keyword_X' anchor keyword 
    in a highly noisy dataset. Verifies proper data slicing and column reassignment.
    """
    # Arrange: Simulate raw legacy system data with garbage metadata rows before the actual table
    raw_data = {
        0: ["Report generated on 2026-03-09", "Empty Info", "Keyword_X", "ALPHA1234567", "BETA7654321"],
        1: ["Confidential Data", "", "Lifecycle_Status", "Processed", "Dispatched"]
    }
    df = pd.DataFrame(raw_data)

    # Act: Pass the dirty dataframe through the cleaner's transformation engine
    cleaned_df = cleaner.find_header_and_fix(df)

    # Assert: Verify noise removal and correct header mapping
    assert cleaned_df is not None
    assert "Keyword_X" in cleaned_df.columns
    assert "Lifecycle_Status" in cleaned_df.columns
    
    # Verify the resulting dataframe successfully dropped the 2 garbage rows
    assert len(cleaned_df) == 2
    
    # Validate a specific cell value to ensure index alignment wasn't corrupted during slicing
    assert cleaned_df.iloc[0]["Keyword_X"] == "ALPHA1234567"

# ==========================================
# TEST 2: MISSING KEYWORD PROTECTION (FAULT TOLERANCE)
# ==========================================
def test_find_header_and_fix_no_target_keyword(cleaner):
    """
    Ensures the cleaner gracefully aborts (returns None) if the anchor keyword ('Keyword_X') 
    is missing. This fault-tolerance prevents overwriting master databases with malformed data.
    """
    # Arrange: Create a dataset lacking the required header identifier
    raw_data = {
        0: ["Generic Header", "Data 1", "Data 2"],
        1: ["Another Header", "Info 1", "Info 2"]
    }
    df = pd.DataFrame(raw_data)

    # Act
    cleaned_df = cleaner.find_header_and_fix(df)

    # Assert: Expect None to trigger a safe skip in the downstream file-saving pipeline
    assert cleaned_df is None