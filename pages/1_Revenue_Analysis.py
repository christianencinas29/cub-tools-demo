import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import traceback
import numpy as np
import os

st.set_page_config(page_title="Revenue Analysis", layout="wide")

st.title("Revenue Missing Tool")

# Add introduction with sample data information
st.markdown("""
This app helps identify missing revenue by comparing Buyer and CUB dashboard data. It matches records 
by UUID or Caller ID, finds missing records, analyzes data quality issues, and detects revenue discrepancies.

**Sample data** is available in the `example_data` directory if you'd like to test the app without uploading your own files.
""")

# Check if example data exists and offer to load it
example_buyer_path = "example_data/sample_buyer_dashboard.csv"
example_cub_path = "example_data/sample_cub_dashboard.csv"

sample_data_available = os.path.exists(example_buyer_path) and os.path.exists(example_cub_path)

if sample_data_available:
    st.info("💡 Sample data is available! Use the checkbox below to load it.")
    load_sample_data = st.checkbox("Load sample data", value=False)
else:
    load_sample_data = False

# Specific column names to look for
BUYER_COLUMNS = {
    "caller_id": ["Caller ID", "From"],
    "uuid": ["Ringba Call UUID", "Inbound Call ID", "Call UUID", "UUID"],
    "revenue": ["Revenue", "Buyer Revenue"]
}

CUB_COLUMNS = {
    "caller_id": ["Caller ID", "From"],
    "uuid": ["Inbound Call ID", "Call UUID", "UUID", "Ringba Call UUID"],
    "revenue": ["Revenue", "CUB Revenue"]
}

RETREAVER_COLUMNS = {
    "caller_id": ["ReceivedCallerID", "From", "Caller ID"]
}

# File upload section
st.header("Upload Dashboard Files")
col1, col2, col3 = st.columns(3)

with col1:
    if not load_sample_data:
        buyer_file = st.file_uploader("Upload Buyer Dashboard", type=['csv'])
    else:
        buyer_file = open(example_buyer_path, "rb")
    st.caption("Required columns: 'Ringba Call UUID' and 'Revenue'")
    
with col2:
    if not load_sample_data:
        cub_file = st.file_uploader("Upload CUB Ringba Dashboard", type=['csv'])
    else:
        cub_file = open(example_cub_path, "rb")
    st.caption("Required columns: 'Inbound Call ID' and 'Revenue'")

with col3:
    retreaver_file = st.file_uploader("Upload CUB Retreaver Dashboard (Optional)", type=['csv'])
    st.caption("Optional: Adds additional matching capability")

def clean_caller_id(caller_id):
    try:
        if pd.isna(caller_id):
            return ""
        return str(caller_id).replace('+', '')
    except Exception as e:
        return str(caller_id)

def clean_uuid(uuid_val):
    """Clean UUID values, replacing NaN with 'Missing UUID'"""
    if pd.isna(uuid_val) or str(uuid_val).lower() == 'nan' or str(uuid_val).strip() == '':
        return "Missing UUID"
    return str(uuid_val)

def find_column(df, column_options):
    """Find the first matching column from a list of options"""
    for col in column_options:
        if col in df.columns:
            return col
    return None

def analyze_data(buyer_df, cub_df, retreaver_df=None):
    # Create tabs for different analyses
    tabs = st.tabs(["UUID Match Analysis", "Missing Records", "Data Quality Issues", "Revenue Discrepancies"])
    
    # Initialize variables that might be used later
    cub_uuids = set()
    buyer_uuids = set()
    cub_caller_ids = set()
    buyer_caller_ids = set()
    
    with tabs[0]:
        st.subheader("Column Detection")
        # Display column names for debugging
        st.write("Buyer dataframe columns:", list(buyer_df.columns))
        st.write("CUB dataframe columns:", list(cub_df.columns))
        if retreaver_df is not None:
            st.write("Retreaver dataframe columns:", list(retreaver_df.columns))
        
        # Make a copy of dataframes to avoid modifying the original
        buyer_df = buyer_df.copy()
        cub_df = cub_df.copy()
        if retreaver_df is not None:
            retreaver_df = retreaver_df.copy()
        
        # Find columns in Buyer dashboard
        st.subheader("Detecting Fields")
        
        # Find UUID columns - primary focus
        buyer_uuid_col = find_column(buyer_df, BUYER_COLUMNS["uuid"])
        cub_uuid_col = find_column(cub_df, CUB_COLUMNS["uuid"])
        
        # Find Caller ID columns as backup
        buyer_caller_id_col = find_column(buyer_df, BUYER_COLUMNS["caller_id"])
        cub_caller_id_col = find_column(cub_df, CUB_COLUMNS["caller_id"])
        
        # NEW: Check if UUID columns exist
        has_uuid_columns = buyer_uuid_col and cub_uuid_col
        
        # NEW: If UUID columns don't exist, inform the user we'll use Caller ID for matching
        if not has_uuid_columns and buyer_caller_id_col and cub_caller_id_col:
            st.warning("Ringba Call UUID not found in one or both dashboards. Using Caller ID for matching instead.")
            st.info("Matching by Caller ID may be less precise than UUID matching.")
            primary_match_method = "caller_id"
        else:
            primary_match_method = "uuid"
            if not buyer_uuid_col:
                st.error("UUID column not found in Buyer Dashboard.")
                possible_columns = []
                for col in buyer_df.columns:
                    if "uuid" in col.lower() or "id" in col.lower() or "call" in col.lower():
                        possible_columns.append(col)
                
                if possible_columns:
                    buyer_uuid_col = st.selectbox("Select Buyer UUID column:", possible_columns)
                else:
                    st.error("No suitable UUID column found in Buyer Dashboard. Analysis may be incomplete.")
            else:
                st.success(f"Found Buyer UUID column: {buyer_uuid_col}")
            
            if not cub_uuid_col:
                st.error("UUID column not found in CUB Dashboard.")
                possible_columns = []
                for col in cub_df.columns:
                    if "uuid" in col.lower() or "id" in col.lower() or "call" in col.lower():
                        possible_columns.append(col)
                
                if possible_columns:
                    cub_uuid_col = st.selectbox("Select CUB UUID column:", possible_columns)
                else:
                    st.error("No suitable UUID column found in CUB Dashboard. Analysis may be incomplete.")
            else:
                st.success(f"Found CUB UUID column: {cub_uuid_col}")
        
        # Find Revenue columns
        buyer_revenue_col = find_column(buyer_df, BUYER_COLUMNS["revenue"])
        cub_revenue_col = find_column(cub_df, CUB_COLUMNS["revenue"])
        
        if not buyer_revenue_col:
            st.error("Revenue column not found in Buyer Dashboard.")
            possible_columns = []
            for col in buyer_df.columns:
                if "revenue" in col.lower() or "cost" in col.lower() or "price" in col.lower() or "amount" in col.lower():
                    possible_columns.append(col)
            
            if possible_columns:
                buyer_revenue_col = st.selectbox("Select Buyer Revenue column:", possible_columns)
            else:
                st.error("No suitable Revenue column found in Buyer Dashboard.")
                return {"error": "Missing required columns"}
        else:
            st.success(f"Found Buyer Revenue column: {buyer_revenue_col}")
        
        if not cub_revenue_col:
            st.error("Revenue column not found in CUB Dashboard.")
            possible_columns = []
            for col in cub_df.columns:
                if "revenue" in col.lower() or "cost" in col.lower() or "price" in col.lower() or "amount" in col.lower():
                    possible_columns.append(col)
            
            if possible_columns:
                cub_revenue_col = st.selectbox("Select CUB Revenue column:", possible_columns)
            else:
                st.error("No suitable Revenue column found in CUB Dashboard.")
                return {"error": "Missing required columns"}
        else:
            st.success(f"Found CUB Revenue column: {cub_revenue_col}")
        
        # Display Caller ID columns if that's our primary match method
        if primary_match_method == "caller_id":
            if not buyer_caller_id_col:
                st.error("Caller ID column not found in Buyer Dashboard.")
                possible_columns = []
                for col in buyer_df.columns:
                    if "caller" in col.lower() or "phone" in col.lower() or "number" in col.lower() or "from" in col.lower():
                        possible_columns.append(col)
                
                if possible_columns:
                    buyer_caller_id_col = st.selectbox("Select Buyer Caller ID column:", possible_columns)
                else:
                    st.error("No suitable Caller ID column found in Buyer Dashboard.")
                    return {"error": "Missing required columns"}
            else:
                st.success(f"Found Buyer Caller ID column for matching: {buyer_caller_id_col}")
            
            if not cub_caller_id_col:
                st.error("Caller ID column not found in CUB Dashboard.")
                possible_columns = []
                for col in cub_df.columns:
                    if "caller" in col.lower() or "phone" in col.lower() or "number" in col.lower() or "from" in col.lower():
                        possible_columns.append(col)
                
                if possible_columns:
                    cub_caller_id_col = st.selectbox("Select CUB Caller ID column:", possible_columns)
                else:
                    st.error("No suitable Caller ID column found in CUB Dashboard.")
                    return {"error": "Missing required columns"}
            else:
                st.success(f"Found CUB Caller ID column for matching: {cub_caller_id_col}")
        else:
            # If UUID is primary, still display Caller ID columns as backup
            if not buyer_caller_id_col:
                st.warning("Caller ID column not found in Buyer Dashboard (will be used as fallback only).")
            else:
                st.success(f"Found Buyer Caller ID column: {buyer_caller_id_col}")
            
            if not cub_caller_id_col:
                st.warning("Caller ID column not found in CUB Dashboard (will be used as fallback only).")
            else:
                st.success(f"Found CUB Caller ID column: {cub_caller_id_col}")
        
        # Create standardized columns for matching and analysis
        st.subheader("Preparing Data")
        
        # Create standardized UUID columns with proper cleaning (if available)
        if buyer_uuid_col:
            buyer_df["_UUID"] = buyer_df[buyer_uuid_col].apply(clean_uuid)
        
        if cub_uuid_col:
            cub_df["_UUID"] = cub_df[cub_uuid_col].apply(clean_uuid)
        
        # Create standardized Revenue columns
        buyer_df["_Revenue"] = pd.to_numeric(buyer_df[buyer_revenue_col], errors='coerce')
        cub_df["_Revenue"] = pd.to_numeric(cub_df[cub_revenue_col], errors='coerce')
        
        # Create standardized Caller ID columns (used as primary if UUID not available)
        if buyer_caller_id_col:
            buyer_df["_CallerId"] = buyer_df[buyer_caller_id_col].apply(clean_caller_id)
        
        if cub_caller_id_col:
            cub_df["_CallerId"] = cub_df[cub_caller_id_col].apply(clean_caller_id)
        
        # Check for records with missing primary match key
        if primary_match_method == "uuid":
            if buyer_uuid_col:
                missing_uuid_count = buyer_df["_UUID"].isin(["Missing UUID", "nan"]).sum()
                if missing_uuid_count > 0:
                    st.warning(f"Found {missing_uuid_count} records with missing UUIDs in Buyer Dashboard")
            
            if cub_uuid_col:
                missing_uuid_count = cub_df["_UUID"].isin(["Missing UUID", "nan"]).sum()
                if missing_uuid_count > 0:
                    st.warning(f"Found {missing_uuid_count} records with missing UUIDs in CUB Dashboard")
        else:  # Using Caller ID
            if buyer_caller_id_col:
                missing_caller_count = buyer_df["_CallerId"].isin(["", "nan"]).sum()
                if missing_caller_count > 0:
                    st.warning(f"Found {missing_caller_count} records with missing Caller IDs in Buyer Dashboard")
            
            if cub_caller_id_col:
                missing_caller_count = cub_df["_CallerId"].isin(["", "nan"]).sum()
                if missing_caller_count > 0:
                    st.warning(f"Found {missing_caller_count} records with missing Caller IDs in CUB Dashboard")
        
        # Display sample data after column mapping
        st.subheader("Data Preview (Standardized Columns)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Buyer Dashboard")
            preview_cols = []
            if "_UUID" in buyer_df.columns:
                preview_cols.append("_UUID")
            preview_cols.append("_Revenue")
            if "_CallerId" in buyer_df.columns:
                preview_cols.append("_CallerId")
            st.dataframe(buyer_df[preview_cols].head())
        
        with col2:
            st.write("CUB Dashboard")
            preview_cols = []
            if "_UUID" in cub_df.columns:
                preview_cols.append("_UUID")
            preview_cols.append("_Revenue")
            if "_CallerId" in cub_df.columns:
                preview_cols.append("_CallerId")
            st.dataframe(cub_df[preview_cols].head())
        
        # Check if we have the required columns for matching
        can_perform_matching = False
        
        if primary_match_method == "uuid" and (buyer_uuid_col and cub_uuid_col):
            can_perform_matching = True
            st.success("Will perform matching by UUID")
        elif primary_match_method == "caller_id" and (buyer_caller_id_col and cub_caller_id_col):
            can_perform_matching = True
            st.success("Will perform matching by Caller ID")
        
        if not can_perform_matching:
            st.error(f"Cannot perform {primary_match_method} matching: one or both datasets missing required column")
        else:
            # Perform Matching Analysis (either by UUID or Caller ID)
            if primary_match_method == "uuid":
                st.subheader("UUID Matching Analysis")
                
                # Filter out missing UUIDs for accurate matching
                valid_buyer_df = buyer_df[~buyer_df["_UUID"].isin(["Missing UUID", "nan"])]
                valid_cub_df = cub_df[~cub_df["_UUID"].isin(["Missing UUID", "nan"])]
                
                # Create sets for faster lookup
                cub_uuids = set(valid_cub_df["_UUID"].astype(str))
                buyer_uuids = set(valid_buyer_df["_UUID"].astype(str))
                
                # Find records in both, only in buyer, and only in CUB
                uuids_in_both = buyer_uuids.intersection(cub_uuids)
                uuids_only_in_buyer = buyer_uuids - cub_uuids
                uuids_only_in_cub = cub_uuids - buyer_uuids
                
                # Display Venn diagram stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Records in Both", len(uuids_in_both))
                with col2:
                    st.metric("Only in Buyer", len(uuids_only_in_buyer))
                with col3:
                    st.metric("Only in CUB", len(uuids_only_in_cub))
                
                # Calculate match percentage
                match_percentage = (len(uuids_in_both) / len(buyer_uuids) * 100) if len(buyer_uuids) > 0 else 0
                st.metric("UUID Match Percentage", f"{match_percentage:.2f}%")
                
                # Add duplicate detection analysis
                st.subheader("Duplicate UUID Analysis")
                
                # Check for duplicates in the buyer dataframe
                if "_UUID" in buyer_df.columns:
                    # Count occurrences of each UUID
                    buyer_uuid_counts = buyer_df["_UUID"].value_counts()
                    
                    # Find duplicated UUIDs (count > 1)
                    duplicated_uuids = buyer_uuid_counts[buyer_uuid_counts > 1]
                    
                    if len(duplicated_uuids) > 0:
                        total_duplicate_records = sum(duplicated_uuids) - len(duplicated_uuids)
                        
                        st.warning(f"Found {len(duplicated_uuids)} UUIDs that appear multiple times in Buyer dashboard, accounting for {total_duplicate_records} duplicate records")
                        
                        # Display the count of each duplicated UUID
                        dup_df = pd.DataFrame({"UUID": duplicated_uuids.index, "Occurrences": duplicated_uuids.values})
                        st.dataframe(dup_df, use_container_width=True)
                        
                        # Show actual duplicate records for inspection
                        st.subheader("Duplicate Records in Buyer Dashboard")
                        duplicate_records = buyer_df[buyer_df["_UUID"].isin(duplicated_uuids.index)]
                        st.dataframe(duplicate_records, use_container_width=True)
                        
                        # Check if number of duplicates matches the missing record count
                        if total_duplicate_records == (len(buyer_df) - len(cub_df)):
                            st.success(f"✅ The gap of {total_duplicate_records} records matches the number of duplicate records in Buyer dashboard")
                        else:
                            st.info(f"Duplicate records ({total_duplicate_records}) do not fully explain the gap between Buyer ({len(buyer_df)}) and CUB ({len(cub_df)}) dashboards")
                    else:
                        st.success("No duplicate UUIDs found in Buyer dashboard")
                
                # Also check for duplicates in CUB
                if "_UUID" in cub_df.columns:
                    # Count occurrences of each UUID
                    cub_uuid_counts = cub_df["_UUID"].value_counts()
                    
                    # Find duplicated UUIDs (count > 1)
                    duplicated_uuids = cub_uuid_counts[cub_uuid_counts > 1]
                    
                    if len(duplicated_uuids) > 0:
                        total_duplicate_records = sum(duplicated_uuids) - len(duplicated_uuids)
                        
                        st.warning(f"Found {len(duplicated_uuids)} UUIDs that appear multiple times in CUB dashboard, accounting for {total_duplicate_records} duplicate records")
                        
                        # Display the duplicated UUIDs and their counts
                        dup_df = pd.DataFrame({"UUID": duplicated_uuids.index, "Occurrences": duplicated_uuids.values})
                        st.dataframe(dup_df, use_container_width=True)
                    else:
                        st.success("No duplicate UUIDs found in CUB dashboard")
            else:
                # CALLER ID MATCHING LOGIC
                st.subheader("Caller ID Matching Analysis")
                
                # Filter out missing Caller IDs for accurate matching
                valid_buyer_df = buyer_df[~buyer_df["_CallerId"].isin(["", "nan"])]
                valid_cub_df = cub_df[~cub_df["_CallerId"].isin(["", "nan"])]
                
                # Create sets for faster lookup
                cub_caller_ids = set(valid_cub_df["_CallerId"].astype(str))
                buyer_caller_ids = set(valid_buyer_df["_CallerId"].astype(str))
                
                # Find records in both, only in buyer, and only in CUB
                caller_ids_in_both = buyer_caller_ids.intersection(cub_caller_ids)
                caller_ids_only_in_buyer = buyer_caller_ids - cub_caller_ids
                caller_ids_only_in_cub = cub_caller_ids - buyer_caller_ids
                
                # Display Venn diagram stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Records in Both", len(caller_ids_in_both))
                with col2:
                    st.metric("Only in Buyer", len(caller_ids_only_in_buyer))
                with col3:
                    st.metric("Only in CUB", len(caller_ids_only_in_cub))
                
                # Calculate match percentage
                match_percentage = (len(caller_ids_in_both) / len(buyer_caller_ids) * 100) if len(buyer_caller_ids) > 0 else 0
                st.metric("Caller ID Match Percentage", f"{match_percentage:.2f}%")
                
                # Add duplicate detection analysis for Caller ID
                st.subheader("Duplicate Caller ID Analysis")
                
                # Check for duplicates in the buyer dataframe
                if "_CallerId" in buyer_df.columns:
                    # Count occurrences of each Caller ID
                    buyer_caller_id_counts = buyer_df["_CallerId"].value_counts()
                    
                    # Find duplicated Caller IDs (count > 1)
                    duplicated_caller_ids = buyer_caller_id_counts[buyer_caller_id_counts > 1]
                    
                    if len(duplicated_caller_ids) > 0:
                        total_duplicate_records = sum(duplicated_caller_ids) - len(duplicated_caller_ids)
                        
                        st.warning(f"Found {len(duplicated_caller_ids)} Caller IDs that appear multiple times in Buyer dashboard, accounting for {total_duplicate_records} duplicate records")
                        
                        # Display the count of each duplicated Caller ID
                        dup_df = pd.DataFrame({"Caller ID": duplicated_caller_ids.index, "Occurrences": duplicated_caller_ids.values})
                        st.dataframe(dup_df, use_container_width=True)
                    else:
                        st.success("No duplicate Caller IDs found in Buyer dashboard")

            # Store the number of duplicate records for use in the results
            buyer_duplicates = 0
            if primary_match_method == "uuid" and "_UUID" in buyer_df.columns:
                # Count occurrences of each UUID
                buyer_uuid_counts = buyer_df["_UUID"].value_counts()
                
                # Find duplicated UUIDs (count > 1)
                duplicated_uuids = buyer_uuid_counts[buyer_uuid_counts > 1]
                
                if len(duplicated_uuids) > 0:
                    buyer_duplicates = sum(duplicated_uuids) - len(duplicated_uuids)
            elif primary_match_method == "caller_id" and "_CallerId" in buyer_df.columns:
                # Count occurrences of each Caller ID
                buyer_caller_id_counts = buyer_df["_CallerId"].value_counts()
                
                # Find duplicated Caller IDs (count > 1)
                duplicated_caller_ids = buyer_caller_id_counts[buyer_caller_id_counts > 1]
                
                if len(duplicated_caller_ids) > 0:
                    buyer_duplicates = sum(duplicated_caller_ids) - len(duplicated_caller_ids)
    
    # Process missing records tab
    with tabs[1]:
        st.subheader("Finding Missing Records in CUB Dashboard")
        
        # Find missing records (in Buyer but not in CUB)
        missing_records = []
        missing_key_records = []  # generic name for missing UUID/CallerID
        
        # Ensure we have the lookup sets before using them
        if primary_match_method == "uuid" and "_UUID" in buyer_df.columns and "_UUID" in cub_df.columns:
            # Make sure cub_uuids is defined if not already done in the UUID analysis tab
            if len(cub_uuids) == 0:
                valid_cub_df = cub_df[~cub_df["_UUID"].isin(["Missing UUID", "nan"])]
                cub_uuids = set(valid_cub_df["_UUID"].astype(str))
                valid_buyer_df = buyer_df[~buyer_df["_UUID"].isin(["Missing UUID", "nan"])]
                buyer_uuids = set(valid_buyer_df["_UUID"].astype(str))
            
            st.write("Matching by UUID...")
            
            # First, identify records with actual missing UUIDs
            for _, record in buyer_df.iterrows():
                try:
                    uuid = str(record["_UUID"])
                    if uuid in ["Missing UUID", "nan"]:
                        missing_key_records.append(record)
                    elif uuid not in cub_uuids:
                        missing_records.append(record)
                except Exception as e:
                    continue
                    
        elif primary_match_method == "caller_id" and "_CallerId" in buyer_df.columns and "_CallerId" in cub_df.columns:
            # Make sure cub_caller_ids is defined
            if len(cub_caller_ids) == 0:
                valid_cub_df = cub_df[~cub_df["_CallerId"].isin(["", "nan"])]
                cub_caller_ids = set(valid_cub_df["_CallerId"].astype(str))
                valid_buyer_df = buyer_df[~buyer_df["_CallerId"].isin(["", "nan"])]
                buyer_caller_ids = set(valid_buyer_df["_CallerId"].astype(str))
                
            st.write("Matching by Caller ID...")
            
            # First, identify records with missing Caller IDs
            for _, record in buyer_df.iterrows():
                try:
                    caller_id = str(record["_CallerId"])
                    if caller_id in ["", "nan"] or len(caller_id) < 5:  # Assuming valid caller ID is at least 5 chars
                        missing_key_records.append(record)
                    elif caller_id not in cub_caller_ids:
                        missing_records.append(record)
                except Exception as e:
                    continue
        
        # Fall back to alternate matching if still needed
        if len(missing_records) == 0 and primary_match_method == "uuid" and buyer_caller_id_col and cub_caller_id_col:
            st.write("No missing records found by UUID. Trying by Caller ID...")
            # Make sure cub_caller_ids is defined
            if len(cub_caller_ids) == 0:
                valid_cub_df = cub_df[~cub_df["_CallerId"].isin(["", "nan"])]
                cub_caller_ids = set(valid_cub_df["_CallerId"].astype(str))
                
            for _, record in buyer_df.iterrows():
                try:
                    caller_id = str(record["_CallerId"])
                    if caller_id and caller_id not in cub_caller_ids:
                        missing_records.append(record)
                except Exception as e:
                    continue
        
        # Ensure we have missing_df and missing_uuid_df defined
        if len(missing_records) == 0 and len(missing_key_records) == 0:
            st.info(f"No missing records found! All Buyer records exist in CUB (matched by {primary_match_method}).")
            missing_df = pd.DataFrame(columns=["UUID", "Revenue", "Caller ID"])
            missing_uuid_df = pd.DataFrame(columns=["UUID", "Revenue", "Caller ID"])
        else:
            # Create final dataframe with results - keep all original columns
            missing_df = pd.DataFrame(missing_records) if missing_records else pd.DataFrame()
            missing_uuid_df = pd.DataFrame(missing_key_records) if missing_key_records else pd.DataFrame()
            
            # Rename the standardized columns for clarity but KEEP all other columns
            columns_map = {
                "_UUID": "UUID",
                "_Revenue": "Revenue",
                "_CallerId": "Caller ID"
            }
            
            # Create final dataframe for missing records but preserving all columns
            if not missing_df.empty:
                # First make a copy of all original columns
                final_missing_df = missing_df.copy()
                
                # Then rename the standardized columns
                for old_col, new_col in columns_map.items():
                    if old_col in final_missing_df.columns:
                        final_missing_df[new_col] = final_missing_df[old_col]
                        # Remove the old column only if it's a standardized one we renamed
                        final_missing_df = final_missing_df.drop(columns=[old_col])
                
                missing_df = final_missing_df
            
            # Similar process for missing_uuid_df
            if not missing_uuid_df.empty:
                # First make a copy of all original columns
                final_missing_uuid_df = missing_uuid_df.copy()
                
                # Then rename the standardized columns
                for old_col, new_col in columns_map.items():
                    if old_col in final_missing_uuid_df.columns:
                        final_missing_uuid_df[new_col] = final_missing_uuid_df[old_col]
                        # Remove the old column only if it's a standardized one we renamed
                        final_missing_uuid_df = final_missing_uuid_df.drop(columns=[old_col])
                
                missing_uuid_df = final_missing_uuid_df
        
        # Display summary stats
        st.subheader("Missing Records Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Buyer Records", len(buyer_df))
        with col2:
            st.metric("Missing Records (with valid keys)", len(missing_df))
        with col3:
            missing_percentage = (len(missing_df) / len(buyer_df) * 100) if len(buyer_df) > 0 else 0
            st.metric("Missing Percentage", f"{missing_percentage:.2f}%")
        
        # NOW DIRECTLY SHOW THE MISSING RECORDS
        if not missing_df.empty:
            st.subheader("Missing Records Detail")
            
            # Show a notification that all columns are included
            st.info("All original columns from the data file are included in the display and download.")
            
            # Display all columns
            st.dataframe(missing_df, use_container_width=True)
            
            # Add download button right here for immediate access
            csv = missing_df.to_csv(index=False)
            st.download_button(
                label="Download Missing Records CSV (All Columns)",
                data=csv,
                file_name="missing_records_all_columns.csv",
                mime="text/csv",
                help="Download the complete list of missing records with all original columns"
            )
            
            # Show total revenue impact
            if 'Revenue' in missing_df.columns:
                total_revenue = missing_df['Revenue'].sum()
                st.metric("Total Missing Revenue", f"${total_revenue:,.2f}")
        
        # If we have records with missing UUIDs/CallerIDs, display them separately
        if not missing_uuid_df.empty:
            if primary_match_method == "uuid":
                st.subheader(f"Records with Missing UUIDs: {len(missing_uuid_df)}")
            else:
                st.subheader(f"Records with Missing Caller IDs: {len(missing_uuid_df)}")
                
            # Show a notification that all columns are included
            st.info("All original columns from the data file are included in the display and download.")
            
            # Display all columns
            st.dataframe(missing_uuid_df, use_container_width=True)
            
            # Add download button for these records too
            csv = missing_uuid_df.to_csv(index=False)
            st.download_button(
                label=f"Download Records with Missing {'UUIDs' if primary_match_method == 'uuid' else 'Caller IDs'} CSV (All Columns)",
                data=csv,
                file_name=f"missing_{'uuid' if primary_match_method == 'uuid' else 'caller_id'}_records_all_columns.csv",
                mime="text/csv"
            )
    
    # Data Quality Issues tab
    with tabs[2]:
        st.subheader("Data Quality Analysis")
        
        # Check for null values in critical columns
        quality_issues = []
        
        # Check buyer dataframe
        total_buyer = len(buyer_df)
        if buyer_uuid_col:
            null_uuid = buyer_df[buyer_uuid_col].isna().sum()
            if null_uuid > 0:
                quality_issues.append({
                    "System": "Buyer",
                    "Column": buyer_uuid_col,
                    "Issue": "Missing Values",
                    "Count": null_uuid,
                    "Percentage": f"{(null_uuid/total_buyer*100):.2f}%"
                })
        
        if buyer_revenue_col:
            null_revenue = buyer_df[buyer_revenue_col].isna().sum()
            if null_revenue > 0:
                quality_issues.append({
                    "System": "Buyer",
                    "Column": buyer_revenue_col,
                    "Issue": "Missing Values",
                    "Count": null_revenue,
                    "Percentage": f"{(null_revenue/total_buyer*100):.2f}%"
                })
        
        if buyer_caller_id_col:
            null_caller = buyer_df[buyer_caller_id_col].isna().sum()
            if null_caller > 0:
                quality_issues.append({
                    "System": "Buyer",
                    "Column": buyer_caller_id_col,
                    "Issue": "Missing Values",
                    "Count": null_caller,
                    "Percentage": f"{(null_caller/total_buyer*100):.2f}%"
                })
        
        # Check CUB dataframe
        total_cub = len(cub_df)
        if cub_uuid_col:
            null_uuid = cub_df[cub_uuid_col].isna().sum()
            if null_uuid > 0:
                quality_issues.append({
                    "System": "CUB",
                    "Column": cub_uuid_col,
                    "Issue": "Missing Values",
                    "Count": null_uuid,
                    "Percentage": f"{(null_uuid/total_cub*100):.2f}%"
                })
        
        if cub_revenue_col:
            null_revenue = cub_df[cub_revenue_col].isna().sum()
            if null_revenue > 0:
                quality_issues.append({
                    "System": "CUB",
                    "Column": cub_revenue_col,
                    "Issue": "Missing Values",
                    "Count": null_revenue,
                    "Percentage": f"{(null_revenue/total_cub*100):.2f}%"
                })
        
        if cub_caller_id_col:
            null_caller = cub_df[cub_caller_id_col].isna().sum()
            if null_caller > 0:
                quality_issues.append({
                    "System": "CUB",
                    "Column": cub_caller_id_col,
                    "Issue": "Missing Values",
                    "Count": null_caller,
                    "Percentage": f"{(null_caller/total_cub*100):.2f}%"
                })
        
        # Display quality issues if any
        if quality_issues:
            st.write("The following data quality issues were found:")
            st.dataframe(pd.DataFrame(quality_issues), use_container_width=True)
        else:
            st.success("No data quality issues found in critical columns!")
            
        # Check for duplicate UUIDs
        if buyer_uuid_col:
            # Filter out missing UUIDs
            valid_buyer_uuids = buyer_df[~buyer_df[buyer_uuid_col].isna()][buyer_uuid_col]
            duplicate_uuids = valid_buyer_uuids[valid_buyer_uuids.duplicated()]
            if not duplicate_uuids.empty:
                st.warning(f"Found {len(duplicate_uuids)} duplicate UUIDs in Buyer dashboard")
                st.dataframe(buyer_df[buyer_df[buyer_uuid_col].isin(duplicate_uuids)])
        
        if cub_uuid_col:
            # Filter out missing UUIDs
            valid_cub_uuids = cub_df[~cub_df[cub_uuid_col].isna()][cub_uuid_col]
            duplicate_uuids = valid_cub_uuids[valid_cub_uuids.duplicated()]
            if not duplicate_uuids.empty:
                st.warning(f"Found {len(duplicate_uuids)} duplicate UUIDs in CUB dashboard")
                st.dataframe(cub_df[cub_df[cub_uuid_col].isin(duplicate_uuids)])
    
    # Process revenue discrepancies tab
    with tabs[3]:
        st.subheader("Finding Revenue Discrepancies")
        
        # Check if we have the required columns
        if not (buyer_uuid_col and cub_uuid_col and buyer_revenue_col and cub_revenue_col):
            st.error("Cannot analyze revenue discrepancies: missing required columns")
            discrepancies_df = pd.DataFrame(columns=["UUID", "Buyer Revenue", "CUB Revenue", "Difference"])
        else:
            st.write("Comparing revenues between Buyer and CUB dashboards based on UUID...")
            revenue_discrepancies = []
            
            # For each record that exists in both systems by UUID
            for uuid in uuids_in_both:
                try:
                    # Get the matching records
                    buyer_record = buyer_df[buyer_df["_UUID"] == uuid].iloc[0]
                    cub_record = cub_df[cub_df["_UUID"] == uuid].iloc[0]
                    
                    # Get revenues
                    buyer_revenue = buyer_record["_Revenue"]
                    cub_revenue = cub_record["_Revenue"]
                    
                    # Check if revenues match (with small tolerance for floating point)
                    if not pd.isna(buyer_revenue) and not pd.isna(cub_revenue):
                        # Calculate difference and check if it's significant
                        revenue_diff = float(buyer_revenue) - float(cub_revenue)
                        
                        # If difference is significant (more than 1 cent)
                        if abs(revenue_diff) > 0.01:
                            discrepancy = {
                                "_UUID": uuid,
                                "_BuyerRevenue": buyer_revenue,
                                "_CUBRevenue": cub_revenue,
                                "_RevenueDiff": revenue_diff
                            }
                            
                            # Add caller ID if available
                            if "_CallerId" in buyer_record:
                                discrepancy["_CallerId"] = buyer_record["_CallerId"]
                            
                            revenue_discrepancies.append(discrepancy)
                except Exception as e:
                    continue
            
            if not revenue_discrepancies:
                st.success("No revenue discrepancies found! All matching records have the same revenue.")
                discrepancies_df = pd.DataFrame(columns=["UUID", "Caller ID", "Buyer Revenue", "CUB Revenue", "Difference"])
            else:
                # Create discrepancies dataframe
                discrepancies_df = pd.DataFrame(revenue_discrepancies)
                
                # Rename columns for clarity
                columns_map = {
                    "_UUID": "UUID",
                    "_CallerId": "Caller ID",
                    "_BuyerRevenue": "Buyer Revenue",
                    "_CUBRevenue": "CUB Revenue",
                    "_RevenueDiff": "Difference"
                }
                
                # Create final dataframe with standardized column names
                final_discrepancies_df = pd.DataFrame()
                for old_col, new_col in columns_map.items():
                    if old_col in discrepancies_df.columns:
                        final_discrepancies_df[new_col] = discrepancies_df[old_col]
                
                discrepancies_df = final_discrepancies_df
                
                # Sort by absolute difference (largest first)
                discrepancies_df = discrepancies_df.sort_values(by="Difference", key=abs, ascending=False)
                
                st.warning(f"Found {len(discrepancies_df)} records with revenue discrepancies")
        
        # Display summary stats
        st.subheader("Revenue Discrepancies Summary")
        col1, col2, col3 = st.columns(3)
        try:
            with col1:
                st.metric("Records in Both Systems", len(uuids_in_both))
            with col2:
                st.metric("Records with Discrepancies", len(discrepancies_df))
            with col3:
                if len(uuids_in_both) > 0:
                    discrepancy_percentage = (len(discrepancies_df) / len(uuids_in_both) * 100)
                    st.metric("Discrepancy Percentage", f"{discrepancy_percentage:.2f}%")
                else:
                    st.metric("Discrepancy Percentage", "N/A")
        except Exception as e:
            st.error(f"Error calculating metrics: {str(e)}")
    
    # ADD THIS NEW SECTION HERE - identify unexplained records
    # Let's identify unexplained missing records
    # These are records that should be accounted for but aren't in our missing or missing_uuid sets
    unexplained_records = []
    
    # Extract all UIDs we've already accounted for
    accounted_uuids = set()
    if not missing_df.empty and 'UUID' in missing_df.columns:
        accounted_uuids.update(missing_df['UUID'].astype(str))
    
    # Also add missing UUID records (these typically have 'Missing UUID' as value)
    accounted_missing_uuids = set()
    if not missing_uuid_df.empty:
        if 'UUID' in missing_uuid_df.columns:
            accounted_missing_uuids.update(missing_uuid_df['UUID'].astype(str))
    
    # Find any remaining records that aren't accounted for
    for _, record in buyer_df.iterrows():
        if '_UUID' in record:
            uuid = str(record['_UUID'])
            # If this UUID isn't already in our tracked missing records
            # and it's not in CUB, it's unexplained
            if uuid not in accounted_uuids and uuid not in accounted_missing_uuids and uuid not in cub_uuids:
                unexplained_records.append(record)
    
    # Create dataframe of unexplained records
    unexplained_df = pd.DataFrame(unexplained_records)
    if not unexplained_df.empty:
        # Standardize column names
        final_unexplained_df = pd.DataFrame()
        for old_col, new_col in columns_map.items():
            if old_col in unexplained_df.columns:
                final_unexplained_df[new_col] = unexplained_df[old_col]
        
        # Add original columns if useful
        for col in unexplained_df.columns:
            if not col.startswith("_") and col not in final_unexplained_df.columns:
                if col in [buyer_uuid_col, buyer_revenue_col, buyer_caller_id_col]:
                    final_unexplained_df[col] = unexplained_df[col]
        
        unexplained_df = final_unexplained_df
    else:
        unexplained_df = pd.DataFrame(columns=["UUID", "Revenue", "Caller ID"])
    
    # Modify the return statement at the end of the function
    return {
        "missing": missing_df, 
        "missing_uuid": missing_uuid_df,
        "unexplained_missing": unexplained_df,
        "discrepancies": discrepancies_df if 'discrepancies_df' in locals() else pd.DataFrame(),
        "total_buyer_records": len(buyer_df),
        "total_cub_records": len(cub_df),
        "buyer_duplicates": buyer_duplicates,
        "buyer_df_for_analysis": buyer_df,
        "cub_df_for_analysis": cub_df,
        "primary_match_method": primary_match_method
    }

def display_results(results):
    missing_records = results["missing"]
    missing_uuid_records = results["missing_uuid"]
    unexplained_records = results.get("unexplained_missing", pd.DataFrame())
    discrepancies = results["discrepancies"]
    primary_match_method = results.get("primary_match_method", "uuid")  # Default to UUID if not specified
    
    # Extract just the matching keys for download (either UUID or Caller ID)
    all_missing_keys = []
    key_field = "UUID" if primary_match_method == "uuid" else "Caller ID"
    
    # Add keys from normal missing records
    if key_field in missing_records.columns:
        all_missing_keys.extend(missing_records[key_field].tolist())
    
    # Add keys from unexplained missing records
    if key_field in unexplained_records.columns:
        all_missing_keys.extend(unexplained_records[key_field].tolist())
    
    # Create a simple DataFrame with just the keys
    missing_keys_df = pd.DataFrame({f'Missing_{key_field}': all_missing_keys})
    
    # Set up tabs for different analyses
    tabs = st.tabs(["Missing Records Summary", "Duplicate Records", f"Missing {key_field}s", "Missing Records Detail", "Records with Missing Keys", "Unexplained Missing Records", "Revenue Discrepancies"])
    
    # NEW TAB: Missing Records Summary - Quick overview of the gap
    with tabs[0]:
        st.header("Missing Records Summary")
        
        # Calculate totals
        total_buyer_records = results.get("total_buyer_records", 0)
        total_cub_records = results.get("total_cub_records", 0)
        total_missing = len(missing_records)
        total_missing_uuid = len(missing_uuid_records)
        total_unexplained = len(unexplained_records)
        
        # Calculate the gap
        record_gap = total_buyer_records - total_cub_records
        
        # Display metrics in a more visible way
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Buyer Records", total_buyer_records)
        with col2:
            st.metric("Total CUB Records", total_cub_records)
        with col3:
            st.metric("Records Gap", record_gap, 
                     delta=f"{(record_gap/total_buyer_records*100):.1f}%" if total_buyer_records > 0 else "N/A")
        
        # Show matching method used
        st.info(f"Matching Method: {primary_match_method.upper()}")
        
        # Show breakdown of the missing records
        st.subheader("Missing Records Breakdown")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"Records with Valid {key_field} Missing from CUB", total_missing)
            missing_pct = (total_missing/total_buyer_records*100) if total_buyer_records > 0 else 0
            st.write(f"These records have {key_field}s but don't appear in CUB ({missing_pct:.1f}% of Buyer records)")
        
        with col2:
            st.metric(f"Records with Missing/Invalid {key_field}s", total_missing_uuid)
            missing_uuid_pct = (total_missing_uuid/total_buyer_records*100) if total_buyer_records > 0 else 0
            st.write(f"These records can't be matched due to missing {key_field}s ({missing_uuid_pct:.1f}% of Buyer records)")
            
        with col3:
            st.metric("Unexplained Missing Records", total_unexplained)
            unexplained_pct = (total_unexplained/total_buyer_records*100) if total_buyer_records > 0 else 0
            st.write(f"These records are missing for other reasons ({unexplained_pct:.1f}% of Buyer records)")
        
        # Calculate if there's any unexplained difference
        explained_missing = total_missing + total_missing_uuid + total_unexplained
        remaining_diff = record_gap - explained_missing
        
        if remaining_diff != 0:
            st.warning(f"⚠️ Still unexplained difference: {remaining_diff} records. Further investigation needed.")
        else:
            st.success(f"✅ All {record_gap} missing records have been identified and categorized.")
        
        # Show revenue impact
        if 'Revenue' in missing_records.columns:
            total_missing_revenue = missing_records['Revenue'].sum()
            st.metric("Total Missing Revenue", f"${total_missing_revenue:,.2f}")
            
            # Pie chart showing revenue distribution
            if total_missing > 0:
                try:
                    fig = px.pie(
                        missing_records.head(10),
                        values='Revenue',
                        names=key_field if key_field in missing_records.columns else 'Revenue',
                        title=f"Revenue Distribution of Top 10 Missing Records"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not create revenue chart: {str(e)}")
        
        # Add a new download button for just the keys
        st.subheader(f"Download Missing {key_field}s")
        total_missing_keys = len(all_missing_keys)
        st.write(f"Total {key_field}s missing from CUB: {total_missing_keys}")
        
        # Create a CSV with just the keys
        keys_csv = missing_keys_df.to_csv(index=False)
        st.download_button(
            label=f"Download All Missing {key_field}s as CSV",
            data=keys_csv,
            file_name=f"missing_{key_field.lower()}s.csv",
            mime="text/csv"
        )
        
        # Add duplicate analysis to the summary tab
        st.subheader("Duplicate Records Analysis")
        
        # Get the total buyer and CUB records
        total_buyer_records = results.get("total_buyer_records", 0)
        total_cub_records = results.get("total_cub_records", 0)
        record_gap = total_buyer_records - total_cub_records
        
        # Get duplicate info if available
        buyer_duplicates = results.get("buyer_duplicates", 0)
        if buyer_duplicates:
            st.metric("Duplicate Records in Buyer Dashboard", buyer_duplicates)
            
            if buyer_duplicates == record_gap:
                st.success(f"✅ The entire gap of {record_gap} records is explained by duplicates in the Buyer dashboard")
            elif buyer_duplicates > 0:
                st.info(f"Duplicates ({buyer_duplicates}) partially explain the gap of {record_gap} records")
        else:
            st.info("Duplicate records analysis not available. Check the 'Duplicate Records' tab for details.")
    
    # Tab 2: Missing Keys - A simple list of keys (UUIDs or Caller IDs)
    with tabs[2]:
        st.header(f"{key_field}s Missing from CUB Dashboard")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"Total {key_field}s Missing from CUB", len(all_missing_keys))
        with col2:
            st.download_button(
                label=f"Download Missing {key_field}s List",
                data=keys_csv,
                file_name=f"missing_{key_field.lower()}s.csv",
                mime="text/csv"
            )
        
        # Display the keys
        st.subheader(f"List of Missing {key_field}s")
        st.dataframe(missing_keys_df, use_container_width=True)
        
        # Alternative format - plain text for easy copying
        st.subheader("Plain Text (for copying)")
        all_keys_text = "\n".join(all_missing_keys)
        st.text_area(f"{key_field}s (one per line)", all_keys_text, height=300)
    
    # The remaining tabs with updated titles to reflect the matching method
    with tabs[3]:
        # Missing Records Detail tab
        if missing_records.empty:
            st.info(f"No missing records found in CUB Dashboard (with valid {key_field}s).")
        else:
            # Display summary statistics
            st.header("Missing Records Detail")
            
            # Key metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Missing Records", len(missing_records))
            with col2:
                try:
                    total_revenue = missing_records['Revenue'].sum() if 'Revenue' in missing_records.columns else 0
                    st.metric("Total Missing Revenue", f"${total_revenue:,.2f}")
                except Exception as e:
                    st.metric("Total Missing Revenue", "Error calculating")
            
            # Basic bar chart for top UUIDs by revenue
            try:
                # Get top 20 records by revenue
                if 'Revenue' in missing_records.columns:
                    top_records = missing_records.sort_values('Revenue', ascending=False).head(20)
                else:
                    top_records = missing_records.head(20)
                    
                fig = px.bar(
                    top_records,
                    x=key_field if key_field in top_records.columns else 'Revenue',
                    y='Revenue',
                    title="Top 20 Missing Records by Revenue",
                    labels={
                        key_field: key_field, 
                        'Revenue': 'Revenue ($)'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not create visualization: {str(e)}")
            
            # Display detailed records table
            st.subheader("Detailed Missing Records")
            st.dataframe(missing_records, use_container_width=True)
            
            # Download button for missing records
            csv = missing_records.to_csv(index=False)
            st.download_button(
                label="Download Missing Records CSV",
                data=csv,
                file_name="missing_records.csv",
                mime="text/csv"
            )
    
    with tabs[4]:
        # Records with Missing Keys tab
        if missing_uuid_records.empty:
            st.success(f"No records with missing {key_field}s found in Buyer Dashboard.")
        else:
            st.header(f"Records with Missing {key_field}s")
            
            # Key metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Records with Missing Keys", len(missing_uuid_records))
            with col2:
                try:
                    total_revenue = missing_uuid_records['Revenue'].sum() if 'Revenue' in missing_uuid_records.columns else 0
                    st.metric("Total Revenue", f"${total_revenue:,.2f}")
                except Exception as e:
                    st.metric("Total Revenue", "Error calculating")
            
            # Display detailed records table
            st.subheader("Records with Missing Keys")
            st.dataframe(missing_uuid_records, use_container_width=True)
            
            # Download button
            csv = missing_uuid_records.to_csv(index=False)
            st.download_button(
                label="Download Missing Keys Records CSV",
                data=csv,
                file_name="missing_keys_records.csv",
                mime="text/csv"
            )
    
    # NEW TAB: Unexplained Missing Records
    with tabs[5]:
        if unexplained_records.empty:
            st.success("No unexplained missing records found! All missing records are accounted for.")
        else:
            st.header(f"Unexplained Missing Records: {len(unexplained_records)}")
            
            # Key metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Unexplained Records", len(unexplained_records))
            with col2:
                try:
                    total_revenue = unexplained_records['Revenue'].sum() if 'Revenue' in unexplained_records.columns else 0
                    st.metric("Total Unexplained Missing Revenue", f"${total_revenue:,.2f}")
                except Exception as e:
                    st.metric("Total Unexplained Missing Revenue", "Error calculating")
            
            # Display detailed records table
            st.subheader("Unexplained Missing Records Detail")
            st.dataframe(unexplained_records, use_container_width=True)
            
            # Download button for unexplained records
            csv = unexplained_records.to_csv(index=False)
            st.download_button(
                label="Download Unexplained Missing Records CSV",
                data=csv,
                file_name="unexplained_missing_records.csv",
                mime="text/csv",
                help="Download the 39 records that are missing but not accounted for by UUID issues"
            )
            
            # Explanation
            st.info("""
            These records are missing from the CUB system but aren't accounted for by our standard checks.
            Possible reasons include:
            1. Data entry errors or formatting differences in UIDs
            2. Records excluded by filters in one system but not the other
            3. Timing differences in data processing between systems
            4. Special characters or encoding issues in IDs
            """)
    
    with tabs[6]:
        if discrepancies.empty:
            st.success("No revenue discrepancies found between systems!")
        else:
            # Display summary statistics
            st.header("Revenue Discrepancy Analysis")
            
            # Key metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Records with Discrepancies", len(discrepancies))
            with col2:
                try:
                    total_diff = discrepancies['Difference'].sum()
                    st.metric("Total Revenue Difference", f"${total_diff:,.2f}")
                except Exception as e:
                    st.metric("Total Revenue Difference", "Error calculating")
            with col3:
                try:
                    avg_diff = discrepancies['Difference'].mean()
                    st.metric("Average Difference", f"${avg_diff:,.2f}")
                except Exception as e:
                    st.metric("Average Difference", "Error calculating")
            
            # Create a histogram of differences
            try:
                fig = px.histogram(
                    discrepancies,
                    x='Difference',
                    title="Distribution of Revenue Differences",
                    labels={'Difference': 'Revenue Difference ($)'},
                    nbins=20
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not create histogram: {str(e)}")
            
            # Display detailed discrepancies table
            st.subheader("Detailed Revenue Discrepancies")
            st.dataframe(discrepancies, use_container_width=True)
            
            # Download button for discrepancies
            csv = discrepancies.to_csv(index=False)
            st.download_button(
                label="Download Discrepancies CSV",
                data=csv,
                file_name="revenue_discrepancies.csv",
                mime="text/csv"
            )

# Check if required files are uploaded
if buyer_file and cub_file:
    # Add Generate Report button
    if st.button("Generate Analysis Report", type="primary"):
        try:
            with st.spinner("Analyzing data..."):
                # Read the required files
                buyer_df = pd.read_csv(buyer_file)
                cub_df = pd.read_csv(cub_file)
                
                # Read Retreaver file if provided
                retreaver_df = None
                if retreaver_file:
                    retreaver_df = pd.read_csv(retreaver_file)
                
                # Simple check for empty files
                if buyer_df.empty or cub_df.empty:
                    st.error("One or more of the uploaded files is empty")
                else:
                    # Analyze data
                    results = analyze_data(buyer_df, cub_df, retreaver_df)
                    
                    if "error" not in results:
                        # Display results
                        display_results(results)
                        
                        # Show success message
                        st.success("Analysis completed successfully!")
                
        except Exception as e:
            st.error(f"An error occurred while processing the files: {str(e)}")
            st.error(f"Error details: {traceback.format_exc()}")
else:
    st.info("Please upload both the Buyer Dashboard and CUB Ringba Dashboard files to begin the analysis.") 