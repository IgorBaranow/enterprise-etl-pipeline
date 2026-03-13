import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import json
import os
import ctypes
import traceback
from pathlib import Path

# Fix blurry text on High-DPI (4K) displays on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

try:
    import sv_ttk 
    from core.config import ScraperSettings
    # Importing abstracted scraper modules (Synchronized with updated class names)
    from scrapers.portal_a_scraper import PortalAScraper
    from scrapers.portal_b_scraper import PortalBScraper
    from scrapers.portal_c_scraper import PortalCScraper
    from scrapers.region_y_scraper import RegionYSecureScraper
    from scrapers.region_x_scraper import RegionXScraper
    from core.excel_cleaner import ExcelCleaner
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print(f"Critical Import Error: {e}")

class LogRedirector:
    """
    Utility class to intercept Python's standard output (print statements and logs) 
    and route them directly into the Tkinter GUI text widget in real-time.
    """
    def __init__(self, text_widget):
        self.text_widget = text_widget
        
    def write(self, text):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END) # Auto-scroll to the bottom
        self.text_widget.config(state=tk.DISABLED)
        
    def flush(self): 
        pass

class EnterpriseAutomationApp:
    """
    Main GUI application built with Tkinter.
    Acts as a central command center to manage credentials, trigger isolated automation 
    pipelines, and monitor execution logs without requiring command-line knowledge.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Enterprise ETL Command Center v1.1")
        
        # --- Adaptive Window Sizing & Centering ---
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        window_width = int(screen_width * 0.70)
        window_height = int(screen_height * 0.75)

        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)

        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.minsize(800, 600)        
        # ----------------------------------------------
        
        self.active_threads = 0 
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        try:
            sv_ttk.set_theme("light") # Apply modern flat theme
        except Exception: 
            pass

        # Secure local vault for credentials
        self.secret_file = Path.home() / "system_secrets.json"
        self.nav_btns = {}
        
        self.current_actual_password = ""
        self.current_masked_password = ""

        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 11))

        # --- Layout: Sidebar & Main Content ---
        self.sidebar = tk.Frame(root, bg="#f1f3f5", width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.main_container = tk.Frame(root, bg="white")
        self.main_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.setup_sidebar()
        
        self.pages = {}
        for name in ["Run", "Access", "System"]:
            self.pages[name] = tk.Frame(self.main_container, bg="white", padx=40, pady=30)
        
        self.setup_run_page()
        self.setup_access_page()
        self.setup_system_page()
        self.show_page("Run")

    def setup_sidebar(self):
        tk.Label(self.sidebar, text="Command Center", font=("Segoe UI Bold", 16), bg="#f1f3f5", fg="#0051BA", pady=35).pack()
        menu = [("Run", "🚀 Pipelines"), ("Access", "🔑 Passwords"), ("System", "⚙️ Reset")]
        for target, label in menu:
            btn = tk.Button(self.sidebar, text=label, font=("Segoe UI Semibold", 10), bg="#f1f3f5", fg="#495057",
                            relief=tk.FLAT, anchor="w", padx=25, pady=12, command=lambda t=target: self.show_page(t))
            btn.pack(fill=tk.X)
            self.nav_btns[target] = btn

    def show_page(self, name):
        self.current_page = name
        for n, b in self.nav_btns.items():
            b.config(bg="#0051BA" if n == name else "#f1f3f5", fg="white" if n == name else "#495057")
        for p in self.pages.values(): 
            p.pack_forget()
        self.pages[name].pack(fill=tk.BOTH, expand=True)

    # ==========================================
    # WINDOW: RUN PIPELINES
    # ==========================================
    def setup_run_page(self):
        page = self.pages["Run"]
        tk.Label(page, text="Automation Control Panel", font=("Segoe UI Bold", 20), bg="white").pack(anchor="w", pady=(0, 25))
        
        list_frame = tk.Frame(page, bg="white")
        list_frame.pack(fill=tk.X)

        # Abstracted business regions and task lists
        tasks = [
            ("Region A Operations", "REG_A", ["Full Pipeline", "Portal C", "Portal A", "Portal B"], self.run_region_a),
            ("Region B Operations", "REG_B", ["Full Pipeline", "Secure Portal Y"], self.run_region_b),
            ("Region C Operations", "REG_C", ["Full Pipeline", "Compliance Portal X"], self.run_region_c),
            ("Region D Maintenance", "REG_D", ["Full Pipeline", "Data Cleanup"], self.run_region_d)
        ]

        for name, code, sub, func in tasks:
            row = tk.Frame(list_frame, bg="white", pady=12)
            row.pack(fill=tk.X)
            
            tk.Frame(list_frame, height=1, bg="#f1f3f5").pack(fill=tk.X)
            
            task_var = tk.StringVar(value=sub[0])
            
            # Button triggers threading to keep UI from freezing during Playwright execution
            ttk.Button(row, text="\u25B6   Run", style="Accent.TButton", width=10,
                      command=lambda f=func, v=task_var, c=code: self.start_thread(lambda: self.handle_launch(f, v.get(), c))).pack(side=tk.LEFT)

            tk.Label(row, text=f"{code} - {name}", font=("Segoe UI Semibold", 11), bg="white", width=30, anchor="w").pack(side=tk.LEFT, padx=20)
            
            cb = ttk.Combobox(row, textvariable=task_var, values=sub, state="readonly", width=25)
            cb.pack(side=tk.RIGHT)
            tk.Label(row, text="Module:", font=("Segoe UI", 9), bg="white", fg="#888").pack(side=tk.RIGHT, padx=10)

        log_frame = ttk.LabelFrame(page, text=" Operational Output Console ", padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(25, 0))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=('Consolas', 10), bg="#f8f9fa", fg="#212529", borderwidth=0, padx=15, pady=15, insertbackground="black")
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.config(state=tk.DISABLED)
        
        # Reroute all backend prints/logs to the GUI text box
        sys.stdout = LogRedirector(self.log_area)
        sys.stderr = LogRedirector(self.log_area)

    # ==========================================
    # WINDOW: ACCESS & PASSWORDS
    # ==========================================
    def setup_access_page(self):
        page = self.pages["Access"]
        tk.Label(page, text="Credential Vault", font=("Segoe UI Bold", 20), bg="white").pack(anchor="w", pady=(0, 25))
        
        pw_frame = ttk.LabelFrame(page, text=" Website Credentials ", padding=25)
        pw_frame.pack(fill=tk.X, pady=(0, 30))

        # Dummy URLs synchronized with the scraper modules
        self.sites = {
            "PORTAL C (SECURE)": "https://example-enterprise-portal.com/", 
            "PORTAL B (ASSETS)": "https://example-asset-tracker.com/login", 
            "COMPLIANCE PORTAL X": "https://example-compliance-gateway.com/records"
        }
        
        ttk.Label(pw_frame, text="Target System:").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.site_var = tk.StringVar()
        cb = ttk.Combobox(pw_frame, textvariable=self.site_var, values=list(self.sites.keys()), state="readonly", width=35)
        cb.grid(row=0, column=1, sticky=tk.W, padx=15)
        cb.bind("<<ComboboxSelected>>", self.load_creds)
        
        ttk.Label(pw_frame, text="Login Email:").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.l_entry = ttk.Entry(pw_frame, width=38)
        self.l_entry.grid(row=1, column=1, sticky=tk.W, padx=15)
        
        ttk.Label(pw_frame, text="Vault Password:").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.p_entry = ttk.Entry(pw_frame, width=38)
        self.p_entry.grid(row=2, column=1, sticky=tk.W, padx=15)
        
        ttk.Button(pw_frame, text="Save Updates", style="Accent.TButton", command=self.save_creds).grid(row=3, column=1, sticky=tk.W, padx=15, pady=20)

        # Anti-Bot Profile Manager Section
        auth_frame = ttk.LabelFrame(page, text=" Anti-Bot Profile Authentication ", padding=25)
        auth_frame.pack(fill=tk.X)

        instr = (
            "PURPOSE:\n"
            "Certain legacy portals enforce strict anti-bot measures (e.g., Cloudflare Turnstile, WAF). "
            "This utility allows the operator to manually authenticate the browser profile to cache required security tokens.\n\n"
            "EXECUTION STEPS:\n"
            " 1. Click the 'Launch Manual Session' button below.\n"
            " 2. Complete the 'Verify you are human' or MFA security check.\n"
            " 3. Wait for the main dashboard to fully load.\n"
            " 4. CLOSE the browser manually to save the session state."
        )
        
        tk.Label(auth_frame, text=instr, font=("Segoe UI", 9), justify=tk.LEFT, wraplength=750, foreground="#555").pack(anchor="w", pady=(0, 20))
        ttk.Button(auth_frame, text="🌐 Launch Manual Auth Session", style="Accent.TButton", command=lambda: self.start_thread(self.refresh_portal_profile)).pack(anchor="w")

    # ==========================================
    # WINDOW: SYSTEM 
    # ==========================================
    def setup_system_page(self):
        page = self.pages["System"]
        tk.Label(page, text="System Maintenance", font=("Segoe UI Bold", 20), bg="white").pack(anchor="w", pady=(0, 25))
        
        f = ttk.LabelFrame(page, text=" Factory Reset ", padding=25)
        f.pack(fill=tk.X)
        
        msg = "WARNING: This will permanently delete the virtual environment and all cached browser profiles."
        tk.Label(f, text=msg, foreground="#d93025", font=("Segoe UI Semibold", 10), justify=tk.LEFT, wraplength=800).pack(pady=(0, 25), anchor="w")
        
        ttk.Button(f, text="PERFORM COMPLETE RESET", style="Accent.TButton", command=self.factory_reset).pack(anchor="w")

    # ==========================================
    # EXECUTION LOGIC & ROUTING
    # ==========================================
    def handle_launch(self, full_pipeline_func, selection, region_code):
        if "Full" in selection: 
            full_pipeline_func()
        else: 
            self.run_single_module(region_code, selection)

    def run_single_module(self, region_code: str, module: str):
        print(f"\n[USER] Task initiated: {module} ({region_code})")
        
        # Abstracted settings lookup
        s = ScraperSettings(region_code=region_code)
        
        try:
            if "Portal C" in module: PortalCScraper(s).run()
            elif "Portal A" in module: PortalAScraper(s).run()
            elif "Portal B" in module: PortalBScraper(s).run()
            elif "Secure Portal Y" in module: RegionYSecureScraper(s).run()
            elif "Compliance Portal X" in module: RegionXScraper(s).run()
            elif "Cleanup" in module:
                ExcelCleaner(s, "VENDOR_A_DATA", "Result").convert_and_replace()
                ExcelCleaner(s, "VENDOR_B_DATA", "Sheet1").convert_and_replace()
        except Exception as e: 
            print(f"[!] Critical execution error: {e}")

    def run_region_a(self):
        s = ScraperSettings(region_code="REG_A")
        # Executes multiple modules sequentially
        for bot in [PortalCScraper(s), PortalAScraper(s), PortalBScraper(s)]:
            try: 
                bot.run()
            except Exception as e: 
                print(f"[!] Sub-pipeline failed: {e}")

    def run_region_b(self):
        try: 
            RegionYSecureScraper(ScraperSettings(region_code="REG_B")).run()
        except Exception as e: 
            print(f"[!] Pipeline failed: {e}")

    def run_region_c(self):
        try: 
            RegionXScraper(ScraperSettings(region_code="REG_C")).run()
        except Exception as e: 
            print(f"[!] Pipeline failed: {e}")

    def run_region_d(self): 
        self.run_single_module("REG_D", "Cleanup")

    # ==========================================
    # CREDENTIALS VAULT LOGIC
    # ==========================================
    def load_creds(self, e=None):
        """Loads and masks credentials when a user selects a site from the dropdown."""
        url = self.sites.get(self.site_var.get())
        
        self.l_entry.delete(0, tk.END)
        self.p_entry.delete(0, tk.END)
        self.current_actual_password = ""
        self.current_masked_password = ""
        
        if url and self.secret_file.exists():
            data = json.load(open(self.secret_file))
            curr = data.get(url, {})
            
            self.l_entry.insert(0, curr.get("login", ""))
            
            pwd = curr.get("password", "")
            self.current_actual_password = pwd
            
            if pwd:
                if len(pwd) > 5:
                    masked = pwd[:5] + "*" * (len(pwd) - 5)
                else:
                    masked = pwd
                
                self.current_masked_password = masked
                self.p_entry.insert(0, masked)

    def save_creds(self):
        url = self.sites.get(self.site_var.get())
        if not url: return
        
        new_login = self.l_entry.get().strip()
        new_pwd_input = self.p_entry.get().strip()
        
        # If the user didn't change the masked string, keep the real password
        if new_pwd_input == self.current_masked_password:
            final_password = self.current_actual_password
        else:
            final_password = new_pwd_input 
            
        data = json.load(open(self.secret_file)) if self.secret_file.exists() else {}
        data[url] = {"login": new_login, "password": final_password}
        
        with open(self.secret_file, "w") as f: 
            json.dump(data, f, indent=4)
            
        messagebox.showinfo("Security", "Vault updated successfully.")
        
        self.current_actual_password = final_password
        if len(final_password) > 5:
            self.current_masked_password = final_password[:5] + "*" * (len(final_password) - 5)
        else:
            self.current_masked_password = final_password
            
        self.p_entry.delete(0, tk.END)
        self.p_entry.insert(0, self.current_masked_password)

    def refresh_portal_profile(self):
        """Opens a visible browser to allow manual solving of CAPTCHAs."""
        p_dir = Path.home() / "EdgeProfile_PortalA_Automation"
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=p_dir, 
                    channel="msedge", 
                    headless=False, 
                    no_viewport=True, 
                    ignore_default_args=["--enable-automation"], 
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
                )
                page = browser.pages[0]
                # Hide webdriver flag from basic bot detection
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page.goto("https://example-legacy-portal.com/main.xhtml")
                
                print("[SYS] Waiting for manual browser close...")
                page.wait_for_event("close", timeout=0)
                
            messagebox.showinfo("Success", "Security tokens cached. Profile updated.")
        except Exception as e: 
            print(f"[ERROR] Session failed: {e}")

    def factory_reset(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to perform a factory reset?"):
            v = Path(__file__).resolve().parent.parent / ".venv"
            b = Path.cwd() / "wipe.bat"
            with open(b, "w") as f: 
                f.write(f'@echo off\ntaskkill /f /im python.exe /t\nrmdir /s /q "{v}"\ndel "%~f0"\nexit\n')
            os.startfile(b)
            self.root.destroy()

    def start_thread(self, func): 
        """Utility to launch blocking tasks in background threads."""
        threading.Thread(target=func, daemon=True).start()
        
    def on_closing(self): 
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = EnterpriseAutomationApp(root)
    root.mainloop()