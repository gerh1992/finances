import os
import sys
import pandas as pd
import hashlib
from datetime import datetime

# Define directories relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")

def load_csv_safely(filepath, headers):
    """Loads a CSV file or initializes it with headers if missing."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                # File exists and is populated
                return pd.read_csv(filepath)
        except Exception:
            pass
            
    # File doesn't exist or is empty
    return pd.DataFrame(columns=headers)

def classify_transaction(row, desc, amount):
    """
    Classifies Mercado Pago transaction based on description, types and amounts.
    Returns (normalized_type, expense_bucket, expense_type, needs_review)
    """
    # Default values
    normalized_type = "expense" if amount < 0 else "income"
    expense_bucket = "-"
    expense_type = "-"
    needs_review = False

    tx_type = str(row.get("TRANSACTION_TYPE", "")).strip().upper()
    pm_type = str(row.get("PAYMENT_METHOD_TYPE", "")).strip().lower()

    # If it is a payout or transfer
    if tx_type == "PAYOUTS":
        normalized_type = "internal_transfer"
        needs_review = True  # Flag to let user confirm if it's their own account or a third-party payment
    elif pm_type == "bank_transfer":
        normalized_type = "internal_transfer"
        needs_review = True  # Flag to let user confirm if it's their own account
    elif tx_type == "SETTLEMENT":
        # Standard payment or settlement
        if amount < 0:
            normalized_type = "expense"
            desc_lower = desc.lower()
            
            # Category: Shopping
            if "mercado libre" in desc_lower or "mercadolibre" in desc_lower:
                expense_bucket = "shopping"
                expense_type = "discretionary"
            # Category: Food / Groceries
            elif any(x in desc_lower for x in ["coto", "carrefour", "jumbo", "disco", "dia", "supermercado"]):
                expense_bucket = "food"
                expense_type = "fixed"
            # Category: Transport
            elif any(x in desc_lower for x in ["uber", "cabify", "didi", "sube", "subte"]):
                expense_bucket = "transport"
                expense_type = "discretionary"
            # Category: Hobbies / Subscriptions
            elif any(x in desc_lower for x in ["netflix", "spotify", "disney", "hbo", "steam"]):
                expense_bucket = "hobbies"
                expense_type = "discretionary"
            else:
                # Default unknown expense
                expense_bucket = "other"
                expense_type = "discretionary"
                needs_review = True
        else:
            normalized_type = "income"
    elif "FEE" in tx_type:
        normalized_type = "fee"
        expense_bucket = "other"
        expense_type = "fixed"

    return normalized_type, expense_bucket, expense_type, needs_review

def parse_and_normalize(file_path, file_name, dry_run=False):
    """
    Parses Mercado Pago CSV file, normalizes fields, and writes to transactions_normalized.csv.
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
        
    try:
        # Load Mercado Pago CSV
        # Separator is ;
        df_raw = pd.read_csv(file_path, sep=";")
    except Exception as e:
        return False, f"Failed to read Mercado Pago CSV: {e}"
        
    required_cols = ["SOURCE_ID", "TRANSACTION_DATE", "SETTLEMENT_DATE", "REAL_AMOUNT", "BUSINESS_UNIT", "SUB_UNIT", "TRANSACTION_TYPE"]
    for col in required_cols:
        if col not in df_raw.columns:
            return False, f"Missing required column in Mercado Pago CSV: {col}"
            
    txn_headers = [
        "txn_id", "account_id", "txn_date", "posted_date", 
        "description_raw", "amount_original", "currency", "direction", 
        "normalized_type", "counterparty", "is_internal_transfer", 
        "expense_bucket", "expense_type", "needs_review", "source_file", "notes"
    ]
    
    # 1. Load existing transactions
    txns_filepath = os.path.join(NORMALIZED_DIR, "transactions_normalized.csv")
    df_txns = load_csv_safely(txns_filepath, txn_headers)
    
    added_count = 0
    skipped_count = 0
    
    # Iterate through rows
    new_rows = []
    
    # Process from oldest to newest if needed, but order of CSV is fine
    for idx, row in df_raw.iterrows():
        source_id = str(row["SOURCE_ID"])
        # Handle decimal formats or NaN
        if not source_id or pd.isna(row["SOURCE_ID"]):
            continue
        
        # Clean source_id of float formatting (e.g. 1.23e+11)
        if "." in source_id:
            try:
                source_id = str(int(float(source_id)))
            except ValueError:
                pass
                
        # Unique txn_id
        txn_id = f"mp_{source_id}"
        
        # Check duplicate in loaded df_txns
        if txn_id in df_txns["txn_id"].values:
            skipped_count += 1
            continue
            
        # Parse Dates
        # Format in MP: 2026-04-30T22:06:00.000-03:00
        txn_date_raw = str(row["TRANSACTION_DATE"])
        settlement_date_raw = str(row["SETTLEMENT_DATE"])
        
        txn_date = txn_date_raw.split("T")[0] if "T" in txn_date_raw else txn_date_raw
        posted_date = settlement_date_raw.split("T")[0] if "T" in settlement_date_raw and not pd.isna(row["SETTLEMENT_DATE"]) else txn_date
        if pd.isna(row["SETTLEMENT_DATE"]):
            posted_date = txn_date
            
        # Amount (using REAL_AMOUNT)
        amount = float(row["REAL_AMOUNT"])
        
        # Currency (derived from filename / context. ARS by default since it is Mercado Pago Argentina)
        currency = "ARS"
        if "usd" in file_name.lower():
            currency = "USD"
            
        # Description
        business_unit = str(row["BUSINESS_UNIT"]).strip() if not pd.isna(row["BUSINESS_UNIT"]) else ""
        sub_unit = str(row["SUB_UNIT"]).strip() if not pd.isna(row["SUB_UNIT"]) else ""
        txn_type = str(row["TRANSACTION_TYPE"]).strip()
        
        desc_parts = []
        if business_unit:
            desc_parts.append(business_unit)
        if sub_unit:
            desc_parts.append(sub_unit)
            
        if desc_parts:
            desc = " - ".join(desc_parts) + f" ({txn_type})"
        else:
            desc = txn_type
            
        # Counterparty
        counterparty = business_unit if business_unit else "-"
        
        # Classification
        normalized_type, expense_bucket, expense_type, needs_review = classify_transaction(row, desc, amount)
        
        is_internal_transfer = (normalized_type == "internal_transfer")
        direction = "inflow" if amount >= 0 else "outflow"
        
        new_row = {
            "txn_id": txn_id,
            "account_id": "mercadopago_ars" if currency == "ARS" else "mercadopago_usd",
            "txn_date": txn_date,
            "posted_date": posted_date,
            "description_raw": desc,
            "amount_original": amount,
            "currency": currency,
            "direction": direction,
            "normalized_type": normalized_type,
            "counterparty": counterparty,
            "is_internal_transfer": is_internal_transfer,
            "expense_bucket": expense_bucket,
            "expense_type": expense_type,
            "needs_review": needs_review,
            "source_file": file_name,
            "notes": f"Ingested via parse_mercadopago_csv.py"
        }
        new_rows.append(new_row)
        added_count += 1
        
    if added_count > 0 and not dry_run:
        df_new = pd.DataFrame(new_rows)
        df_txns = pd.concat([df_txns, df_new], ignore_index=True)
        os.makedirs(NORMALIZED_DIR, exist_ok=True)
        # Ensure we write exact column order to match CSV header
        df_txns = df_txns[txn_headers]
        df_txns.to_csv(txns_filepath, index=False)
            
    msg = f"Parsed {added_count + skipped_count} rows: {added_count} added, {skipped_count} skipped (duplicates)."
    return True, msg
