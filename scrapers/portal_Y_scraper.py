import time
import re
import json
import pandas as pd
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeout, Locator, FrameLocator

from core.base_scraper import BaseScraper
from core.config import ScraperSettings

class PortalAScraper(BaseScraper):
    """
    Extraction module for 'Portal A'.
    This legacy portal uses an older iFrame-based architecture and requires a persistent 
    browser profile to bypass initial security checks (WAF/CAPTCHA).
    Extracts item statuses by analyzing front-end CSS icon classes instead of raw text.
    """
    def __init__(self, settings: ScraperSettings):
        super().__init__(settings, script_name="PORTAL_A")
        
        self.results = [] 
        
        # Abstracted target URLs and target group categories
        self.website_url = "https://example-legacy-portal.com/main.xhtml"
        self.target_group = "GROUP-ALPHA-1"
        self.output_filename = "PORTAL_A_OUTPUT.xlsx"
        self.output_sheet_name = "RESULTS_ALPHA"
        
        # Mapping front-end visual CSS icons to human-readable data statuses
        self.status_map = {
            "fa-check": "YES",
            "fa-times": "NO",
            "fa-ban":   "N/A"
        }

    def get_icon_status(self, row_locator: Locator, col_index: int) -> str:
        """
        Extracts the business status (YES/NO/N/A) by reading the CSS class 
        of an icon element located in a specific table column.
        """
        icon = row_locator.locator(f"td:nth-child({col_index}) i")

        if icon.count() == 0:
            return "N/A"

        cls = icon.get_attribute("class")
        
        if not cls:
            self.logger.warning(f"Icon at column {col_index} exists but has no class attribute!")
            return "WARN_NO_CLASS"

        for icon_class, status in self.status_map.items():
            if icon_class in cls:
                return status

        self.logger.warning(f"Found unknown icon class: '{cls}' at column {col_index}")
        return f"UNKNOWN_ICON_{cls.split()[-1]}"

    def run(self):
        """
        Main execution pipeline: loads target items, filters them, attaches to the legacy 
        iFrame dashboard, processes items one by one, and exports the results.
        """
        self.logger.info("="*60)
        self.logger.info(">>> STARTING PORTAL A EXTRACTION (OOP Edition)")
        self.logger.info("="*60)

        # Load and normalize input data
        df = self.read_input_data("REGION_A_INPUT.xlsx")
        df.columns = df.columns.str.strip()
        df.rename(columns={df.columns[0]: 'ITEM_ID', df.columns[1]: 'GROUP'}, inplace=True)
        
        # Filter logic: Only process items matching the standardized 11-character alphanumeric format
        # and belonging to the specific target group.
        work_queue = df[
            (df['ITEM_ID'].astype(str).str.match(r'^[A-Z]{4}\d{7}$', na=False)) & 
            (df['GROUP'] == self.target_group)
        ].copy()
        
        if work_queue.empty:
            self.logger.warning("No valid items found to process for this group. Exiting.")
            return 
            
        self.logger.info(f"Loaded {len(work_queue)} valid items for processing.")

        # Using a persistent profile allows us to retain CAPTCHA clearance cookies 
        # generated during manual profile refresh sessions.
        profile_dir = Path.home() / "EdgeProfile_PortalA_Automation"
        
        save_success = False
        
        try:
            self.start_browser(profile_dir=profile_dir)
            assert self.page is not None, "Browser page failed to initialize"
            
            self.logger.info(f"Navigating to {self.website_url}")
            self.page.goto(self.website_url)

            # Handle optional 'Guest' entry modal if it appears
            try:
                guest_btn = self.page.get_by_role("button", name="Guest")
                if guest_btn.is_visible(timeout=5000):
                    self.logger.info("Clicking 'Guest' entry button...")
                    guest_btn.click()
                    time.sleep(2)
            except Exception: 
                pass

            self.logger.info("Verifying dashboard access and attaching to main iFrame...")
            self.page.wait_for_selector("iframe[name='main']", state="attached", timeout=30000)
            
            
            # The entire application logic lives inside an iFrame, so we must scope our locators here
            frame: FrameLocator = self.page.frame_locator("iframe[name='main']")
            frame.locator("body").wait_for(timeout=10000)

            if not frame.locator("body").is_visible():
                raise RuntimeError("Main frame content failed to render or is not visible!")
                
            self.logger.info("Dashboard verification successful.")

            total = len(work_queue)
            for index, row in enumerate(work_queue.itertuples(), start=1):
                item_id = str(row.ITEM_ID).strip()
                self.logger.info(f"[{index}/{total}] Processing Item: {item_id}")

                status_primary = "N/A"
                status_secondary = "N/A"

                try:
                    # Reset the search form to ensure a clean state for the next item
                    try:
                        reset_btn = frame.get_by_role("button", name=re.compile(r"New (Search|Query|Request)", re.IGNORECASE))
                        if reset_btn.is_visible(timeout=500):
                            reset_btn.click()
                    except Exception: 
                        pass

                    inp = frame.get_by_role("textbox", name="Item Id:")
                    inp.click()
                    inp.fill(item_id)

                    try:
                        go_btn = frame.get_by_role("button", name="Go")
                        go_btn.click()
                    except Exception:
                        inp.press("Enter")

                    # Wait for either the data table to populate OR the 'not found' message to appear
                    try:
                        frame.locator(".ui-datatable-data tr").or_(
                            frame.locator("text='No details exist'")
                        ).first.wait_for(timeout=5000)
                    except PlaywrightTimeout:
                        pass 

                    if frame.get_by_text("No details exist").is_visible():
                        status_primary, status_secondary = "NOT FOUND", "NOT FOUND"
                    else:
                        row_el = frame.locator("tbody[id*='DataTableImp_data'] tr").first
                        if row_el.is_visible():
                            # Column 4 and 5 contain the specific status icons we need
                            status_primary = self.get_icon_status(row_el, 4)
                            status_secondary = self.get_icon_status(row_el, 5)
                        else:
                            status_primary, status_secondary = "UNKNOWN_NO_ROW", "UNKNOWN_NO_ROW"

                except Exception as e:
                    # Failsafe: Detect if the user explicitly closed the browser window mid-run
                    if self.page.is_closed() or "has been closed" in str(e):
                        self.logger.critical("Browser was closed manually by the user! Aborting the entire loop.")
                        raise 
                        
                    self.logger.error(f"Row {index} ({item_id}) encountered an error: {e}")
                    status_primary, status_secondary = "ERROR", "ERROR"
                
                self.results.append([item_id, status_primary, status_secondary])
            
            save_success = True
            
        except Exception as e:
             self.logger.critical(f"Critical execution error: {e}")
             raise
             
        finally:
            self.close_browser()

        # Final export step
        if self.results and save_success:
            self.logger.info("Exporting results to Excel...")
            try:
                output_file = self.settings.get_output_file(self.output_filename)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                df_out = pd.DataFrame(self.results, columns=["ITEM_ID", "PRIMARY_STATUS", "SECONDARY_STATUS"])
                
                with pd.ExcelWriter(output_file, mode='w', engine='openpyxl') as writer:
                    df_out.to_excel(writer, sheet_name=self.output_sheet_name, index=False)
                    
                self.logger.info(f"Pipeline complete! File saved: {output_file}")
            except Exception as e:
                self.logger.critical(f"Could not save file (is it open in another program?): {e}")
                raise
        else:
            self.logger.warning("Pipeline aborted. Skipping save operation to prevent file corruption.")


if __name__ == "__main__":
    # Local testing block
    test_settings = ScraperSettings(region_code="REGION_A")
    bot = PortalAScraper(test_settings)
    bot.run()