import streamlit as st
import os

st.set_page_config(
    page_title="CUB Admin Tools Demo",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CUB Admin Tools Demo")

st.markdown("""
This application provides administrative tools for CUB data analysis:

### 🔍 Available Tools:

**1. Revenue Analysis** - Analyze missing revenue between Buyer and CUB dashboard data:
- Match records by UUID or Caller ID
- Find missing records
- Analyze data quality issues
- Detect revenue discrepancies

**2. Publisher Policies Analysis** - Analyze policy data by publisher:
- Match phone numbers between policy data and Ringba call logs
- Calculate policy counts
- Perform CPA analysis by publisher

**3. Redtrack Conversion Tool** - Convert Ringba call logs to conversion format:
- Select conversion type from multiple options
- Adjust timestamps automatically (+4 hours)
- Set custom payout values for specific conversion types
- Generate ready-to-upload conversion files

### 📋 Getting Started:

1. Select the tool you need from the sidebar
2. Upload your data files
3. Follow the on-screen instructions

### 📚 Sample Data:

Each tool has sample data available for testing.
""")

# Show sample data information
st.subheader("Sample Data Files")

# Check for sample data
sample_buyer_path = "example_data/sample_buyer_dashboard.csv"
sample_cub_path = "example_data/sample_cub_dashboard.csv"
sample_policies_path = "example_data/sample_policies.csv"
sample_ringba_path = "example_data/sample_ringba_calls.csv"

col1, col2 = st.columns(2)

with col1:
    st.write("##### Revenue Analysis Sample Files:")
    if os.path.exists(sample_buyer_path) and os.path.exists(sample_cub_path):
        st.success("✅ Sample data available for Revenue Analysis")
    else:
        st.warning("⚠️ Sample data not available for Revenue Analysis")

with col2:
    st.write("##### Publisher Policies Sample Files:")
    if os.path.exists(sample_policies_path) and os.path.exists(sample_ringba_path):
        st.success("✅ Sample data available for Publisher Policies Analysis")
    else:
        st.warning("⚠️ Sample data not available for Publisher Policies Analysis")

# Add a footer
st.markdown("""
---
### 📞 Support


*Version 1.0.0*
""") 
