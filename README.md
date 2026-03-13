# 🌍 Enterprise ETL & Data Orchestration Pipeline (Deployed in Production)

![Production](https://img.shields.io/badge/Status-Active_Production-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white&style=for-the-badge)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458?logo=pandas&logoColor=white&style=for-the-badge)
![Playwright](https://img.shields.io/badge/Playwright-Web_Scraping-2EAD33?logo=playwright&logoColor=white&style=for-the-badge)

> ⚠️ **NDA Disclaimer:** *This repository contains a white-labeled, generalized version of a proprietary system I architected and developed for a Top-Tier Global Enterprise. Sensitive business logic, credentials, and identifiable data have been fully anonymized to comply with strict NDA policies.*

## 💼 Real-World Business Impact 

This is not a portfolio "pet project" — this is a **mission-critical business tool** actively used by operations specialists to orchestrate complex cross-border enterprise data. 

Before this application, the company's data ingestion was a massive manual bottleneck due to legacy third-party portals heavily protected by anti-bot systems.

**Measurable Results Delivered to the Business:**
* 💰 **Drastic Penalty Cost Reduction (SLA & Vendor Fees):** By automatically capturing highly granular operational timestamps across the asset lifecycle, the business gained the ability to accurately pinpoint liability for processing delays. This allowed the company to definitively contest and reject unjustified third-party vendor penalties, directly saving significant operational costs.
* 📈 **10+ Hours Saved Weekly:** Completely eliminated manual data entry for operators across 4 different regional hubs.
* 🎯 **100% Data Accuracy:** Replaced error-prone manual copy-pasting with a standardized Pandas-based ETL transformation pipeline.
* 🛡️ **Zero Downtime:** Successfully bypassed complex CAPTCHA and 2FA blockers that previously prevented direct API integrations.

---

## 🏛️ Architectural Decision: Why Local Desktop instead of Cloud/SQL?

A common question is why this pipeline wasn't deployed on a cloud server (AWS/GCP) writing to a traditional SQL database. This architecture was explicitly chosen to navigate strict corporate realities:

1. **Strict Corporate IT & Security Policies:** Deploying external cloud infrastructure or provisioning internal SQL databases requires months of bureaucratic approvals in a highly locked-down enterprise environment. A local, self-contained Python application delivered immediate ROI without violating security policies.
2. **Web Application Firewalls & IP Reputation:** Target vendor portals aggressively block traffic originating from Data Center IPs (AWS/Azure). Running the extraction locally utilizes trusted corporate network gateways, naturally bypassing IP-based bot detection.
3. **Human-in-the-Loop (MFA/CAPTCHA):** Several legacy systems require manual 2FA verification or visual CAPTCHA solving. A local Tkinter GUI allows the operator to seamlessly take control, authenticate, and hand the session back to the automated headless pipeline—something highly complex and brittle to achieve on a remote cloud server.
4. **End-User Data Portability:** The primary stakeholders rely entirely on Excel for their downstream operations. The pipeline natively integrates with their existing workflow, transforming messy web data into clean, historicized local datasets without requiring them to learn SQL.

---

An end-to-end, multi-threaded desktop application designed to automate complex **ETL (Extract, Transform, Load)** workflows across secure, legacy third-party web portals.

## 🏗 System Architecture & ETL Flow

The application is structured using strict **OOP** principles, cleanly separating the UI orchestration layer from the underlying data engineering engines.

### 1. Extract (Automated Web Extraction)
* **Anti-Bot Evasion:** Engineered persistent browser sessions (`user_data_dir`) using Playwright to bypass advanced anti-bot protections (e.g., Cloudflare Turnstile). Includes a "Hybrid Automation" fallback allowing manual 2FA/CAPTCHA clearance to cache security tokens.
* **Complex SPA Handling:** Navigates modern React/Material-UI Single Page Applications using explicit waits, DOM state validation (`networkidle`), and JavaScript click injections to handle overlay blockers.
* **Legacy iFrame Support:** Successfully targets and parses deep DOM structures within outdated corporate iFrame applications.

### 2. Transform (Data Cleansing & Validation)
* **Legacy Format Conversion:** The `ExcelCleaner` module utilizes `xlrd` and `openpyxl` to automatically intercept outdated `.xls` system exports and convert them to modern `.xlsx` formats.
* **Dynamic Header Detection:** Implements heuristic scanning to dynamically locate true data headers in messy vendor exports (bypassing variable amounts of garbage metadata rows at the top of files).
* **Regex Data Validation:** Validates input queues (e.g., standardized 11-character alphanumeric IDs) before initiating heavy browser operations to ensure data quality and prevent pipeline crashes.

### 3. Load (Archiving & State Management)
* **Master Database Synchronization:** Extracted records are appended to a historical Master Archive. Uses `pandas` to perform upsert-like operations, dropping exact duplicates (ignoring ingestion timestamps) to maintain a clean local data warehouse.
* **Encrypted Credential Vault:** Securely manages system passwords locally via `json`, keeping sensitive data out of the source code.

---

## 🛠 Key Engineering Features

* **Multi-Threaded GUI (`app.py`):** Built a responsive, DPI-aware Tkinter interface using `sv_ttk` for modern styling. Heavy extraction workloads are dispatched to background daemon threads, keeping the UI fully interactive.
* **Self-Healing Launcher (`System_Launcher.bat`):** A robust deployment script that automatically provisions the Python `.venv`, resolves dependencies, checks for a system Python installation (and redirects to the MS Store if missing), and repairs broken environments without user intervention.
* **Dual-Channel Logging:** Implemented a custom `logging` configuration. Detailed, method-level debug logs are routed to rotating text files for developer troubleshooting, while clean operational outputs are streamed in real-time to the GUI console.
* **Graceful Failure & Recovery:** Features robust try/except blocks capable of detecting manual browser closures, automatically escaping trapped UI modals via keystrokes, and executing OS-level `taskkill` sweeps to prevent memory leaks from zombie processes.

---

## 📂 Project Structure

📦 Enterprise-ETL-Pipeline
 ┣ 📂 core/                   # Core Data Engineering & Automation logic
 ┃ ┣ 📜 __init__.py
 ┃ ┣ 📜 base_scraper.py       # Base OOP class (Browser init, context management)
 ┃ ┣ 📜 config.py             # Pydantic-based settings and path routing (DRY)
 ┃ ┣ 📜 excel_cleaner.py      # Pandas-based data transformation utility
 ┃ ┣ 📜 logger.py             # Dual-channel custom logging engine
 ┃ ┗ 📜 settings_manager.py   # CLI utility for credential and profile management
 ┣ 📂 scrapers/               # Isolated extraction modules per data source
 ┃ ┣ 📜 __init__.py
 ┃ ┣ 📜 portal_a_scraper.py   # Legacy iFrame extraction logic
 ┃ ┣ 📜 portal_b_scraper.py   # Asset tracking and retry-loop logic
 ┃ ┣ 📜 portal_c_scraper.py   # Secure compliance portal logic
 ┃ ┣ 📜 region_x_scraper.py   # SPA dynamic dropdown extraction logic
 ┃ ┗ 📜 region_y_scraper.py   # Region-specific secure portal logic
 ┣ 📂 tests/                  # Automated testing suite (pytest)
 ┣ 📜 main.py                 # Main GUI Application & Thread Orchestrator
 ┣ 📜 Emergency_Reset.bat     # OS-level deep cleanup tool (Fault isolation)
 ┣ 📜 System_Launcher.bat     # Self-healing environment provisioner (Launcher)
 ┗ 📜 requirements.txt        # Python dependency manifest