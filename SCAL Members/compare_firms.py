"""Utility to compare an external firm list against the SCAL member CSV.

Reads the pre‑scraped ``scal_members.csv`` (must already exist) and performs a
fuzzy match of each name in an input list. The result is written to an Excel
file with a yes/no column indicating membership.

Usage:
    python compare_firms.py [Firm List_SEG.xlsx] [--threshold 80] [--output CompareSCALwSEG.csv]

Requirements:
    pip install pandas rapidfuzz openpyxl

The input firm list may be a CSV/Excel/PLAIN text file containing one name per
line; the script will try to load it automatically.
"""

import argparse
import pandas as pd
import os
import re


def load_firm_list(path: str) -> list[str]:
    """Load a one-column list of names from various file formats."""
    try:
        df = pd.read_csv(path, header=None)
    except Exception:
        try:
            df = pd.read_excel(path, header=None)
        except Exception:
            with open(path, encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
    return df.iloc[:, 0].astype(str).tolist()


def clean_company_name(name: str) -> str:
    """Remove common legal suffixes and punctuation for better matching."""
    if not name or pd.isna(name):
        return ""
    # Convert to uppercase
    name = str(name).upper()
    # Remove content inside parentheses like (PTE) or (S)
    name = re.sub(r'\(.*?\)', '', name)
    # Remove punctuation
    name = re.sub(r'[^\w\s]', ' ', name)
    # Remove common legal suffixes
    suffixes = [
        "PTE", "LTD", "LIMITED", "PRIVATE", "LLP", "CO", "CORP", "CORPORATION",
        "INC", "BHD", "SDN", "AND", "&"
    ]
    pattern = r'\b(' + '|'.join(suffixes) + r')\b'
    name = re.sub(pattern, '', name)
    # Collapse multiple spaces
    return " ".join(name.split())


def fuzzy_match_firms(firms: list[str], members_df: pd.DataFrame, threshold: int = 80) -> pd.DataFrame:
    """Return a DataFrame comparing firms against member names."""
    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        raise ImportError("rapidfuzz is required; install with `pip install rapidfuzz`.")

    original_names = members_df["name"].astype(str).tolist()
    # Create a cleaned version of the master list for matching
    cleaned_master_list = [clean_company_name(n) for n in original_names]

    rows = []
    for firm in firms:
        if not firm or pd.isna(firm):
            rows.append([firm, None, None, "No"])
            continue
        
        cleaned_firm = clean_company_name(firm)
        if not cleaned_firm: # Fallback if cleaning removed everything
            cleaned_firm = str(firm)
            
        # Match cleaned input against cleaned master list
        # extractOne returns (match_string, score, index)
        match = process.extractOne(cleaned_firm, cleaned_master_list, scorer=fuzz.token_sort_ratio)
        
        if match and match[1] >= threshold:
            # Retrieve the original name using the index
            best_match_original = original_names[match[2]]

            # Check if first word matches exactly
            input_words = cleaned_firm.split()
            match_words = match[0].split()

            if input_words and match_words and input_words[0] == match_words[0]:
                rows.append([firm, best_match_original, match[1], "Yes"])
            else:
                rows.append([firm, best_match_original, match[1], "No"])
        else:
            best_match_original = original_names[match[2]] if match else None
            rows.append([firm, best_match_original, match[1] if match else None, "No"])

    return pd.DataFrame(rows, columns=["firm", "best_match", "score", "in_scal"])


def main():
    parser = argparse.ArgumentParser(description="Compare firm names to SCAL members")
    parser.add_argument("firm_file", nargs="?", help="Path to file containing firm names to check")
    parser.add_argument("--threshold", type=int, default=80, help="minimum match score")
    parser.add_argument("--output", default="CompareSCALwSEG.csv", help="Output path (CSV or Excel)")
    args = parser.parse_args()

    firm_file = args.firm_file
    if not firm_file:
        # Check for default files in order of preference
        for candidate in ["Firm List_SEG.csv", "Firm List_SEG.xlsx"]:
            if os.path.exists(candidate):
                firm_file = candidate
                break
        if not firm_file:
            print("Error: No input file provided and default files (Firm List_SEG.csv/xlsx) not found.")
            return

    member_csv = "scal_members.csv"
    try:
        members_df = pd.read_csv(member_csv)
    except FileNotFoundError:
        print(f"Error: {member_csv} not found. Run the scraper first.")
        return

    firms = load_firm_list(firm_file)
    print(f"Loaded {len(firms)} firm names from {firm_file}")

    result = fuzzy_match_firms(firms, members_df, threshold=args.threshold)

    if args.output.lower().endswith(".csv"):
        result.to_csv(args.output, index=False)
    else:
        result.to_excel(args.output, index=False)
    print(f"Wrote comparison file {args.output}")

    print(result.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
