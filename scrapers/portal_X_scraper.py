import time
import re
import json
import pandas as pd
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from core.base_scraper import BaseScraper
from core.config import ScraperSettings

class RegionXScraper(BaseScraper):
    """
    Extraction module for the Region X Compliance/Tracking Portal.
    Handles automated login, dynamic search suggestions, and extracting structured 
    operational event timestamps using Regex pattern matching.
    """
    def __init__(self, settings: ScraperSettings):
        super().__init__(settings, script_name="REGION_X_TRACKING")
        
        # Abstracted URL for the portfolio purposes
        self.website_url = "https://example-x-tracking.io/#/records"
        self.output_filename = "REGION_X_results.xlsx"
        
        self.all_records: list[dict[str, str]] = []

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

    def perform_login(self, login: str, password: str) -> None:
        """Executes the login sequence and waits for the SPA (Single Page Application) dashboard to route."""
        assert self.page is not None
        
        self.logger.info(f"Navigating to {self.website_url}...")
        self.page.goto(self.website_url, wait_until="domcontentloaded")

        try:
            self.logger.info("Injecting credentials...")
            # Locating inputs by accessible roles ensures the script doesn't break if CSS classes change
            self.page.get_by_role("textbox", name="name@host.com").fill(login)
            self.page.get_by_role("textbox", name="Password").fill(password)
            self.page.get_by_role("button", name="submit").click()
            
            self.logger.info("Waiting for dashboard routing...")
            self.page.wait_for_url(lambda u: u.startswith("https://example-x-tracking.io/#/"), timeout=30000)
            
            # Abstracted target module link
            tracking_link = self.page.get_by_role("link", name="] Records")
            tracking_link.wait_for(state="visible", timeout=15000)
            tracking_link.click()
            self.logger.info("Login successful. Navigated to Records module.")
            
        except Exception as e:
            self.logger.error(f"Login sequence failed or timed out: {e}")
            raise

    def scrape_item_data(self, target_items: list[str]) -> None:
        """
        Iterates through the target items list, interacts with the dynamic search dropdown,
        and extracts various release timestamps into a structured dictionary.
        """
        assert self.page is not None
        total = len(target_items)

        for i, item_id in enumerate(target_items):
            self.logger.info(f"[{i+1}/{total}] Fetching data for Entity {item_id} ...")
            
            try:
                # Target the dynamic search field
                field = self.page.get_by_role("textbox", name="()")
                field.wait_for(state="visible", timeout=10000)
                field.fill("") # Clear previous entry
                field.fill(item_id)
                
                # The site uses an autocomplete dropdown. We must wait for and click the exact suggestion.
                suggestion = self.page.get_by_role("link", name=re.compile(rf"^{re.escape(item_id)}\b"))
                suggestion.first.wait_for(state="visible", timeout=5000)
                suggestion.first.click()
                
                # Wait for the data row to render in the DOM
                row = self.page.locator(".results-tracking-line").first
                row.wait_for(state="visible", timeout=10000)

                # Extract generic metadata using Regex
                left_block = self.page.locator(".header-tracking .col-md-3").first.inner_text().strip()
                m = re.search(r"XXX_example", left_block)
                bl = m.group(1) if m else ""
                vendor = m.group(2).strip() if m else ""

                # Map UI display names to internal data attributes
                cols = [
                    ("Field_1", "res_val_1"),
                    ("Field_2", 'res_val_2'),
                    ("Field_3", 'res_val_3'),
                    ("Field_4", 'res_val_4'),
                    ("Field_5", 'res_val_5'),
                    ("Field_6", 'res_val_6'),
                ]

                record: dict[str, str] = {"Entity_ID": item_id, "Metadata_1": bl, "Metadata_2": vendor}
                
                # Dynamically extract timestamps for all mapped columns
                for label, name in cols:
                    block = row.locator(f'tracking-result-data[tracking-data-name="{name}"]')
                    parts = [t.inner_text().strip() for t in block.locator(".date").all()]
                    record[label] = " ".join(p for p in parts if p)

                self.all_records.append(record)
                
            except Exception as e:
                # Catch scenarios where the user manually closed the browser mid-execution
                if self.page.is_closed() or "has been closed" in str(e):
                    self.logger.critical(f"Browser was closed manually! Aborting execution loop.")
                    raise
                
                self.logger.warning(f"No result found or element timeout for {item_id}")
                self.all_records.append({"Entity_ID": item_id, "Metadata_1": "ERROR/NOT FOUND", "Metadata_2": ""})
                
                # Attempt to escape the dropdown/modal if an error occurred to reset state for the next item
                try:
                    self.page.keyboard.press("Escape")
                except Exception: 
                    pass
                continue

    def run(self):
        """Orchestrates the data loading, browser launch, extraction loop, and data export."""
        self.logger.info("="*60)
        self.logger.info(">>> STARTING REGION X EXTRACTION PIPELINE (OOP Edition)")
        self.logger.info("="*60)

        input_file = self.settings.get_newest_input_file()
        self.logger.info(f"Processing target file: {input_file.name}")
        
        try:
            df_in = pd.read_excel(input_file, usecols="A", header=None, engine='openpyxl')
            
            # Use Regex to filter out invalid item formats based on business rules
            pat = re.compile(r"^[A-Z]{4}\d{7}$") # Standardized Entity ID Validation Regex
            target_items = [str(v).strip().upper() for v in df_in[0].dropna() if pat.fullmatch(str(v).strip().upper())]
            
            if not target_items:
                self.logger.warning("No valid Entity IDs found in the input. Exiting.")
                return
            self.logger.info(f"Successfully loaded {len(target_items)} valid target entities.")
        except Exception as e:
            self.logger.critical(f"Failed to parse input Excel: {e}")
            raise

        my_login, my_password = self.get_credentials()

        save_success = False 
        try:
            # We don't need a persistent profile here because this portal doesn't use heavy anti-bot software
            self.start_browser(profile_dir=None)
            self.perform_login(my_login, my_password)
            self.scrape_item_data(target_items)
            save_success = True 
            
        except Exception as e:
             self.logger.critical(f"Critical execution error: {e}")
             raise
             
        finally:
            self.close_browser()
            
        # Only save if we have data and the pipeline didn't crash mid-way
        if self.all_records and save_success:
            self.logger.info("Exporting results to Excel...")
            try:
                output_file = self.settings.get_output_file(self.output_filename)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                df_out = pd.DataFrame(self.all_records)
                
                with pd.ExcelWriter(output_file, mode='w', engine='openpyxl') as writer:
                    df_out.to_excel(writer, index=False)
                    
                self.logger.info(f"Pipeline complete! File saved: {output_file}")
            except Exception as e:
                self.logger.critical(f"Could not save file (is it open in another program?): {e}")
                raise
        else:
             self.logger.warning("Pipeline aborted. Skipping save operation to prevent file corruption.")


if __name__ == "__main__":
    # Test execution block
    x_settings = ScraperSettings(region_code="REGION_X")
    bot = RegionXScraper(x_settings)
    bot.run()