from pydantic import BaseModel
from pathlib import Path
import sys
from core.logger import get_logger 

logger = get_logger("CONFIG")

class ScraperSettings(BaseModel):
    """
    Central configuration class for all extraction modules.
    Manages file paths, environment settings, and region-specific directories.
    Using Pydantic ensures data validation and type safety across the project.
    """
    region_code: str
    input_folder_name: str = "01_WEB_INPUT"
    output_folder_name: str = "03_WEB_OUTPUT"
    archive_folder_name: str = "_ARCHIVE"

    @property
    def base_dir(self) -> Path:
        """
        Defines the root directory for all data files.
        Using a property keeps the code DRY and makes it easy to change the environment 
        (e.g., from local testing to a production server).
        """
        # Abstracted the path
        return Path.home() / "OneDrive - Corporate" / "Enterprise_Data_Integration" / "Automated_Sources"

    def get_input_file(self, filename: str) -> Path:
        """
        Constructs the path for a specific input file and verifies its existence.
        We halt the execution early if the file is missing to prevent downstream pipeline crashes.
        """
        full_path = self.base_dir / self.region_code / self.input_folder_name / filename
        
        if not full_path.exists():
            logger.critical(f"Input file not found. Please verify the path: {full_path}")
            sys.exit(1) 
            
        return full_path

    def get_output_file(self, filename: str) -> Path:
        """Generates the absolute path where the final extracted data will be saved."""
        return self.base_dir / self.region_code / self.output_folder_name / filename
    
    def get_archive_file(self, filename: str) -> Path:
        """Generates the path for archiving processed files."""
        return self.base_dir / self.region_code / self.archive_folder_name / filename
    
    def get_newest_input_file(self) -> Path:
        """
        Scans the input directory and dynamically returns the most recently modified .xlsx file.
        This allows the pipeline to always pick up the latest task list without manual filename updates.
        """
        folder_path = self.base_dir / self.region_code / self.input_folder_name
        
        if not folder_path.exists():
            logger.critical(f"Input directory does not exist: {folder_path}")
            sys.exit(1)
            
        xlsx_files = list(folder_path.glob("*.xlsx"))
        if not xlsx_files:
            logger.critical(f"No .xlsx files found in the directory: {folder_path}")
            sys.exit(1)
            
        # Find the file with the most recent modification time
        newest_file = max(xlsx_files, key=lambda f: f.stat().st_mtime)
        return newest_file

    def get_profile_path(self, site_name: str) -> Path:
        """
        Returns the local path for a specific site's persistent browser profile.
        Essential for keeping active sessions and bypassing strict anti-bot protections.
        """
        profile_dir = Path.home() / f"EdgeProfile_{site_name}_Automation"
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir