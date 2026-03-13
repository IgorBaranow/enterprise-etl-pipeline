import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from core.logger import get_logger

class SettingsManager:
    """
    A CLI utility to manage local credentials and refresh persistent browser profiles.
    Allows operators to securely update passwords without touching the codebase,
    and manually solve CAPTCHAs to store valid session cookies for the automated ETL bot.
    """
    def __init__(self):
        # Storing secrets in the user's home directory prevents accidental git commits of sensitive data
        self.secret_file = Path.home() / "system_secrets.json"
        self.logger = get_logger("SETTINGS", region_code="Global")
        
        # Abstracted site list to comply with NDA and security best practices
        self.sites = {
            "1": {"name": "Portal A (Region 1 & 2)", "url": "https://example-portal-a.com/login"},
            "2": {"name": "Vendor B (Region 1)", "url": "https://example-vendor-b.com/login"},
            "3": {"name": "Compliance Gateway C (Region 3)", "url": "https://example-compliance-gateway.com/records"}
        }

    def _load_secrets(self) -> dict:
        """Loads the credentials vault from the local file system."""
        if self.secret_file.exists():
            try:
                with open(self.secret_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.logger.error("Secrets file is corrupted. Starting fresh.")
        return {}

    def _save_secrets(self, data: dict):
        """Saves the updated credentials back to the JSON vault."""
        with open(self.secret_file, "w") as f:
            json.dump(data, f, indent=4)

    def update_credentials(self):
        """
        Interactive command-line menu for updating site logins and passwords.
        Masks existing passwords for basic shoulder-surfing security.
        """
        data = self._load_secrets()
        
        while True:
            print("\n" + "="*50)
            print("   CREDENTIALS MANAGER")
            print("="*50)
            for key, site in self.sites.items():
                print(f"{key}. {site['name']}")
            print("0. Go Back")
            print("="*50)
            
            choice = input("\n>>> Select site to update (0-3): ").strip()
            if choice == '0':
                break
            
            if choice in self.sites:
                site = self.sites[choice]
                url = site["url"]
                curr = data.get(url, {})
                
                cur_log = curr.get('login', 'Not Set')
                cur_pass = curr.get('password', '')

                # Simple password masking for the console output
                if cur_pass:
                    mask = cur_pass[:3] + "..." + cur_pass[-3:] if len(cur_pass) > 6 else "******"
                else:
                    mask = "Not Set"
                
                print(f"\n--- CONFIGURING: {site['name']} ---")
                print(f"Current Login:    {cur_log}")
                print(f"Current Password: {mask}")
                print("-" * 40)
                
                new_l = input("Enter New Login (Leave blank to keep current): ").strip()
                new_p = input("Enter New Password (Leave blank to keep current): ").strip()
                
                if new_l: curr['login'] = new_l
                if new_p: curr['password'] = new_p
                
                data[url] = curr
                self._save_secrets(data)
                print(f"\n[SUCCESS] Credentials saved for {site['name']}!")
            else:
                print("Invalid choice. Please try again.")

    def refresh_profile(self, profile_folder: str, url: str, site_name: str):
        """
        Launches a visible browser session using a specific profile directory.
        This is crucial for bypassing strict anti-bot protections (like Web Application Firewalls):
        a human operator solves the initial CAPTCHA/MFA, and the clearance cookies are saved 
        to the profile for the headless bot to use later.
        """
        profile_dir = Path.home() / profile_folder
        print(f"\n>>> OPENING {site_name} BROWSER...")
        print("INSTRUCTIONS:")
        print("1. Log in to the website.")
        print("2. Solve any security checks (CAPTCHA/MFA) if present.")
        print("3. CLOSE THE BROWSER completely when done to save the session state.")
        
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="msedge",
                headless=False,
                no_viewport=True,
                args=["--start-maximized"]
            )
            page = context.pages[0]
            page.goto(url)
            
            print("\n[!] Waiting for you to close the browser window...")
            try:
                # Pauses script execution until the user manually closes the browser window.
                # This gives the user unlimited time to solve MFA challenges.
                page.wait_for_event("close", timeout=0) 
            except Exception:
                pass
            print(f"[SUCCESS] Security tokens cached! Profile '{profile_folder}' saved.")

    def profile_menu(self):
        """Interactive CLI menu for managing and refreshing browser profiles."""
        while True:
            print("\n" + "="*50)
            print("   BROWSER PROFILE REFRESH (Fix Logins/Captchas)")
            print("="*50)
            print("1. Refresh Portal A Profile")
            print("2. Refresh Vendor B Profile")
            print("0. Go Back")
            print("="*50)
            
            choice = input("\n>>> Select profile to refresh (0-2): ").strip()
            
            if choice == '1':
                self.refresh_profile("EdgeProfile_Portal_A_Automation", "https://example-portal-a.com/main", "PORTAL A")
            elif choice == '2':
                self.refresh_profile("EdgeProfile_Vendor_B_Automation", "https://example-vendor-b.com/login", "VENDOR B")
            elif choice == '0':
                break
            else:
                print("Invalid choice.")