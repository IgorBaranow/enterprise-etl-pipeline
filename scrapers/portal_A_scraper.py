import time
import re
import json
import pandas as pd
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from core.base_scraper import BaseScraper
from core.config import ScraperSettings

class Country_A_Scraper(BaseScraper):
    """
    Extraction module for 'Portal C' (Enterprise Compliance Portal).
    Handles complex Single Page Application (SPA) interactions, including JavaScript-injected clicks, 
    manual 2FA intervention pauses, pagination scanning, and native browser file downloads.
    """
    def __init__(self, settings: ScraperSettings):
        super().__init__(settings, script_name="PORTAL_C_EXTRACTOR")
        
        # Abstracted URLs and target data parameters
        self.website_url = "https://example-enterprise-portal.com/"
        self.target_status = "Action Required" 
        self.target_locations = ["ZONE-X", "ZONE-Y"]
        
        # React/Material-UI often uses data-testids. These map to the specific columns we need.
        self.status_col_id = "17"
        self.location_col_id = "8"
        
        self.output_filename = "PORTAL_C_OUTPUT.xlsx"

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
        raise Exception("Credentials missing! Please configure them via the CLI Settings Manager.")

    def perform_login(self, login: str, password: str) -> None:
        """
        Executes the initial login sequence. 
        Uses JavaScript injection as a primary click method to bypass strict event listeners on the SPA frontend.
        """
        assert self.page is not None
        
        self.logger.info(f"Navigating to: {self.website_url}")
        self.page.goto(self.website_url)
        
        self.logger.info(f"Injecting credentials for: {login}")
        self.page.get_by_role("textbox", name="Your email address").fill(login)
        self.page.get_by_role("textbox", name="Password").fill(password)
        
        # Simulating human behavior to trigger React form validation states
        self.page.keyboard.press("Tab")
        time.sleep(1) 

        login_btn = self.page.get_by_role("button", name=re.compile(r"Log\s?in|Sign\s?in|Login", re.IGNORECASE))

        try:
            login_btn.wait_for(state="attached", timeout=5000)
            self.logger.info("Injecting JavaScript CLICK event to bypass overlay blockers...")
            login_btn.evaluate("element => element.click()")
            self.logger.info("JS Click command dispatched successfully.")
            
            try:
                self.page.wait_for_load_state("networkidle", timeout=5000)
            except PlaywrightTimeout: 
                pass
                
        except Exception as e:
            self.logger.error(f"JS Click execution failed: {e}")
            self.logger.info("Fallback activated: Simulating physical 'Enter' key press...")
            self.page.keyboard.press("Enter")

    def handle_manual_2fa(self) -> None:
        """
        Pauses the automated execution pipeline to allow a human operator to complete 
        a Multi-Factor Authentication (MFA) challenge sent via email or SMS.
        """
        assert self.page is not None
        
        self.logger.info(">>> PIPELINE PAUSED FOR MANUAL INTERVENTION (MFA/2FA) <<<")
        self.logger.info("Awaiting operator input. You have 3 minutes to enter the security code...")
        
        try:
            # We wait for a specific dashboard element to appear, signaling MFA is complete
            self.page.wait_for_selector("text=View per Item", timeout=180000)
            self.logger.info("MFA challenge cleared! Dashboard detected. Resuming automated pipeline...")
        except PlaywrightTimeout:
            self.logger.warning("3-minute timeout elapsed. Verifying if dashboard routed successfully...")
        
        self.page.wait_for_load_state("domcontentloaded")
        if "Secure Portal" not in self.page.title():
            raise Exception(f"Validation Failed: Expected 'Secure Portal', but routed to '{self.page.title()}'")

    def setup_dashboard_view(self) -> None:
        """Configures the UI table to display the necessary columns and sorts by the target status."""
        assert self.page is not None
        self.logger.info("Configuring frontend data table view...")
        
        self.page.get_by_role("tab", name="View per Item").click()
        
        try:
            # Using data-testid is the most robust way to interact with modern React apps
            self.page.wait_for_selector(f"[data-testid='headcol-{self.status_col_id}']", state="visible", timeout=10000)
        except PlaywrightTimeout:
            raise Exception("Table headers failed to render. Potential network latency or UI update.")

        self.logger.info(f"Applying sorting logic on Column ID {self.status_col_id}...")
        self.page.get_by_test_id(f"headcol-{self.status_col_id}").click()
        
        # Hard sleep required here as the SPA sorting animation doesn't trigger a reliable network/DOM event
        self.logger.info("Awaiting UI state reconciliation (10 seconds)...")
        time.sleep(10)
        self.logger.info("Resuming data extraction...")

    def scrape_items(self) -> int:
        """
        Iterates through paginated table rows, evaluates business logic (Status & Location),
        and interacts with checkboxes to build an export queue.
        """
        assert self.page is not None
        selected_items_count = 0
        page_number = 0   
        keep_scanning = True

        while keep_scanning:
            page_number += 1
            self.logger.info(f"Scanning UI Data Page {page_number}...")
            
            try:
                self.page.wait_for_selector(f"[data-testid^='MuiDataTableBodyCell-{self.status_col_id}-']", timeout=5000)
            except Exception as e:
                if self.page.is_closed() or "has been closed" in str(e):
                    self.logger.critical("Browser context was terminated externally. Aborting.")
                    raise
                self.logger.info("DOM empty: No data rows found on current page view.")
                break

            for i in range(50): # Max rows per page is 50
                if self.page.is_closed():
                    self.logger.critical("Browser context was terminated externally. Aborting.")
                    raise Exception("Target page or browser has been closed unexpectedly.")

                status_cell = self.page.get_by_test_id(f"MuiDataTableBodyCell-{self.status_col_id}-{i}")
                loc_cell    = self.page.get_by_test_id(f"MuiDataTableBodyCell-{self.location_col_id}-{i}")

                if not status_cell.is_visible():
                    keep_scanning = False
                    break
                
                status_text = status_cell.inner_text().strip()
                loc_text    = loc_cell.inner_text().strip()
                
                # Business Logic Validation
                if self.target_status in status_text:
                    if loc_text in self.target_locations:
                        selected_items_count += 1
                        try:
                            status_cell.click()
                            self.logger.info(f"Queued Row {i+1} | Location: {loc_text}")
                            time.sleep(0.1)
                        except Exception as e:
                            if self.page.is_closed() or "has been closed" in str(e):
                                self.logger.critical("Browser context was terminated externally. Aborting.")
                                raise
                            self.logger.error(f"Interaction failed on row {i+1}: {e}")
                else:
                    if status_text != "":
                        self.logger.info(f"Boundary reached. Discovered non-target status: '{status_text}'. Halting scan.")
                        keep_scanning = False
                        break 
            
            # Pagination Handling
            if keep_scanning:
                try:
                    next_button = self.page.get_by_test_id("pagination-next")
                    if next_button.is_visible() and next_button.is_enabled():
                        self.logger.info("Triggering pagination event...")
                        next_button.click()
                        self.page.wait_for_load_state("networkidle")
                        time.sleep(3) 
                    else:
                        self.logger.info("End of paginated data reached.")
                        keep_scanning = False
                except Exception as e:
                    if self.page.is_closed() or "has been closed" in str(e):
                        self.logger.critical("Browser context was terminated externally. Aborting.")
                        raise
                    self.logger.error(f"Pagination sequence failed: {e}")
                    keep_scanning = False

        self.logger.info(f"Total valid items queued for extraction: {selected_items_count}")
        return selected_items_count

    def export_data(self) -> None:
        """Triggers the web application's native export functionality and intercepts the downloaded file."""
        assert self.page is not None
        self.logger.info("Initializing Export Protocol...")
        
        try:
            self.page.get_by_role("button", name="excel").click()
            time.sleep(1) 
            self.page.wait_for_selector("text=Flat table", timeout=3000)
            self.page.get_by_role("menuitem", name="Flat table").click()
        except Exception:
            self.logger.error("Failed to interact with the DOM Export menu.")
            return

        self.logger.info("Awaiting binary file stream from server...")

        try:
            # Intercepting the browser's download event to save the file programmatically
            with self.page.expect_download(timeout=300000) as download_info:
                self.page.get_by_role("button", name="Continue with pincode").click()
                download = download_info.value
                
                target_path = self.settings.get_output_file(self.output_filename)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(target_path)
                self.logger.info(f"SUCCESS! Stream intercepted and saved to: {target_path.name}")
                
                self._update_master_archive(target_path)

        except Exception as e:
            self.logger.error(f"Download interception or Archiving process failed: {e}")

    def _update_master_archive(self, fresh_file_path: Path):
        """
        Maintains a historical database. Appends new scrape results to an existing master Excel file,
        removing duplicates to keep the dataset clean.
        """
        self.logger.info(">>> Syncing data with Master Archive...")
        
        archive_path = self.settings.get_output_file("MASTER_PORTAL_C_ARCHIVE.xlsx")
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            df_new = pd.read_excel(fresh_file_path)
            # Tagging records with an ingestion timestamp for historical tracking
            df_new['INGESTION_TIMESTAMP'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

            if archive_path.exists():
                df_archive = pd.read_excel(archive_path)
                df_combined = pd.concat([df_archive, df_new], ignore_index=True)
                
                # Deduplicate based on all columns except the timestamp to keep the most recent unique records
                cols_to_check = [c for c in df_new.columns if c != 'INGESTION_TIMESTAMP']
                df_combined.drop_duplicates(subset=cols_to_check, keep='last', inplace=True)
            else:
                df_combined = df_new

            df_combined.to_excel(archive_path, index=False, engine='openpyxl')
            self.logger.info(f">>> Archive synchronized successfully! Total historical rows: {len(df_combined)}")

        except Exception as e:
            self.logger.critical(f"Database synchronization failed: {e}")

    def run(self):
        """Orchestrates the entire scraping lifecycle."""
        self.logger.info("="*60)
        self.logger.info(">>> STARTING PORTAL C PIPELINE (OOP Edition)")
        self.logger.info("="*60)

        my_login, my_password = self.get_credentials()

        try:
            self.start_browser(profile_dir=None)
            
            self.perform_login(my_login, my_password)
            self.handle_manual_2fa()
            self.setup_dashboard_view()
            
            total_found = self.scrape_items()

            if total_found > 0:
                self.export_data()
            else:
                self.logger.warning("No items matched the specific business criteria. Export sequence skipped.")
                
        except Exception as e:
             self.logger.critical(f"Critical execution error: {e}")
             raise
        finally:
            self.close_browser()

if __name__ == "__main__":
    # Local testing block initialized with the globally updated variable schema
    region_c_settings = ScraperSettings(region_code="REGION_C")
    bot = Country_A_Scraper(region_c_settings)
    bot.run()