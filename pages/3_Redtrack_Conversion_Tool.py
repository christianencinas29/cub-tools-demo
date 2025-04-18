import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="CUB Admin Tools - Conversion Tool", layout="wide")

st.title("Redtrack Conversion Tool")
st.write("This app converts Ringba call log exports to the conversion format required for Redtrack Conversion uploads.")

# Configuration options in columns
col1, col2 = st.columns(2)
with col1:
    # Add conversion type selector
    conversion_types = ['50m', '5m', '10m', '15m', '30m', 'Lead', 'Contact', 'Revs', 'Upsell', 'Conncall', 'Rcall', 'Pcall', 'AddToCart', 'InitiateCheckout', 'AddPaymentInfo', 'ViewContent', 'Ncon', 'Paywall', 'PaywallNcon', 'Policy']
    selected_type = st.selectbox("Select Conversion Type", conversion_types, index=0)

with col2:
    # Add payout value input - only enabled for specific types
    payout_enabled_types = ['Lead', 'Pcall', 'Paywall', 'PaywallNcon']
    payout_enabled = selected_type in payout_enabled_types
    
    if payout_enabled:
        payout_value = st.number_input(
            "Payout Value", 
            min_value=0.0, 
            value=0.0, 
            step=0.1, 
            format="%.2f", 
            help="Available for Lead, Pcall, Paywall, and PaywallNcon conversion types"
        )
    else:
        st.text_input("Payout Value", value="0.00", disabled=True, help="Only available for Lead, Pcall, Paywall, and PaywallNcon conversion types")
        payout_value = 0.0

uploaded_file = st.file_uploader("Upload Ringba CSV Export (must have column 'Call Complete Timestamp' and 'Tag User rtkcid')", type="csv")

if uploaded_file is not None:
    # Read the uploaded file
    try:
        df = pd.read_csv(uploaded_file)
        st.write(f"**Original File Preview** - {len(df)} records")
        st.dataframe(df.head(5), use_container_width=True)
        
        # Add a Generate button to explicitly trigger the conversion
        if st.button("Generate Conversion File", type="primary"):
            # Process the data
            if 'tag:User:rtkcid' in df.columns and 'Call Complete Timestamp' in df.columns:
                # Filter rows with non-empty rtkcid
                df_filtered = df[df['tag:User:rtkcid'].notna() & (df['tag:User:rtkcid'] != '')]
                
                # Convert timestamps and add 4 hours (4/24 of a day)
                timestamps = pd.to_datetime(df_filtered['Call Complete Timestamp'])
                adjusted_timestamps = timestamps + timedelta(hours=4)
                
                # Create the conversion dataframe
                conversion_data = {
                    'Click ID': df_filtered['tag:User:rtkcid'],
                    'Payout': payout_value if payout_enabled else 0,
                    'CreatedAt': adjusted_timestamps.dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'Type': selected_type
                }
                
                result_df = pd.DataFrame(conversion_data)
                
                # Add a comparison of original vs adjusted timestamps for preview
                preview_df = pd.DataFrame({
                    'Click ID': df_filtered['tag:User:rtkcid'],
                    'Original Timestamp': timestamps.dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'Adjusted Timestamp (+4h)': adjusted_timestamps.dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'Payout': payout_value if payout_enabled else 0,
                    'Type': selected_type
                })
                
                success_message = f"✅ Successfully generated conversion file with {len(result_df)} records using type: {selected_type}"
                if payout_enabled and payout_value > 0:
                    success_message += f" and payout: ${payout_value:.2f}"
                st.success(success_message)
                
                st.write(f"**Conversion Output Preview** - {len(result_df)} records")
                st.dataframe(preview_df.head(10), use_container_width=True)
                
                # Download button with type in filename
                csv = result_df.to_csv(index=False)
                st.download_button(
                    label=f"Download Conversion CSV ({selected_type})",
                    data=csv,
                    file_name=f"ringba_conversions_{selected_type}.csv",
                    mime="text/csv",
                )
                
                # Stats
                col_count = 4 if payout_enabled and payout_value > 0 else 3
                cols = st.columns(col_count)
                
                cols[0].metric("Total Records Processed", len(df))
                cols[1].metric("Valid Conversions Created", len(result_df))
                cols[2].metric("Conversion Type", selected_type)
                
                if payout_enabled and payout_value > 0:
                    cols[3].metric("Payout Value", f"${payout_value:.2f}")
                    
            else:
                st.error("The file doesn't have the required columns: 'Tag User rtkcid' and 'Call Complete Timestamp'")
    
    except Exception as e:
        st.error(f"Error processing the file: {e}")

# Instructions sidebar
with st.sidebar:
    st.header("Instructions")
    st.write("""
    1. Export your call log data from Ringba
    2. Select the conversion type from the dropdown
    3. Set the payout value (only for Lead, Pcall, Paywall, and PaywallNcon types)
    4. Upload the CSV file using the uploader
    5. Click the "Generate Conversion File" button
    6. Preview the results and download the conversion file
    7. Upload the conversion file to the conversion upload page in Redtrack
    
    **Required Format:**
    - Click ID: from tag:User:rtkcid
    - Payout: value set in the payout field (Lead, Pcall, Paywall, PaywallNcon only)
    - CreatedAt: formatted from Call Complete Timestamp + 4 hours
    - Type: selected from dropdown (default is 50m)
    """)
    
    st.divider()
    st.write("Created by Admin Team") 
