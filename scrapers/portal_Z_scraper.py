import time
import re
import json
from pathlib import Path
import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from core.base_scraper import BaseScraper
from core.config import ScraperSettings

class PortalBScraper(BaseScraper):
    """
    Extraction module for 'Portal B' (Global Asset Tracking System).
    Handles authenticated sessions, executes sequential search queries, 
    and extracts status information with built-in retry mechanisms for slow-loading dynamic tables.
    """
    def __init__(self, settings: ScraperSettings):
        super().__init__(settings, script_name="PORTAL_B_TRACKER")
        self.results = []
        
        # Abstracted URLs and target endpoints
        self.website_url = "https://example-asset-tracker.com/login"
        self.target_locations = ["LOCATION-1", "LOCATION-2"]
        self.output_filename = "PORTAL_B_OUTPUT.xlsx"
        self.output_sheet_name = "TRACKING_RESULTS"
        
        # Standard validation pattern for Item IDs (e.g., 4 letters + 7 digits)
        self.item_pattern = re.compile(r"^[A-Z]{4}\d{7}$")

    def get_credentials(self) -> tuple[str, str]:
        """Retrieves login credentials from the encrypted local vault."""
        secret_file = Path.home() / "system_secrets.json"
        secrets_db = {}
        
        if secret_file.exists():
            try:
                with open(secret_file, "r") as f:
                    secrets_db = json.load(f)
            except json.JSONDecodeError:
                self.logger.exception("Secrets file is corrupted or unreadable.")

        if self.website_url in secrets_db:
            self.logger.info("Credentials successfully loaded from local vault.")
            return secrets_db[self.website_url]['login'], secrets_db[self.website_url]['password']

        self.logger.error(f"Credentials missing for {self.website_url}")
        raise Exception("Credentials missing! Please configure them in the CLI Settings Manager.")

    def get_tracking_status(self, item_id: str) -> str:
        """
        Executes a search for a specific item ID and attempts to read its status from the DOM.
        Implements a multi-attempt retry loop to handle network latency and delayed DOM rendering.
        """
        assert self.page is not None
        
        try:
            search_box = self.page.get_by_role("textbox", name="Enter item number(s) here")
            search_box.fill(item_id)
            self.page.get_by_role("button", name="Search").click()

            # Retry loop: The application table sometimes takes a moment to fetch data via XHR
            for attempt in range(1, 4):
                try:
                    table = self.page.locator("table.data-table").first
                    table.wait_for(state="visible", timeout=3000) 
                    
                    status_cell = table.locator("td.data-table__status-cell").first
                    
                    if status_cell.is_visible():
                        raw_text = status_cell.inner_text()
                        
                        # Data cleansing: Extracting the primary status line
                        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                        result = lines[0] if lines else "N/A"

                        # Filtering out placeholder text that indicates the data hasn't loaded yet
                        bad_keywords = ["Status is unavailable", "N/A", "Actions"]
                        if any(bad in result for bad in bad_keywords) or result == "":
                            if attempt < 3:
                                time.sleep(1)
                                continue
                            return result
                        
                        return result 
                
                except PlaywrightTimeout:
                    if attempt < 3:
                        time.sleep(1)
                        continue
                    return "N/A"
            
            return "N/A"
            
        except Exception as e:
            if self.page.is_closed() or "has been closed" in str(e):
                self.logger.critical("Browser was closed manually! Aborting.")
                raise
            self.logger.error(f"Error extracting status for {item_id}: {e}")
            return "ERROR"

    def run(self):
        """Orchestrates the login, data parsing, scraping loop, and output generation."""
        self.logger.info("="*60)
        self.logger.info(">>> STARTING PORTAL B EXTRACTION (OOP Edition)")
        self.logger.info("="*60)

        # 1. Fetch Credentials
        my_login, my_password = self.get_credentials()

        # 2. Load and Filter Input Data
        df = self.read_input_data("REGION_B_INPUT.xlsx")
        df.columns = df.columns.str.strip()
        df.rename(columns={df.columns[0]: 'ITEM_ID', df.columns[1]: 'LOCATION'}, inplace=True)
        
        # Filter logic: Validate ID format and ensure the item belongs to our target locations
        work_queue = df[
            (df['ITEM_ID'].astype(str).str.match(self.item_pattern, na=False)) & 
            (df['LOCATION'].isin(self.target_locations))
        ].copy()
        
        if work_queue.empty:
            self.logger.warning("No valid items found for Portal B. Exiting.")
            return
            
        self.logger.info(f"Loaded {len(work_queue)} items for processing.")

        # 3. Initialize Browser and Login (Stateless session)
        save_success = False 

        try:
            # profile_dir=None prevents the creation of unnecessary persistent folders
            self.start_browser(profile_dir=None)
            assert self.page is not None, "Browser page failed to initialize"

            self.logger.info(f"Navigating to {self.website_url}")
            self.page.goto(self.website_url, wait_until="domcontentloaded")
            time.sleep(2)

            self.logger.info("Logging in...")
            try:
                email_field = self.page.get_by_placeholder("Enter email address")
                if email_field.is_visible(timeout=3000):
                     email_field.fill(my_login)
                     self.page.get_by_placeholder("Enter password").fill(my_password)
                     self.page.locator("#login_page_login_button").click()
                     
                     # Wait for network activity to settle before proceeding
                     self.page.wait_for_load_state("networkidle")
                     self.logger.info("Login successful.")
                else:
                     self.logger.warning("Login form not found. Retrying page load...")
                     self.page.reload()
                     
            except Exception as e:
                if self.page.is_closed() or "has been closed" in str(e):
                    raise
                self.logger.error(f"Login sequence failed: {e}")

            # 4. Main Scraping Loop
            self.logger.info("Starting processing loop...")
            first_search = True
            total = len(work_queue)

            for index, row in enumerate(work_queue.itertuples(), start=1):
                item_id = str(row.ITEM_ID).strip()
                self.logger.info(f"[{index}/{total}] Processing: {item_id}")

                try:
                    # Clear previous search state for subsequent items
                    if not first_search:
                        try: 
                            self.page.get_by_role("button", name="New search").click(timeout=1000)
                        except Exception: 
                            pass
                    
                    first_search = False
                    status = self.get_tracking_status(item_id)
                    
                except Exception as e:
                    if self.page.is_closed() or "has been closed" in str(e):
                        self.logger.critical("Browser was closed manually! Aborting the entire loop.")
                        raise 
                    self.logger.error(f"Item {item_id} failed: {e}")
                    status = "ERROR"

                self.results.append([item_id, status])
                
            save_success = True 
            
        except Exception as e:
             self.logger.critical(f"Critical browser error: {e}")
             raise
        finally:
            self.close_browser()

        # 5. Export Results
        if self.results and save_success:
            self.logger.info("Exporting results to Excel...")
            try:
                output_file = self.settings.get_output_file(self.output_filename)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                df_out = pd.DataFrame(self.results, columns=["ITEM_ID", "STATUS_INFO"])
                
                with pd.ExcelWriter(output_file, mode='w', engine='openpyxl') as writer:
                    df_out.to_excel(writer, sheet_name=self.output_sheet_name, index=False)
                    
                self.logger.info(f"Pipeline complete! File saved at: {output_file}")
            except Exception as e:
                self.logger.critical(f"Could not save file (is it open in another application?): {e}")
        else:
             self.logger.warning("Pipeline aborted. Skipping save operation to prevent file corruption.")

if __name__ == "__main__":
    # Local testing block
    test_settings = ScraperSettings(region_code="REGION_B")
    bot = PortalBScraper(test_settings)
    bot.run()