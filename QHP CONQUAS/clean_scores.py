"""
CONQUAS Score CSV Cleaner
=========================
This script reads the 'conquas_scores.csv' file, cleans the
'CONQUAS Band' column by removing negative signs and parentheses,
and then saves the cleaned data back to the same file.

Run:
    python clean_scores.py
"""

import pandas as pd
import os

CSV_FILE = "conquas_scores.csv"
EXCEL_FILE = "conquas_scores_6 March 2026.xlsx"

def clean_csv(file_path):
    """
    Reads the specified CSV, cleans the 'CONQUAS Band' column,
    and saves it back to the same file.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return

    try:
        df = pd.read_csv(file_path)
        print(f"Successfully read '{file_path}'.")

        if "CONQUAS Band" not in df.columns:
            print("Error: 'CONQUAS Band' column not found.")
            return

        print("Cleaning 'CONQUAS Band' column (removing '-', '(', and ')')...")
        # Use .astype(str) to prevent errors on non-string data
        # Use regex to remove any instance of '-', '(', or ')'
        cleaned_band = df["CONQUAS Band"].astype(str).str.replace(r'[-()#]', '', regex=True)

        # Convert numeric-like strings to numbers; keep non-numeric text as strings.
        band_numeric = pd.to_numeric(cleaned_band, errors="coerce")
        df["CONQUAS Band"] = band_numeric.where(band_numeric.notna(), cleaned_band)

        # Ensure the first column (S/N) is a running sequence: 1, 2, 3, ...
        df.iloc[:, 0] = range(1, len(df) + 1)

        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"Successfully cleaned and saved data back to '{file_path}'.")

        df.to_excel(EXCEL_FILE, index=False)
        print(f"Successfully saved Excel file as '{EXCEL_FILE}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    clean_csv(CSV_FILE)
