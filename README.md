# 🌍 Multi-Region RPA Data Extraction Pipeline

**A robust, multi-threaded robotic process automation (RPA) suite designed to orchestrate complex data extraction workflows across 6 distinct secure, legacy, and SPA web portals.** Built to eliminate manual data entry and ingestion bottlenecks for data analysts.

> ⚠️ **NDA Disclaimer:** *This repository contains a white-labeled, generalized version of a proprietary system I architected and developed for a Top-Tier Global Enterprise. Sensitive data and business logic have been fully anonymized.*

### 🚀 Tech Stack
* **Core:** Python 3.12+, Strict OOP Architecture
* **Orchestration:** Multi-threaded Task Manager (`app.py`), CSV/Excel Queue Processing
* **Web Automation:** Playwright (Headless & Hybrid mode)
* **Data Engineering:** Pandas, Pydantic, Openpyxl
* **Evasion & Security:** 2FA/CAPTCHA Fallback Modules, Encrypted `json` Credential Vault

---

## 💼 Real-World Business Impact 

This is a mission-critical operations tool actively used to orchestrate complex data ingestion and resolve severe bottlenecks.

* 📈 **10+ Hours Saved Weekly:** Completely eliminated manual copy-pasting across 4 regional hubs.
* 💰 **SLA Penalty Reduction:** Definitively rejected third-party vendor penalties using standardized, automated timestamp capture.
* 🎯 **100% Data Accuracy:** Replaced error-prone manual entry with a standardized Pandas-based ETL pipeline.

---

## 🏗 Automation Architecture & Data Journey

The application is a suite of Python automation scripts, with each script acting as a specialized, request-driven data fetching tool for a specific website. The core design principle is to provide a reliable, automated bridge between an analyst's Excel requests and the target web portal.

The system performs a direct, one-to-one request-to-delivery loop for each scraping task:

### 1. Request Ingestion (Input)
The process begins when an analyst places a request-specific Excel file into a shared location. The pipeline ingests this file, extracting the detailed data requests for the target website.

### 2. Targeted Web Automation (Execution)
The corresponding multi-threaded Playwright script is launched. It performs the following sequential actions:

* **Secure Authentication:** Automatically logs into secure portals using encrypted local credentials.
* **Verification Traversal:** Robustly handles logic (like 2FA/CAPTCHA), pausing for manual clearance if needed, ensuring session clearance.
* **Targeted Scraping:** Navigates the portal to fetch precisely the data requested in the input file.

### 3. Data Cleansing & Final Delivery (Output)
Retrieved web data is immediately structured, cleaned, and standardized using Pandas-based logic to ensure accuracy and consistency. The script then generates professional Excel reports and delivers them directly back to the shared location (e.g., SharePoint). These finalized datasets serve as the primary input source for automated Power BI dashboards, eliminating manual data handling in the business intelligence pipeline.

---

## 🛠 Key Engineering Features

* **Multi-Threaded GUI (`app.py`):** Built a responsive, DPI-aware Tkinter interface using `sv_ttk`. Heavy RPA workloads are dispatched to background daemon threads, keeping the UI fully interactive during extractions.
* **Self-Healing Launcher (`System_Launcher.bat`):** A robust deployment script that automatically provisions the Python `.venv`, resolves dependencies, and repairs broken environments without user intervention.
* **Emergency OS-Level Reset (`Emergency_Reset.bat`):** A critical failure isolation tool that performs OS-level `taskkill` sweeps on zombie browser processes, preventing memory leaks and data corruption.
* **Dual-Channel Logging:** Detailed, method-level debug logs are routed to rotating text files for troubleshooting, while clean operational outputs are streamed in real-time to the GUI console.

---

## 📂 Project Structure

```text
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
 ┣ 📜 app.py                  # Main GUI Application & Thread Orchestrator
 ┣ 📜 Emergency_Reset.bat     # OS-level deep cleanup tool (Fault isolation)
 ┣ 📜 System_Launcher.bat     # Self-healing environment provisioner (Launcher)
 ┗ 📜 requirements.txt        # Python dependency manifest
