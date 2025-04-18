# CUB Admin Tools Demo

This multi-page Streamlit application provides administrative tools for CUB data analysis.

## Features

### 1. Revenue Analysis
- UUID Matching Analysis: Identifies records present in both systems
- Missing Records Detection: Finds records that exist in Buyer dashboard but are missing from CUB
- Data Quality Issues: Identifies potential data problems like missing values
- Revenue Discrepancies: Compares revenue values between systems for matching records

### 2. Publisher Policies Analysis
- Policy Count Analysis: Count policies by publisher
- CPA Analysis: Calculate CPA metrics by publisher
- Data Exploration: Explore and filter policy data
- Phone Number Matching: Match phone numbers between policy data and Ringba call logs

### 3. Redtrack Conversion Tool
- Conversion Format Creation: Converts Ringba call logs to the required conversion upload format
- Multiple Conversion Types: Supports 20+ conversion types (50m, 5m, Lead, etc.)
- Timestamp Adjustment: Automatically adds 4 hours to timestamps
- Custom Payouts: Set custom payout values for specific conversion types

## How to Use

1. Select the tool you need from the sidebar
2. Upload your data files
3. Follow the on-screen instructions

### Revenue Analysis
1. Upload your Buyer Dashboard CSV (requires Ringba Call UUID and Revenue columns)
2. Upload your CUB Ringba Dashboard CSV (requires Inbound Call ID and Revenue columns)
3. Optionally upload a CUB Retreaver Dashboard CSV for additional matching capability
4. Click the "Generate Analysis Report" button
5. Review the analysis results across the different tabs

### Publisher Policies Analysis
1. Upload your Policies CSV file (requires ANI and Buyer/Publisher columns)
2. Upload your Ringba Call Log Export CSV (optional, for CPA analysis)
3. Use the various tabs to analyze the data

### Redtrack Conversion Tool
1. Export your call log data from Ringba
2. Select the conversion type from the dropdown
3. Set the payout value if needed
4. Upload the CSV file
5. Click "Generate Conversion File"
6. Download the formatted conversion file

## Sample Data

Example data files are provided in the `example_data` directory to demonstrate how each app works:

**Revenue Analysis:**
- `sample_buyer_dashboard.csv`: Example Buyer dashboard data
- `sample_cub_dashboard.csv`: Example CUB dashboard data

**Publisher Policies Analysis:**
- `sample_policies.csv`: Example Policies data with ANI and Buyer columns
- `sample_ringba_calls.csv`: Example Ringba call log data

## Local Development

To run this app locally:

```bash
pip install -r requirements.txt
streamlit run Home.py
``` 
