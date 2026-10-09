# SIMBA Financial Report Generator

Automate manual faculty financial account monitoring with a zero-installation web app. This code enables uploading SIMBA CSV files directly in the browser to instantly generate individual department balance summaries (PDF + CSV format), departmental dashboards, and 12-month spend forecasts with risk alerts. Built with Streamlit for Penn State faculty and staff to monitor budgets, track spending rates, and identify overspend risks before year-end without requiring any software installation on local machines.

## How to Access

**Live App:** [INSERT_STREAMLIT_URL_HERE]

Simply click the link and start uploading your SIMBA files. No login required.

## Technical Details

Built with Streamlit for instant deployment to the cloud. Processes CSV/Excel files in-memory without storing data. Generates PDF reports and CSV exports on-the-fly.

**Requirements:** `streamlit`, `pandas`, `numpy`, `fpdf2`, `openpyxl` (auto-installed by Streamlit Cloud)
