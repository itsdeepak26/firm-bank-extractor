# --- 2. Universal Mapping Logic (UPDATED WITH SAFETY NET) ---
def process_pdf(uploaded_file):
    try: # <--- We added a TRY block
        all_rows = []
        
        column_mapping = {
            'txn date': 'Date', 'transaction date': 'Date', 'date': 'Date', 'value date': 'Date',
            'narration': 'Narration', 'particulars': 'Narration', 'description': 'Narration', 'details': 'Narration',
            'chq no': 'Cheque No/Other', 'cheque number': 'Cheque No/Other', 'ref no': 'Cheque No/Other', 'reference': 'Cheque No/Other',
            'withdrawal': 'Withdrawal', 'dr': 'Withdrawal', 'debit': 'Withdrawal', 'debits': 'Withdrawal',
            'deposit': 'Deposit', 'cr': 'Deposit', 'credit': 'Deposit', 'credits': 'Deposit',
            'balance': 'Balance', 'closing balance': 'Balance'
        }

        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        cleaned_table = [[str(cell).replace('\n', ' ').strip() if cell else '' for cell in row] for row in table]
                        all_rows.extend(cleaned_table)
        
        if not all_rows:
            return None, "No tabular data found in this PDF. Is it a scanned image?"

        df = pd.DataFrame(all_rows)
        
        header_idx = -1
        for i, row in df.iterrows():
            row_text = ' '.join([str(val).lower() for val in row.values])
            if 'date' in row_text or 'particular' in row_text or 'narration' in row_text:
                header_idx = i
                break
                
        if header_idx != -1:
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx+1:].reset_index(drop=True)
            
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
            standard_cols = ['Date', 'Narration', 'Cheque No/Other', 'Withdrawal', 'Deposit', 'Balance']
            
            for col in standard_cols:
                if col not in df.columns:
                    df[col] = ''
                    
            final_df = df[standard_cols].copy()
            final_df = final_df.dropna(how='all')
            final_df = final_df[~final_df['Date'].astype(str).str.contains('Date', na=False, case=False)]
            
            return final_df, "Success"
        else:
            return None, "Could not identify the header row (Date, Narration, etc.) in this format."

    except Exception as e:
        # <--- If ANYTHING fails, it stops the spinner and reports the error here
        return None, f"System Error crashed the app: {str(e)}"
