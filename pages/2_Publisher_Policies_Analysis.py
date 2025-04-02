import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import re

st.set_page_config(page_title="Publisher Policy Tracker", layout="wide")

st.title("Policy Issuance Tracker")

# Clean phone number function
def clean_phone_number(phone, is_policies=False):
    """Clean phone numbers to a standard format for matching"""
    if pd.isna(phone):
        return ""
    
    # Convert to string
    phone = str(phone)
    
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Handle different cases
    if is_policies:
        # For ANI values from policies file, add "1" prefix if needed
        if len(phone) == 10 and not phone.startswith('1'):
            phone = '1' + phone
    else:
        # For Ringba values, check if it has a +1 format and extract the right portion
        if len(phone) > 10:
            # If it starts with 1 and is longer than 10, assume country code format
            if phone.startswith('1') and len(phone) == 11:
                # This is likely a 1XXXXXXXXXX format, keep as is
                pass
            else:
                # This could be other format with extra digits, keep the last 10 or 11 digits
                if len(phone) > 11:
                    phone = phone[-11:] if phone[-11] == '1' else phone[-10:]
    
    # Make sure we return either a 10-digit or 11-digit (with leading 1) number
    if len(phone) == 10:
        # For consistent matching, if we're evaluating policies, add the 1
        if is_policies:
            phone = '1' + phone
    
    return phone

# File upload section
st.header("Upload Policy Data")

col1, col2 = st.columns(2)

with col1:
    policies_file = st.file_uploader("Upload Policies CSV file (ANI, Buyer)", 
                                   type=['csv'], 
                                   key="policy_csv_upload")
    st.caption("Upload file containing ANI (phone numbers) and Buyer/Publisher information")

with col2:
    ringba_file = st.file_uploader("Upload Ringba Call Log Export CSV", 
                                  type=['csv'], 
                                  key="ringba_csv_upload")
    st.caption("Upload Ringba call log file to compare with Policies data")

# Settings and filters section
st.sidebar.header("Analysis Settings")

# Function to analyze publisher policy data
def analyze_policies_data(policies_df, ringba_df=None):
    # Make a copy to avoid modifying the original
    policies_df = policies_df.copy()
    if ringba_df is not None:
        ringba_df = ringba_df.copy()
    
    # Initialize variables to avoid "referenced before assignment" errors
    caller_id_col = None
    number_col = None
    
    # Check if Publisher column is in the Ringba file rather than the Policies file
    publisher_in_ringba = ringba_df is not None and "Publisher" in ringba_df.columns
    publisher_in_policies = "Buyer" in policies_df.columns or "Publisher" in policies_df.columns
    
    if publisher_in_ringba:
        st.info("Found 'Publisher' column in the Ringba data file. Using this for publisher analysis.")
    else:
        # Original approach - use Buyer column from policies file
        if "Buyer" in policies_df.columns and not "Publisher" in policies_df.columns:
            policies_df = policies_df.rename(columns={"Buyer": "Publisher"})
            st.success("Renamed 'Buyer' column to 'Publisher' for analysis")
    
    if "ANI" in policies_df.columns and not "Policy Number" in policies_df.columns:
        # Clean the phone numbers
        policies_df["Clean ANI"] = policies_df["ANI"].apply(clean_phone_number, is_policies=True)
        policies_df = policies_df.rename(columns={"ANI": "Policy Number"})
        st.success("Using ANI (phone numbers) as unique policy identifiers")
    
    # Create tabs for different analyses
    if ringba_df is not None:
        tabs = st.tabs(["Policy Count", "CPA Analysis", "Publisher Details", "Data Explorer", "File Comparison"])
    else:
        tabs = st.tabs(["Policy Count", "Publisher Details", "Data Explorer"])
    
    # TAB 1: Policy Count Analysis
    with tabs[0]:
        # If Publisher is in Ringba, we need a different approach
        if publisher_in_ringba:
            st.header("Policy Count by Publisher (from Ringba Data)")
            
            # Count policies by publisher in Ringba data
            policy_counts = ringba_df['Publisher'].value_counts().reset_index()
            policy_counts.columns = ['Publisher', 'Policy Count']
        else:
            st.header("Policy Count by Publisher (from Policy Data)")
            
            # Count policies by publisher in Policies data
            policy_counts = policies_df['Publisher'].value_counts().reset_index()
            policy_counts.columns = ['Publisher', 'Policy Count']
        
        # Display total stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Publishers", len(policy_counts))
        with col2:
            st.metric("Total Policies", policy_counts['Policy Count'].sum())
        with col3:
            avg_policies = policy_counts['Policy Count'].mean()
            st.metric("Avg Policies per Publisher", f"{avg_policies:.1f}")
        
        # Display results as a bar chart
        st.subheader("Publisher Performance")
        
        chart_type = st.radio("Chart type:", ["Bar Chart", "Pie Chart"], horizontal=True)
        
        # Sort options
        sort_by = st.radio("Sort by:", ["Policy Count (High to Low)", "Policy Count (Low to High)", "Publisher Name"], horizontal=True)
        
        if sort_by == "Policy Count (High to Low)":
            policy_counts = policy_counts.sort_values('Policy Count', ascending=False)
        elif sort_by == "Policy Count (Low to High)":
            policy_counts = policy_counts.sort_values('Policy Count', ascending=True)
        else:  # Publisher Name
            policy_counts = policy_counts.sort_values('Publisher')
        
        # Number of publishers to display
        top_n = st.slider("Number of publishers to display:", min_value=1, max_value=max(len(policy_counts), 1), value=min(20, len(policy_counts)))
        
        # Get the top N publishers
        display_data = policy_counts.head(top_n)
        
        # Create and display the chart
        if chart_type == "Bar Chart":
            fig = px.bar(
                display_data,
                x='Publisher',
                y='Policy Count',
                title=f"Top {top_n} Publishers by Policy Count",
                color='Policy Count',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:  # Pie Chart
            fig = px.pie(
                display_data,
                names='Publisher',
                values='Policy Count',
                title=f"Policy Distribution Across Top {top_n} Publishers"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Display the data table
        st.subheader("Publisher Policy Data")
        st.dataframe(policy_counts, use_container_width=True)
        
        # Download option
        csv = policy_counts.to_csv(index=False)
        st.download_button(
            label="Download Publisher Policy Counts CSV",
            data=csv,
            file_name="publisher_policy_counts.csv",
            mime="text/csv"
        )
    
    # TAB 2: CPA Analysis (when Ringba data is available)
    if ringba_df is not None:
        with tabs[1]:
            st.header("CPA Analysis by Publisher")
            st.info("Total_Revenue shows the sum of all revenue per publisher from the Ringba file, regardless of policy count.")
            st.info("Policy_Count represents the matches between ANI in policies file and Number column in Ringba file.")
            st.info("Note: ANI values from policies file are formatted to match Ringba's Number format by adding a '1' prefix when needed.")
            
            # Try to identify Revenue column in Ringba data
            revenue_columns = []
            for col in ringba_df.columns:
                if any(term in col.lower() for term in ['revenue', 'payout', 'cost', 'price', 'amount', 'value', 'cpa']):
                    revenue_columns.append(col)
            
            if revenue_columns:
                # Let user select the revenue column if multiple are found
                if len(revenue_columns) > 1:
                    ringba_revenue_col = st.selectbox("Select revenue column from Ringba data:", revenue_columns)
                else:
                    ringba_revenue_col = revenue_columns[0]
                    st.success(f"Using '{ringba_revenue_col}' as revenue column from Ringba data")
                
                # Identify the Number column in Ringba data
                number_col = None
                if "Number" in ringba_df.columns:
                    number_col = "Number"
                    st.success(f"Using 'Number' column from Ringba data for policy matching")
                else:
                    # Try to identify a suitable number column
                    phone_columns = []
                    for col in ringba_df.columns:
                        if any(term in col.lower() for term in ['number', 'ani', 'phone', 'caller']):
                            phone_columns.append(col)
                    
                    if phone_columns:
                        if len(phone_columns) > 1:
                            number_col = st.selectbox("Select phone number column from Ringba data:", phone_columns)
                        else:
                            number_col = phone_columns[0]
                            st.success(f"Using '{number_col}' column from Ringba data for policy matching")
                    else:
                        st.error("Could not find a suitable column for phone numbers in Ringba data")
                
                # Check for Caller ID column which is what we should match for policies
                caller_id_col = None
                for col in ringba_df.columns:
                    if "caller" in col.lower() and "id" in col.lower():
                        caller_id_col = col
                        st.success(f"Found Caller ID column in Ringba data: {caller_id_col}")
                        break
                
                if caller_id_col:
                    # Clean the Caller ID values instead of Number for matching policies
                    ringba_df['Clean Number'] = ringba_df[caller_id_col].apply(clean_phone_number, is_policies=False)
                    st.info(f"Using '{caller_id_col}' for the Clean Number field to match against policy ANIs")
                elif number_col:
                    # Use Number as fallback if no Caller ID
                    ringba_df['Clean Number'] = ringba_df[number_col].apply(clean_phone_number, is_policies=False)
                    st.warning(f"No Caller ID column found. Using '{number_col}' column for matching instead.")
                else:
                    st.error("Could not find Caller ID or Number column for policy matching")
                
                # Make sure to clean phone numbers in both datasets for matching
                if "Clean ANI" not in policies_df.columns and "ANI" in policies_df.columns:
                    policies_df["Clean ANI"] = policies_df["ANI"].apply(clean_phone_number, is_policies=True)
                
                if number_col and publisher_in_ringba:
                    # Clean the phone numbers in Ringba data
                    ringba_df['Clean Number'] = ringba_df[number_col].apply(clean_phone_number, is_policies=False)
                    
                    # Show some sample cleaned values for debugging
                    st.subheader("Sample Number Matching")
                    
                    # Show a few sample ANIs from policies
                    st.write("Sample ANIs from policies file (after cleaning):")
                    if not policies_df.empty and 'Clean ANI' in policies_df.columns:
                        sample_anis = policies_df['Clean ANI'].head(10).tolist()
                        st.write(sample_anis)
                    
                    # Check for Caller ID column 
                    for col in ringba_df.columns:
                        if "caller" in col.lower() and "id" in col.lower():
                            caller_id_col = col
                            st.success(f"Found Caller ID column in Ringba data: {caller_id_col}")
                            break
                    
                    # Show sample clean Number and Caller ID values from Ringba
                    if caller_id_col:
                        st.write(f"Sample values from Ringba file (Number and {caller_id_col}):")
                        sample_numbers = {}
                        for idx, row in ringba_df.head(10).iterrows():
                            clean_number = clean_phone_number(row[number_col], is_policies=False)
                            clean_caller_id = clean_phone_number(row[caller_id_col], is_policies=False)
                            sample_numbers[idx] = {
                                'Original Number': row[number_col],
                                'Clean Number': clean_number,
                                f'Original {caller_id_col}': row[caller_id_col],
                                f'Clean {caller_id_col}': clean_caller_id
                            }
                        st.table(pd.DataFrame.from_dict(sample_numbers, orient='index'))
                    else:
                        # Just show the Number column if no Caller ID is available
                        st.write("Sample values from Ringba file (Number only):")
                        sample_numbers = {}
                        for idx, row in ringba_df.head(10).iterrows():
                            clean_number = clean_phone_number(row[number_col], is_policies=False)
                            sample_numbers[idx] = {
                                'Original Number': row[number_col],
                                'Clean Number': clean_number
                            }
                        st.table(pd.DataFrame.from_dict(sample_numbers, orient='index'))
                    
                    # Convert revenue to numeric
                    ringba_df['Revenue'] = pd.to_numeric(ringba_df[ringba_revenue_col], errors='coerce')
                    
                    # Calculate total revenue by Publisher directly from Ringba data
                    publisher_revenue = ringba_df.groupby('Publisher')['Revenue'].sum().reset_index()
                    publisher_revenue.columns = ['Publisher', 'Total_Revenue']
                    
                    # Count policies by matching ANI to Number
                    # First, get all clean ANIs from policies file
                    policy_anis = set(policies_df["Clean ANI"].astype(str))
                    
                    # Check which column might contain the phone numbers that would match ANI
                    # Look for Caller ID field since we're finding no matches with the Number field
                    caller_id_col = None
                    for col in ringba_df.columns:
                        if "caller" in col.lower() and "id" in col.lower():
                            caller_id_col = col
                            st.success(f"Found Caller ID column in Ringba data: {caller_id_col}")
                            break
                    
                    # For each publisher, count how many of their numbers match with policy ANIs
                    publisher_policy_counts = []
                    for publisher in publisher_revenue['Publisher'].unique():
                        publisher_data = ringba_df[ringba_df['Publisher'] == publisher]
                        
                        # Try matching both Number and Caller ID (if available)
                        publisher_numbers = set(publisher_data['Clean Number'].astype(str))
                        matching_policies = len(policy_anis.intersection(publisher_numbers))
                        
                        # If we found a Caller ID column, also check for matches there
                        if caller_id_col:
                            # Clean the Caller ID values
                            publisher_data['Clean Caller ID'] = publisher_data[caller_id_col].apply(clean_phone_number, is_policies=False)
                            publisher_caller_ids = set(publisher_data['Clean Caller ID'].astype(str))
                            
                            # Add matches from Caller ID
                            caller_id_matches = len(policy_anis.intersection(publisher_caller_ids))
                            st.write(f"Publisher {publisher}: Found {matching_policies} matches in Number and {caller_id_matches} in Caller ID")
                            
                            # Use total unique matches (avoid double counting)
                            all_numbers = publisher_numbers.union(publisher_caller_ids)
                            matching_policies = len(policy_anis.intersection(all_numbers))
                        
                        publisher_policy_counts.append({
                            'Publisher': publisher,
                            'Policy_Count': matching_policies
                        })
                    
                    # Create a dataframe from the counts
                    publisher_counts = pd.DataFrame(publisher_policy_counts)
                    
                    # Merge with revenue data, ensuring we keep all publishers from revenue data
                    publisher_stats = pd.merge(publisher_revenue, publisher_counts, on='Publisher', how='left')
                    publisher_stats = publisher_stats.fillna(0)
                    
                    # Calculate CPA (Cost Per Acquisition)
                    publisher_stats['CPA'] = publisher_stats['Total_Revenue'] / publisher_stats['Policy_Count']
                    publisher_stats['CPA'] = publisher_stats['CPA'].replace([np.inf, -np.inf], 0)
                    
                    st.info("Policy_Count shows matches between ANI in policies file and Number in Ringba file per publisher.")
                    
                    # Format the metrics for display
                    publisher_stats_display = publisher_stats.copy()
                    publisher_stats_display['Total_Revenue'] = publisher_stats_display['Total_Revenue'].map('${:,.2f}'.format)
                    publisher_stats_display['CPA'] = publisher_stats_display['CPA'].map('${:,.2f}'.format)
                    
                    # Display CPA metrics
                    st.subheader("CPA by Publisher")
                    st.dataframe(publisher_stats_display[['Publisher', 'Policy_Count', 'Total_Revenue', 'CPA']], use_container_width=True)
                    
                    # Total revenue bar chart (sorted by highest revenue)
                    fig = px.bar(
                        publisher_stats.sort_values('Total_Revenue', ascending=False),
                        x='Publisher',
                        y='Total_Revenue',
                        title="Total Revenue by Publisher (Sorted by Revenue)",
                        color='Total_Revenue',
                        color_continuous_scale='Viridis',
                        labels={'Total_Revenue': 'Total Revenue ($)', 'Publisher': 'Publisher'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # CPA bar chart (sorted by highest CPA)
                    fig = px.bar(
                        publisher_stats.sort_values('CPA', ascending=False),
                        x='Publisher',
                        y='CPA',
                        title="Cost Per Acquisition by Publisher (Sorted by CPA)",
                        color='CPA',
                        color_continuous_scale='Viridis',
                        labels={'CPA': 'CPA ($)', 'Publisher': 'Publisher'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Download option
                    csv = publisher_stats.to_csv(index=False)
                    st.download_button(
                        label="Download CPA Analysis CSV",
                        data=csv,
                        file_name="publisher_cpa_analysis.csv",
                        mime="text/csv"
                    )
                    
                    # Add download button for processed Ringba data with all columns
                    st.subheader("Download Full Processed Ringba Data")
                    st.info("Download the complete Ringba data with all original columns plus the processed Clean Number field and an 'Is_Policy' column that indicates whether each record matches with an ANI in the policies file (True or False).")
                    
                    # Prepare the download CSV with all original columns
                    # Add a Policy column to indicate whether each record matches with a policy
                    policy_anis = set(policies_df["Clean ANI"].astype(str))
                    
                    # Create a copy of ringba_df for download to avoid modifying the original
                    ringba_download_df = ringba_df.copy()
                    
                    # Ensure the Clean Number comes from the Caller ID column rather than the Number column
                    if caller_id_col:
                        ringba_download_df['Clean Number'] = ringba_download_df[caller_id_col].apply(clean_phone_number, is_policies=False)
                        # Also add a Clean Caller ID field for more explicit matching
                        ringba_download_df['Clean Caller ID'] = ringba_download_df[caller_id_col].apply(clean_phone_number, is_policies=False)
                        st.info(f"Using '{caller_id_col}' for Clean Number in the downloaded data for better matching with policies")
                    elif number_col:
                        ringba_download_df['Clean Number'] = ringba_download_df[number_col].apply(clean_phone_number, is_policies=False)
                    
                    # Add Policy column showing if the number or caller ID matches a policy
                    def is_policy(row):
                        # Check if Clean Number matches a policy ANI
                        if 'Clean Number' in ringba_download_df.columns and not pd.isna(row['Clean Number']):
                            clean_number = str(row['Clean Number'])
                            if clean_number in policy_anis:
                                return True
                                
                        # Also check Clean Caller ID if it exists
                        if 'Clean Caller ID' in ringba_download_df.columns and not pd.isna(row['Clean Caller ID']):
                            clean_caller_id = str(row['Clean Caller ID'])
                            if clean_caller_id in policy_anis:
                                return True
                                
                        # Check raw caller ID with basic cleaning as a fallback
                        if caller_id_col and not pd.isna(row[caller_id_col]):
                            caller_id = clean_phone_number(row[caller_id_col], is_policies=False)
                            if caller_id in policy_anis:
                                return True
                                
                        # If we get here, no match was found
                        return False
                    
                    # Add some debugging information
                    st.subheader("Debugging Policy Matching")
                    with st.expander("View policy matching details"):
                        st.write("Policy ANIs (first 10):", list(policy_anis)[:10])
                        
                        # Show some sample Clean Number values from Ringba
                        sample_clean_numbers = []
                        for idx, row in ringba_download_df.head(10).iterrows():
                            if 'Clean Number' in ringba_download_df.columns:
                                sample_clean_numbers.append(str(row['Clean Number']))
                        st.write("Sample Clean Numbers from Ringba (first 10):", sample_clean_numbers)
                        
                        # Check for any matches
                        matches_found = [num for num in sample_clean_numbers if num in policy_anis]
                        st.write(f"Matches found in sample: {len(matches_found)}")
                        if matches_found:
                            st.write("Sample matches:", matches_found)
                        else:
                            st.warning("No matches found in sample - this is likely why all Is_Policy values are False")
                            
                        # Try direct string matching
                        st.write("Trying direct string matching between sample numbers and ANIs")
                        for clean_num in sample_clean_numbers:
                            for ani in list(policy_anis)[:20]:  # Check first 20 ANIs
                                if clean_num == ani:
                                    st.success(f"Match found: {clean_num} == {ani}")
                                elif clean_num in ani or ani in clean_num:
                                    st.info(f"Partial match: {clean_num} vs {ani}")
                    
                    # Apply the function to determine policy match status
                    ringba_download_df['Is_Policy'] = ringba_download_df.apply(is_policy, axis=1)
                    
                    # Check if any rows were marked as True
                    policy_match_count = ringba_download_df['Is_Policy'].sum()
                    if policy_match_count == 0:
                        st.warning(f"No matches found - all {len(ringba_download_df)} rows have Is_Policy = False")
                    else:
                        st.success(f"Found {policy_match_count} rows with Is_Policy = True")
                    
                    # Check raw caller ID column for direct matches
                    if caller_id_col:
                        # Check which column to use for ANI values
                        if 'ANI' in policies_df.columns:
                            ani_list = [str(ani).lower() for ani in policies_df['ANI'].tolist()]
                        elif 'Policy Number' in policies_df.columns:
                            ani_list = [str(ani).lower() for ani in policies_df['Policy Number'].tolist()]
                        elif 'Clean ANI' in policies_df.columns:
                            ani_list = [str(ani).lower() for ani in policies_df['Clean ANI'].tolist()]
                        else:
                            ani_list = []
                            st.warning("Could not find ANI or Policy Number column in policies file")
                        
                        # Using a more direct approach for a final check
                        direct_matches = 0
                        for idx, row in ringba_download_df.head(100).iterrows():
                            if pd.isna(row[caller_id_col]):
                                continue
                            
                            # Remove +1 or 1 prefix if present
                            caller_id = str(row[caller_id_col]).lower().replace('+1', '').replace(' ', '')
                            if caller_id.startswith('1') and len(caller_id) == 11:
                                caller_id = caller_id[1:]
                            
                            for ani in ani_list:
                                # Remove any formatting from ANI
                                ani_clean = re.sub(r'\D', '', ani)
                                if ani_clean.startswith('1') and len(ani_clean) == 11:
                                    ani_clean = ani_clean[1:]
                                
                                if caller_id == ani_clean or caller_id[-10:] == ani_clean[-10:]:
                                    direct_matches += 1
                                    break
                        
                        if direct_matches > 0:
                            st.info(f"Found {direct_matches} direct matches using raw caller ID values")
                            
                            # Get a few examples of matching pairs for manual verification
                            st.write("Creating a more direct matching algorithm for Is_Policy...")
                            
                            # Add a new version of the is_policy function with more direct matching
                            def is_policy_direct(row):
                                if pd.isna(row[caller_id_col]):
                                    return False
                                
                                caller_id = str(row[caller_id_col]).lower().replace('+1', '').replace(' ', '')
                                if caller_id.startswith('1') and len(caller_id) == 11:
                                    caller_id = caller_id[1:]
                                
                                # Check if 'ANI' column exists in policies_df
                                if 'ANI' in policies_df.columns:
                                    ani_list = [str(ani).lower() for ani in policies_df['ANI'].tolist()]
                                elif 'Policy Number' in policies_df.columns:
                                    ani_list = [str(ani).lower() for ani in policies_df['Policy Number'].tolist()]
                                elif 'Clean ANI' in policies_df.columns:
                                    ani_list = [str(ani).lower() for ani in policies_df['Clean ANI'].tolist()]
                                else:
                                    # If no appropriate column is found
                                    return False
                                
                                for ani in ani_list:
                                    ani_clean = re.sub(r'\D', '', ani)
                                    if ani_clean.startswith('1') and len(ani_clean) == 11:
                                        ani_clean = ani_clean[1:]
                                    
                                    if caller_id == ani_clean or caller_id[-10:] == ani_clean[-10:]:
                                        return True
                                
                                return False
                            
                            # Apply the direct matching function 
                            ringba_download_df['Is_Policy'] = ringba_download_df.apply(is_policy_direct, axis=1)
                            policy_match_count = ringba_download_df['Is_Policy'].sum()
                            st.success(f"Updated Is_Policy values: Found {policy_match_count} matches using direct comparison")
                    
                    # Generate CSV with the additional column
                    processed_ringba_csv = ringba_download_df.to_csv(index=False)
                    st.download_button(
                        label="Download Full Processed Ringba Data CSV",
                        data=processed_ringba_csv,
                        file_name="processed_ringba_data_all_columns.csv",
                        mime="text/csv"
                    )
                
                else:
                    # CASE WHERE PUBLISHER IS IN POLICIES FILE BUT NOT IN RINGBA
                    # Here we need to map phone numbers between files to get the publisher for each call
                    
                    # Identify the Number column in Ringba data
                    number_col = None
                    if "Number" in ringba_df.columns:
                        number_col = "Number"
                        st.success(f"Using 'Number' column from Ringba data for policy matching")
                    else:
                        # Try to identify a suitable number column
                        phone_columns = []
                        for col in ringba_df.columns:
                            if any(term in col.lower() for term in ['number', 'ani', 'phone', 'caller']):
                                phone_columns.append(col)
                        
                        if phone_columns:
                            if len(phone_columns) > 1:
                                number_col = st.selectbox("Select phone number column from Ringba data:", phone_columns)
                            else:
                                number_col = phone_columns[0]
                                st.success(f"Using '{number_col}' column from Ringba data for policy matching")
                        else:
                            st.error("Could not find a suitable column for phone numbers in Ringba data")
                    
                    if number_col:
                        # Clean the phone numbers in Ringba data
                        # Check for Caller ID column which is what we should match for policies
                        caller_id_col = None
                        for col in ringba_df.columns:
                            if "caller" in col.lower() and "id" in col.lower():
                                caller_id_col = col
                                st.success(f"Found Caller ID column in Ringba data: {caller_id_col}")
                                break
                        
                        if caller_id_col:
                            # Clean the Caller ID values instead of Number for matching policies
                            ringba_df['Clean Number'] = ringba_df[caller_id_col].apply(clean_phone_number, is_policies=False)
                            st.info(f"Using '{caller_id_col}' for the Clean Number field to match against policy ANIs")
                        else:
                            # Use Number as fallback if no Caller ID
                            ringba_df['Clean Number'] = ringba_df[number_col].apply(clean_phone_number, is_policies=False)
                            st.warning(f"No Caller ID column found. Using '{number_col}' column for matching instead.")
                        
                        # Convert revenue to numeric
                        ringba_df['Revenue'] = pd.to_numeric(ringba_df[ringba_revenue_col], errors='coerce')
                        
                        try:
                            st.info("Matching Ringba calls to Publishers in the Policies file...")
                            
                            # Create a mapping of phone numbers to publishers
                            phone_to_publisher = dict(zip(policies_df['Clean ANI'], policies_df['Publisher']))
                            
                            # Match the Ringba data with policies data to add publisher information
                            ringba_with_publisher = ringba_df.copy()
                            ringba_with_publisher['Publisher'] = ringba_with_publisher['Clean Number'].map(phone_to_publisher)
                            
                            # Filter out records where we couldn't determine the publisher
                            ringba_with_publisher = ringba_with_publisher.dropna(subset=['Publisher'])
                            
                            if not ringba_with_publisher.empty:
                                # Calculate total revenue per publisher
                                publisher_revenue = ringba_with_publisher.groupby('Publisher')['Revenue'].sum().reset_index()
                                publisher_revenue.columns = ['Publisher', 'Total_Revenue']
                                
                                # For Policy_Count, count matches between ANI and Number for each publisher
                                publisher_policy_counts = []
                                
                                # Check for Caller ID column
                                caller_id_col = None
                                for col in ringba_df.columns:
                                    if "caller" in col.lower() and "id" in col.lower():
                                        caller_id_col = col
                                        st.success(f"Found Caller ID column in Ringba data: {caller_id_col}")
                                        break
                                
                                # Group by publisher and count matched ANIs per publisher
                                for publisher in publisher_revenue['Publisher'].unique():
                                    # Get policy ANIs for this publisher
                                    publisher_anis = set(policies_df[policies_df['Publisher'] == publisher]['Clean ANI'].astype(str))
                                    
                                    # Get publisher data from Ringba
                                    publisher_data = ringba_with_publisher[ringba_with_publisher['Publisher'] == publisher]
                                    
                                    # Get numbers from Ringba for this publisher
                                    ringba_numbers = set(publisher_data['Clean Number'].astype(str))
                                    
                                    # Count matches with Number
                                    number_matches = len(publisher_anis.intersection(ringba_numbers))
                                    
                                    # If we found a Caller ID column, also check for matches there
                                    if caller_id_col:
                                        # Clean the Caller ID values
                                        publisher_data['Clean Caller ID'] = publisher_data[caller_id_col].apply(clean_phone_number, is_policies=False)
                                        publisher_caller_ids = set(publisher_data['Clean Caller ID'].astype(str))
                                        
                                        # Get matches from Caller ID
                                        caller_id_matches = len(publisher_anis.intersection(publisher_caller_ids))
                                        st.write(f"Publisher {publisher}: Found {number_matches} matches in Number and {caller_id_matches} in Caller ID")
                                        
                                        # Use total unique matches (avoid double counting)
                                        all_numbers = ringba_numbers.union(publisher_caller_ids)
                                        matching_policies = len(publisher_anis.intersection(all_numbers))
                                    else:
                                        matching_policies = number_matches
                                    
                                    publisher_policy_counts.append({
                                        'Publisher': publisher,
                                        'Policy_Count': matching_policies
                                    })
                                
                                # Create a dataframe from the counts
                                publisher_counts = pd.DataFrame(publisher_policy_counts)
                                
                                # Merge the data
                                publisher_stats = pd.merge(publisher_revenue, publisher_counts, on='Publisher', how='left')
                                publisher_stats = publisher_stats.fillna(0)
                                
                                # Calculate CPA
                                publisher_stats['CPA'] = publisher_stats['Total_Revenue'] / publisher_stats['Policy_Count']
                                publisher_stats['CPA'] = publisher_stats['CPA'].replace([np.inf, -np.inf], 0)
                                
                                # Format for display
                                publisher_stats_display = publisher_stats.copy()
                                publisher_stats_display['Total_Revenue'] = publisher_stats_display['Total_Revenue'].map('${:,.2f}'.format)
                                publisher_stats_display['CPA'] = publisher_stats_display['CPA'].map('${:,.2f}'.format)
                                
                                # Display success message
                                st.success(f"Successfully matched {len(ringba_with_publisher)} Ringba calls to Publishers")
                                st.info("Total_Revenue is the sum of all revenue from matched Ringba calls per publisher. Policy_Count shows matches between ANI in policies file and Number in Ringba file per publisher.")
                                
                                # Display CPA metrics
                                st.subheader("CPA by Publisher")
                                st.dataframe(publisher_stats_display, use_container_width=True)
                                
                                # Total revenue bar chart (sorted by highest revenue)
                                fig = px.bar(
                                    publisher_stats.sort_values('Total_Revenue', ascending=False),
                                    x='Publisher',
                                    y='Total_Revenue',
                                    title="Total Revenue by Publisher (Sorted by Revenue)",
                                    color='Total_Revenue',
                                    color_continuous_scale='Viridis',
                                    labels={'Total_Revenue': 'Total Revenue ($)', 'Publisher': 'Publisher'}
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # CPA bar chart (sorted by highest CPA)
                                fig = px.bar(
                                    publisher_stats.sort_values('CPA', ascending=False),
                                    x='Publisher',
                                    y='CPA',
                                    title="Cost Per Acquisition by Publisher (Sorted by CPA)",
                                    color='CPA',
                                    color_continuous_scale='Viridis',
                                    labels={'CPA': 'CPA ($)', 'Publisher': 'Publisher'}
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Download option
                                csv = publisher_stats.to_csv(index=False)
                                st.download_button(
                                    label="Download CPA Analysis CSV",
                                    data=csv,
                                    file_name="publisher_cpa_analysis.csv",
                                    mime="text/csv"
                                )
                                
                                # Add download button for processed Ringba data with all columns
                                st.subheader("Download Full Processed Ringba Data")
                                st.info("Download the complete Ringba data with all original columns plus the processed Clean Number field and an 'Is_Policy' column that indicates whether each record matches with an ANI in the policies file (True or False).")
                                
                                # Prepare the download CSV with all original columns
                                # Add a Policy column to indicate whether each record matches with a policy
                                policy_anis = set(policies_df["Clean ANI"].astype(str))
                                
                                # Create a copy of ringba_df for download to avoid modifying the original
                                ringba_download_df = ringba_df.copy()
                                
                                # Ensure the Clean Number comes from the Caller ID column rather than the Number column
                                if caller_id_col:
                                    ringba_download_df['Clean Number'] = ringba_download_df[caller_id_col].apply(clean_phone_number, is_policies=False)
                                    # Also add a Clean Caller ID field for more explicit matching
                                    ringba_download_df['Clean Caller ID'] = ringba_download_df[caller_id_col].apply(clean_phone_number, is_policies=False)
                                    st.info(f"Using '{caller_id_col}' for Clean Number in the downloaded data for better matching with policies")
                                elif number_col:
                                    ringba_download_df['Clean Number'] = ringba_download_df[number_col].apply(clean_phone_number, is_policies=False)
                                
                                # Add Policy column showing if the number or caller ID matches a policy
                                def is_policy(row):
                                    # Check if Clean Number matches a policy ANI
                                    if 'Clean Number' in ringba_download_df.columns and not pd.isna(row['Clean Number']):
                                        clean_number = str(row['Clean Number'])
                                        if clean_number in policy_anis:
                                            return True
                                            
                                    # Also check Clean Caller ID if it exists
                                    if 'Clean Caller ID' in ringba_download_df.columns and not pd.isna(row['Clean Caller ID']):
                                        clean_caller_id = str(row['Clean Caller ID'])
                                        if clean_caller_id in policy_anis:
                                            return True
                                            
                                    # Check raw caller ID with basic cleaning as a fallback
                                    if caller_id_col and not pd.isna(row[caller_id_col]):
                                        caller_id = clean_phone_number(row[caller_id_col], is_policies=False)
                                        if caller_id in policy_anis:
                                            return True
                                            
                                    # If we get here, no match was found
                                    return False
                                
                                # Add some debugging information
                                st.subheader("Debugging Policy Matching")
                                with st.expander("View policy matching details"):
                                    st.write("Policy ANIs (first 10):", list(policy_anis)[:10])
                                    
                                    # Show some sample Clean Number values from Ringba
                                    sample_clean_numbers = []
                                    for idx, row in ringba_download_df.head(10).iterrows():
                                        if 'Clean Number' in ringba_download_df.columns:
                                            sample_clean_numbers.append(str(row['Clean Number']))
                                    st.write("Sample Clean Numbers from Ringba (first 10):", sample_clean_numbers)
                                    
                                    # Check for any matches
                                    matches_found = [num for num in sample_clean_numbers if num in policy_anis]
                                    st.write(f"Matches found in sample: {len(matches_found)}")
                                    if matches_found:
                                        st.write("Sample matches:", matches_found)
                                    else:
                                        st.warning("No matches found in sample - this is likely why all Is_Policy values are False")
                                        
                                    # Try direct string matching
                                    st.write("Trying direct string matching between sample numbers and ANIs")
                                    for clean_num in sample_clean_numbers:
                                        for ani in list(policy_anis)[:20]:  # Check first 20 ANIs
                                            if clean_num == ani:
                                                st.success(f"Match found: {clean_num} == {ani}")
                                            elif clean_num in ani or ani in clean_num:
                                                st.info(f"Partial match: {clean_num} vs {ani}")
                                
                                # Apply the function to determine policy match status
                                ringba_download_df['Is_Policy'] = ringba_download_df.apply(is_policy, axis=1)
                                
                                # Check if any rows were marked as True
                                policy_match_count = ringba_download_df['Is_Policy'].sum()
                                if policy_match_count == 0:
                                    st.warning(f"No matches found - all {len(ringba_download_df)} rows have Is_Policy = False")
                                else:
                                    st.success(f"Found {policy_match_count} rows with Is_Policy = True")
                                
                                # Check raw caller ID column for direct matches
                                if caller_id_col:
                                    # Check which column to use for ANI values
                                    if 'ANI' in policies_df.columns:
                                        ani_list = [str(ani).lower() for ani in policies_df['ANI'].tolist()]
                                    elif 'Policy Number' in policies_df.columns:
                                        ani_list = [str(ani).lower() for ani in policies_df['Policy Number'].tolist()]
                                    elif 'Clean ANI' in policies_df.columns:
                                        ani_list = [str(ani).lower() for ani in policies_df['Clean ANI'].tolist()]
                                    else:
                                        ani_list = []
                                        st.warning("Could not find ANI or Policy Number column in policies file")
                                    
                                    # Using a more direct approach for a final check
                                    direct_matches = 0
                                    for idx, row in ringba_download_df.head(100).iterrows():
                                        if pd.isna(row[caller_id_col]):
                                            continue
                                        
                                        # Remove +1 or 1 prefix if present
                                        caller_id = str(row[caller_id_col]).lower().replace('+1', '').replace(' ', '')
                                        if caller_id.startswith('1') and len(caller_id) == 11:
                                            caller_id = caller_id[1:]
                                        
                                        for ani in ani_list:
                                            # Remove any formatting from ANI
                                            ani_clean = re.sub(r'\D', '', ani)
                                            if ani_clean.startswith('1') and len(ani_clean) == 11:
                                                ani_clean = ani_clean[1:]
                                            
                                            if caller_id == ani_clean or caller_id[-10:] == ani_clean[-10:]:
                                                direct_matches += 1
                                                break
                                    
                                    if direct_matches > 0:
                                        st.info(f"Found {direct_matches} direct matches using raw caller ID values")
                                        
                                        # Get a few examples of matching pairs for manual verification
                                        st.write("Creating a more direct matching algorithm for Is_Policy...")
                                        
                                        # Add a new version of the is_policy function with more direct matching
                                        def is_policy_direct(row):
                                            if pd.isna(row[caller_id_col]):
                                                return False
                                            
                                            caller_id = str(row[caller_id_col]).lower().replace('+1', '').replace(' ', '')
                                            if caller_id.startswith('1') and len(caller_id) == 11:
                                                caller_id = caller_id[1:]
                                            
                                            # Check if 'ANI' column exists in policies_df
                                            if 'ANI' in policies_df.columns:
                                                ani_list = [str(ani).lower() for ani in policies_df['ANI'].tolist()]
                                            elif 'Policy Number' in policies_df.columns:
                                                ani_list = [str(ani).lower() for ani in policies_df['Policy Number'].tolist()]
                                            elif 'Clean ANI' in policies_df.columns:
                                                ani_list = [str(ani).lower() for ani in policies_df['Clean ANI'].tolist()]
                                            else:
                                                # If no appropriate column is found
                                                return False
                                            
                                            for ani in ani_list:
                                                ani_clean = re.sub(r'\D', '', ani)
                                                if ani_clean.startswith('1') and len(ani_clean) == 11:
                                                    ani_clean = ani_clean[1:]
                                                
                                                if caller_id == ani_clean or caller_id[-10:] == ani_clean[-10:]:
                                                    return True
                                            
                                            return False
                                        
                                        # Apply the direct matching function 
                                        ringba_download_df['Is_Policy'] = ringba_download_df.apply(is_policy_direct, axis=1)
                                        policy_match_count = ringba_download_df['Is_Policy'].sum()
                                        st.success(f"Updated Is_Policy values: Found {policy_match_count} matches using direct comparison")
                                
                                # Generate CSV with the additional column
                                processed_ringba_csv = ringba_download_df.to_csv(index=False)
                                st.download_button(
                                    label="Download Full Processed Ringba Data CSV",
                                    data=processed_ringba_csv,
                                    file_name="processed_ringba_data_all_columns.csv",
                                    mime="text/csv"
                                )
                            else:
                                st.warning("Could not match any Ringba calls with Publishers from the Policies file.")
                                st.info("Make sure phone numbers are formatted consistently between the files.")
                        except Exception as e:
                            st.error(f"Error during publisher matching: {str(e)}")
                            st.exception(e)
                    else:
                        st.warning("Could not identify phone number column in Ringba data")
                        st.write("Available columns in Ringba data:", list(ringba_df.columns))
            else:
                st.warning("Could not identify revenue column in Ringba data")
                st.write("Available columns in Ringba data:", list(ringba_df.columns))
                
                # Allow manual selection
                if len(ringba_df.columns) > 0:
                    st.write("Please select the revenue column manually:")
                    ringba_revenue_col = st.selectbox("Select column containing revenue data:", ringba_df.columns)
                    
                    if st.button("Use this column for revenue"):
                        st.experimental_rerun()
    
    # Original TABs now shifted down by one when Ringba data is available
    with tabs[1 if ringba_df is None else 2]:
        # Publisher Details tab
        st.header("Publisher Details Analysis")
        
        # Select a publisher to analyze
        selected_publisher = st.selectbox(
            "Select publisher to view details:",
            policy_counts['Publisher'].tolist()
        )
        
        # Filter data for selected publisher
        publisher_data = policies_df[policies_df['Publisher'] == selected_publisher]
        
        # Display publisher metrics
        st.subheader(f"Details for: {selected_publisher}")
        
        # Key metrics
        st.metric("Total Policies", len(publisher_data))
        st.metric("Percentage of All Policies", 
                  f"{(len(publisher_data) / len(policies_df) * 100):.2f}%")
        
        # List all ANIs/Phone Numbers for this publisher
        st.subheader("All Policy Numbers/ANIs")
        st.dataframe(publisher_data, use_container_width=True)
        
        # Download specific publisher data
        csv = publisher_data.to_csv(index=False)
        st.download_button(
            label=f"Download {selected_publisher} Data CSV",
            data=csv,
            file_name=f"{selected_publisher}_policies.csv",
            mime="text/csv"
        )
    
    with tabs[2 if ringba_df is None else 3]:
        # Data Explorer tab
        st.header("Policy Data Explorer")
        
        # Column selector
        available_columns = policies_df.columns.tolist()
        default_columns = ['Publisher', 'Policy Number']
        
        selected_columns = st.multiselect(
            "Select columns to display:",
            available_columns,
            default=default_columns
        )
        
        if selected_columns:
            # Filter data by publisher
            publisher_filter = st.selectbox("Filter by publisher:", ['All'] + policy_counts['Publisher'].tolist())
            
            if publisher_filter != 'All':
                filtered_df = policies_df[policies_df['Publisher'] == publisher_filter]
            else:
                filtered_df = policies_df
            
            # Display filtered data
            st.dataframe(filtered_df[selected_columns], use_container_width=True)
            
            # Download option
            csv = filtered_df[selected_columns].to_csv(index=False)
            st.download_button(
                label="Download Filtered Data CSV",
                data=csv,
                file_name="filtered_policy_data.csv",
                mime="text/csv"
            )
    
    if ringba_df is not None:
        with tabs[4]:
            # File Comparison tab
            st.header("Policy and Ringba Call Log Comparison")
            st.info("Note: ANI values from policies file are formatted to match Ringba's Number format by adding a '1' prefix when needed for proper matching.")
            
            # Try to identify ANI/phone number field in Ringba data
            phone_columns = []
            for col in ringba_df.columns:
                if any(term in col.lower() for term in ['ani', 'phone', 'caller', 'from', 'number']):
                    phone_columns.append(col)
            
            if phone_columns:
                # Let user select the phone column if multiple are found
                if len(phone_columns) > 1:
                    ringba_phone_col = st.selectbox("Select phone/ANI column from Ringba data:", phone_columns)
                else:
                    ringba_phone_col = phone_columns[0]
                    st.success(f"Using '{ringba_phone_col}' as phone number column from Ringba data")
                
                # Create a clean version of the Ringba phone numbers
                ringba_df['Clean Phone'] = ringba_df[ringba_phone_col].apply(clean_phone_number, is_policies=False)
                
                # Set of clean ANIs from Policies
                policy_anis = set(policies_df['Clean ANI'].astype(str))
                
                # Set of clean phone numbers from Ringba
                ringba_phones = set(ringba_df['Clean Phone'].astype(str))
                
                # Find matches and mismatches
                matches = policy_anis.intersection(ringba_phones)
                in_policy_not_ringba = policy_anis - ringba_phones
                in_ringba_not_policy = ringba_phones - policy_anis
                
                # Display Venn diagram-style metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Matching Phone Numbers", len(matches))
                with col2:
                    st.metric("In Policies but not in Ringba", len(in_policy_not_ringba))
                with col3:
                    st.metric("In Ringba but not in Policies", len(in_ringba_not_policy))
                
                # Calculate match percentage
                if len(policy_anis) > 0:
                    match_percentage = (len(matches) / len(policy_anis)) * 100
                    st.metric("Match Percentage", f"{match_percentage:.2f}%")
                
                # Show the actual missing records
                if len(in_policy_not_ringba) > 0:
                    st.subheader("Policies not found in Ringba data")
                    missing_policies = policies_df[policies_df['Clean ANI'].astype(str).isin(in_policy_not_ringba)]
                    st.dataframe(missing_policies, use_container_width=True)
                    
                    # Download option
                    csv = missing_policies.to_csv(index=False)
                    st.download_button(
                        label="Download Missing Policies CSV",
                        data=csv,
                        file_name="policies_not_in_ringba.csv",
                        mime="text/csv"
                    )
                
                # Option to view matching records
                if len(matches) > 0 and st.checkbox("Show matching records"):
                    st.subheader("Policies matching with Ringba data")
                    matching_policies = policies_df[policies_df['Clean ANI'].astype(str).isin(matches)]
                    st.dataframe(matching_policies, use_container_width=True)
            else:
                st.warning("Could not identify phone number column in Ringba data")
                st.write("Available columns in Ringba data:", list(ringba_df.columns))
    
    return policy_counts

# Main application flow
if policies_file is not None:
    try:
        # Load the policies data
        policies_df = pd.read_csv(policies_file)
        
        # Show data preview for policies
        st.subheader("Policies Data Preview")
        st.dataframe(policies_df.head(), use_container_width=True)
        
        # Check if we have the expected columns
        if "ANI" in policies_df.columns and "Buyer" in policies_df.columns:
            st.success("✅ Found the expected columns in Policies file: ANI and Buyer")
        
        # Load the Ringba data if available
        ringba_df = None
        if ringba_file is not None:
            ringba_df = pd.read_csv(ringba_file)
            
            # Show data preview for Ringba
            st.subheader("Ringba Call Log Preview")
            st.dataframe(ringba_df.head(), use_container_width=True)
        
        # Analyze the data
        policy_counts = analyze_policies_data(policies_df, ringba_df)
        
    except Exception as e:
        st.error(f"Error analyzing the data: {str(e)}")
        st.exception(e)
else:
    st.info("Please upload the Cobras - CPA track CSV file with ANI and Buyer columns.")
    
    # Show sample format based on the actual file
    st.subheader("Expected CSV Format")
    
    # Create a sample dataframe that matches your file
    sample_data = {
        'ANI': ['8437583140', '2173140415', '4696582686', '9125122007', '8587524917'],
        'Buyer': ['GH', 'GH', 'GH', 'GH', 'GH'],
    }
    
    sample_df = pd.DataFrame(sample_data)
    st.dataframe(sample_df, use_container_width=True)
    
    st.caption("Your CSV should include at least ANI (phone numbers) and Buyer columns.") 