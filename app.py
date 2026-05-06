import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO
import traceback

# --- 1. Website Interface Setup ---
st.set_page_config(page_title="Firm Bank Statement Extractor", layout="centered")
st.title("🏦 Universal Bank Statement Extractor")
st.markdown("Upload any bank statement PDF. The system will standardize it into a 6-column Excel format.")

# --- 2. Universal Mapping Logic (With Safety Net) ---
def process_pdf(uploaded_file):
    try:
        all_rows = []
        
        # Dictionary to catch various bank column names
        column_mapping = {
            'txn date': 'Date', 'transaction date': 'Date', 'date': 'Date', 'value date': 'Date',
            'narration': 'Narration', 'particulars': 'Narration', 'description': 'Narration', 'details': 'Narration',
            'chq no': 'Cheque No/Other', 'cheque number': 'Cheque No/Other', 'ref no': 'Cheque No/Other', 'reference': 'Cheque No/Other',
            'withdrawal': 'Withdrawal', 'dr': 'Withdrawal', 'debit': 'Withdrawal', 'debits': 'Withdrawal',
            'deposit': 'Deposit', 'cr': 'Deposit', 'credit': 'Deposit', 'credits': 'Deposit',
            'balance': 'Balance', 'closing balance': 'Balance'
        }

        # Attempt to read the PDF
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        cleaned_table = [[str(cell).replace('\n', ' ').strip() if cell else '' for cell in row] for row in table]
                        all_rows.extend(cleaned_table)
        
        if not all_rows:
            return None, "No tables found. Is this PDF a scanned picture instead of text, or is it password protected?"

        df = pd.DataFrame(all_rows)
        
        # Find the header row
        header_idx = -1
        for i, row in df.iterrows():
            row_text = ' '.join([str(val).lower() for val in row.values])
            if 'date' in row_text or 'particular' in row_text or 'narration' in row_text:
                header_idx = i
                break
                
        if header_idx != -1:
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx+1:].reset_index(drop=True)
            
            # Apply the mapping
            new_columns = []
            for col in df.columns:
                col_lower = str(col).lower().strip()
                matched = False
                for key, std_name in column_mapping.items():
                    if key in col_lower:
                        new_columns.append(std_name)
                        matched = True
                        break
                if not matched:
                    new_columns.append('Ignore')
            
            df.columns = new_columns
            
            # Filter to exact requested format
            standard_cols = ['Date', 'Narration', 'Cheque No/Other', 'Withdrawal', 'Deposit', 'Balance']
            
            for col in standard_cols:
                if col not in df.columns:
                    df[col] = ''
                    
            final_df = df[standard_cols].copy()
            final_df = final_df.dropna(how='all')
            final_df = final_df[~final_df['Date'].astype(str).str.contains('Date', na=False, case=False)]
            
            return final_df, "Success"
        else:
            return None, "Could not identify the Date/Narration headers in this format."

    except Exception as e:
        # If it crashes, catch the exact error and send it to the website
        error_details = traceback.format_exc()
        return None, f"System Error: {str(e)}\n\nDetails:\n{error_details}"

# --- 3. Upload & Run Interface ---
uploaded_file = st.file_uploader("Drop PDF Statement Here", type=["pdf"])

if uploaded_file is not None:
    if st.button("Extract Data to Excel"):
        with st.spinner("Reading PDF... please wait."):
            
            # Run the process
            final_df, status = process_pdf(uploaded_file)
            
            # Check results
            if final_df is not None:
                st.success("Extraction Complete! Data standardized.")
                st.dataframe(final_df.head(10)) 
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='Standard_Data')
                processed_data = output.getvalue()
                
                st.download_button(
                    label="📥 Download Standardized Excel",
                    data=processed_data,
                    file_name="Standardized_Bank_Data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                # This is where the safety net prints the red text instead of spinning forever
                st.error("Extraction Failed!")
                st.error(status)
