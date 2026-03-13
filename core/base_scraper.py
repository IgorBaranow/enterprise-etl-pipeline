import pandas as pd
from playwright.sync_api import sync_playwright
import sys
from core.config import ScraperSettings
from core.logger import get_logger

class BaseScraper:
    """
    Base class providing core functionality for all target-specific extraction modules.
    Handles browser initialization, anti-bot evasion, data ingestion, and resource cleanup.
    """
    
    def __init__(self, settings: ScraperSettings, script_name: str):
        self.settings = settings
        self.logger = get_logger(script_name, self.settings.country_code)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start_browser(self, profile_dir=None):
        """
        Launches the headless/headed browser engine. 
        Supports launching with a persistent profile to maintain sessions and bypass security checks.
        """
        self.logger.info(">>> Initializing Browser Engine...")
        self.playwright = sync_playwright().start()
        
        # Use a persistent profile if provided. 
        # Crucial for reusing cached security tokens and bypassing strict Web Application Firewalls (WAF).
        if profile_dir:
            self.logger.info(f">>> Attaching to persistent profile: {profile_dir.name}")
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="msedge",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                no_viewport=True
            )
            self.page = self.context.pages[0]
            
        # Otherwise, launch a clean, stateless browser session.
        else:
            self.browser = self.playwright.chromium.launch(
                channel="msedge", 
                headless=False,
                args=["--start-maximized"]
            )
            self.context = self.browser.new_context(no_viewport=True)
            self.page = self.context.new_page()
            
        # Mask the 'webdriver' flag to prevent immediate fingerprinting by target endpoints.
        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def read_input_data(self, filename: str) -> pd.DataFrame:
        """
        Loads the input data file containing the target entities/records to process in the current batch.
        """
        file_path = self.settings.get_input_file(filename)
        self.logger.info(f">>> Ingesting data batch from: {file_path.name}")
        
        try:
            df = pd.read_excel(file_path)
            return df
        except Exception as e:
            self.logger.critical(f"Critical I/O error during file ingestion: {e}")
            sys.exit(1)

    def close_browser(self):
        """
        Safely terminates the browser context and stops the engine.
        Essential for preventing background zombie processes and freeing up system memory.
        """
        self.logger.info(">>> Terminating browser session and flushing memory...")
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def run(self):
        """
        Main execution pipeline sequence. Must be explicitly overridden by child deployment classes.
        """
        raise NotImplementedError("This execution method must be overridden in the child class!")