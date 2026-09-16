import os
import sys
import json
import argparse
import hashlib
from datetime import datetime
import pypdf

# Define directories relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")

def extract_pdf_text(pdf_path):
    """Extracts text page by page from the given PDF path."""
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found at {pdf_path}")
        sys.exit(1)
    
    try:
        reader = pypdf.PdfReader(pdf_path)
        extracted_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_text.append(f"--- PAGE {i + 1} ---\n{text}")
        return "\n\n".join(extracted_text)
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        sys.exit(1)

def generate_prompt_request(pdf_text, account_id, output_path):
    """Generates the prompt file for LLM extraction."""
    system_prompt = f"""You are a financial data extraction assistant.
Your task is to extract all transactions and closing balances from the bank/broker statement text provided below.

### Output Format:
You must output a single valid JSON object containing two lists:
1. "balances": A list of closing balance snapshots.
2. "transactions": A list of transaction records.

Do NOT include any markdown code formatting (like ```json), explanations, or text outside the JSON. Return only the raw JSON.

### JSON Schema:
{{
  "balances": [
    {{
      "as_of_date": "YYYY-MM-DD",
      "account_id": "{account_id}",
      "currency": "ARS" | "USD",
      "balance_original": 1234.56,
      "liquidity_tier": "immediate" | "short_term" | "invested",
      "notes": "Statement closing balance"
    }}
  ],
  "positions": [
    {{
      "as_of_date": "YYYY-MM-DD",
      "broker_account_id": "{account_id}",
      "asset_id": "TICKER",
      "asset_name": "Asset Name",
      "asset_class": "etf" | "stock" | "fund" | "bond" | "other",
      "quantity": 100.0,
      "currency": "ARS" | "USD",
      "cost_basis_original": 0.0,
      "market_value_original": 12345.67,
      "notes": "Position details"
    }}
  ],
  "transactions": [
    {{
      "txn_date": "YYYY-MM-DD",
      "posted_date": "YYYY-MM-DD",
      "description_raw": "Original bank transaction description",
      "amount_original": 123.45,  // positive for inflow, negative for outflow
      "currency": "ARS" | "USD",
      "direction": "inflow" | "outflow",
      "normalized_type": "expense" | "income" | "internal_transfer" | "investment_funding" | "asset_purchase" | "asset_sale" | "fee" | "fx_conversion" | "card_payment" | "unknown",
      "counterparty": "Merchant or recipient name",
      "is_internal_transfer": true | false,
      "expense_bucket": "housing" | "food" | "transport" | "health" | "social" | "shopping" | "hobbies" | "other" | "-",
      "expense_type": "fixed" | "discretionary" | "-",
      "notes": "Transaction details"
    }}
  ]
}}

### Account ID Context:
The statement belongs to account: {account_id}

### Rules:
1. "balance_original" and "amount_original" must be numeric floats.
2. Positive transaction amounts denote inflows (income, deposits), negative denote outflows (purchases, payments, withdrawals, fees).
3. If an expense_bucket or expense_type is not applicable, use "-".
4. Determine the expense_type (fixed vs. discretionary) based on the criteria:
   - "fixed": Housing/rent, health insurance, essential food/groceries, basic utilities/services.
   - "discretionary": Ocio/dining out, hobbies, shopping, social events, optional subscriptions.
   - "-": If the transaction is not an expense.
5. If posted_date is not available, default to txn_date.

### Input Text:
----------------------------------------
{pdf_text}
----------------------------------------
"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(system_prompt)
        print(f"✅ Prompt request generated successfully at: {output_path}")
        print("👉 Feed this file to your LLM and save the response JSON.")
    except Exception as e:
        print(f"❌ Error writing prompt request: {e}")
        sys.exit(1)

def get_last_day_of_month(date_str):
    """Calculates the YYYY-MM-DD of the last day of the month for the given date string."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.month == 12:
            next_month = datetime(dt.year + 1, 1, 1)
        else:
            next_month = datetime(dt.year, dt.month + 1, 1)
        last_day = next_month - type(next_month - dt)(days=1)
        return last_day.strftime("%Y-%m-%d")
    except Exception:
        return date_str

def get_fx_rate(date_str, from_currency):
    """Looks up FX rate in fx_rates.csv. Defaults to 1.0 for USD. For ARS, finds closest historical rate."""
    if from_currency == "USD":
        return 1.0
    
    fx_rates_path = os.path.join(NORMALIZED_DIR, "fx_rates.csv")
    if os.path.exists(fx_rates_path):
        try:
            import pandas as pd
            df_fx = pd.read_csv(fx_rates_path)
            df_ars = df_fx[df_fx["from_currency"] == from_currency].copy()
            if not df_ars.empty:
                df_ars["rate_date"] = pd.to_datetime(df_ars["rate_date"])
                target_dt = pd.to_datetime(date_str)
                diff = (df_ars["rate_date"] - target_dt).abs()
                closest_idx = diff.idxmin()
                return float(df_ars.loc[closest_idx, "fx_rate"])
        except Exception:
            pass
            
    return 0.0006535948  # Default to 1/1530 instead of 1.0

def load_csv_safely(filepath, headers):
    """Loads a CSV file or initializes it with headers if missing."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                # File exists and is populated
                import pandas as pd
                return pd.read_csv(filepath)
        except Exception:
            pass
            
    # File doesn't exist or is empty
    import pandas as pd
    return pd.DataFrame(columns=headers)

def normalize_response(json_path, source_filename):
    """Processes the JSON response and appends records to normalized CSVs."""
    if not os.path.exists(json_path):
        print(f"❌ Error: JSON response file not found at {json_path}")
        sys.exit(1)
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_content = f.read().strip()
            
        # Clean markdown code blocks if the LLM wrapped it
        if raw_content.startswith("```"):
            lines = raw_content.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_content = "\n".join(lines).strip()
            
        data = json.loads(raw_content)
    except Exception as e:
        print(f"❌ Error parsing JSON response: {e}")
        sys.exit(1)
        
    # Headers based on 02_data_model.md
    balance_headers = [
        "snapshot_date", "as_of_date", "account_id", "currency", 
        "balance_original", "fx_to_usd", "balance_usd", 
        "liquidity_tier", "source_type", "source_file", "notes"
    ]
    txn_headers = [
        "txn_id", "account_id", "txn_date", "posted_date", 
        "description_raw", "amount_original", "currency", "direction", 
        "normalized_type", "counterparty", "is_internal_transfer", 
        "expense_bucket", "expense_type", "needs_review", "source_file", "notes"
    ]
    
    # 1. Process Balances
    balances_to_add = data.get("balances", [])
    if balances_to_add:
        balances_filepath = os.path.join(NORMALIZED_DIR, "account_balances.csv")
        df_balances = load_csv_safely(balances_filepath, balance_headers)
        
        for bal in balances_to_add:
            as_of = bal.get("as_of_date")
            account = bal.get("account_id")
            currency = bal.get("currency")
            orig_val = float(bal.get("balance_original", 0))
            
            # snapshot_date defaults to end of the month
            snapshot_date = get_last_day_of_month(as_of)
            fx = float(bal.get("fx_to_usd", get_fx_rate(as_of, currency)))
            balance_usd = round(orig_val * fx, 2)
            
            new_row = {
                "snapshot_date": snapshot_date,
                "as_of_date": as_of,
                "account_id": account,
                "currency": currency,
                "balance_original": orig_val,
                "fx_to_usd": fx,
                "balance_usd": balance_usd,
                "liquidity_tier": bal.get("liquidity_tier", "immediate"),
                "source_type": "pdf",
                "source_file": source_filename,
                "notes": bal.get("notes", "Extracted closing balance")
            }
            
            # Check for duplicates (same snapshot_date, account_id, currency)
            duplicate_mask = (
                (df_balances["snapshot_date"] == snapshot_date) & 
                (df_balances["account_id"] == account) & 
                (df_balances["currency"] == currency)
            )
            
            # Remove old duplicate if exists, then add
            if duplicate_mask.any():
                df_balances = df_balances[~duplicate_mask]
            
            import pandas as pd
            df_balances = pd.concat([df_balances, pd.DataFrame([new_row])], ignore_index=True)
            
        # Write back
        os.makedirs(NORMALIZED_DIR, exist_ok=True)
        df_balances.to_csv(balances_filepath, index=False)
        print(f"📊 Processed {len(balances_to_add)} balance snapshots in account_balances.csv")

    # 2. Process Transactions
    txns_to_add = data.get("transactions", [])
    if txns_to_add:
        txns_filepath = os.path.join(NORMALIZED_DIR, "transactions_normalized.csv")
        df_txns = load_csv_safely(txns_filepath, txn_headers)
        
        added_count = 0
        skipped_count = 0
        
        for txn in txns_to_add:
            account = txn.get("account_id")
            txn_date = txn.get("txn_date")
            posted_date = txn.get("posted_date", txn_date)
            desc = txn.get("description_raw", "")
            amount = float(txn.get("amount_original", 0))
            currency = txn.get("currency", "USD")
            
            # Deterministic hash ID to prevent duplication
            raw_hash_string = f"{account}_{txn_date}_{amount}_{desc}"
            txn_id = hashlib.md5(raw_hash_string.encode('utf-8')).hexdigest()[:16]
            
            # Check duplicate by txn_id
            if txn_id in df_txns["txn_id"].values:
                skipped_count += 1
                continue
                
            new_row = {
                "txn_id": txn_id,
                "account_id": account,
                "txn_date": txn_date,
                "posted_date": posted_date,
                "description_raw": desc,
                "amount_original": amount,
                "currency": currency,
                "direction": txn.get("direction", "outflow" if amount < 0 else "inflow"),
                "normalized_type": txn.get("normalized_type", "expense"),
                "counterparty": txn.get("counterparty", "-"),
                "is_internal_transfer": bool(txn.get("is_internal_transfer", False)),
                "expense_bucket": txn.get("expense_bucket", "-"),
                "expense_type": txn.get("expense_type", "-"),
                "needs_review": bool(txn.get("needs_review", False)),
                "source_file": source_filename,
                "notes": txn.get("notes", "")
            }
            
            import pandas as pd
            df_txns = pd.concat([df_txns, pd.DataFrame([new_row])], ignore_index=True)
            added_count += 1
            
        # Write back
        os.makedirs(NORMALIZED_DIR, exist_ok=True)
        df_txns.to_csv(txns_filepath, index=False)
        print(f"💸 Transactions: {added_count} added, {skipped_count} skipped (duplicates) in transactions_normalized.csv")

    # 3. Process Positions
    positions_to_add = data.get("positions", [])
    if positions_to_add:
        pos_filepath = os.path.join(NORMALIZED_DIR, "investment_positions.csv")
        pos_headers = [
            "snapshot_date", "as_of_date", "broker_account_id", "asset_id", 
            "asset_name", "asset_class", "quantity", "currency", 
            "cost_basis_original", "market_value_original", "fx_to_usd", 
            "market_value_usd", "unrealized_pnl_usd", "notes"
        ]
        df_pos = load_csv_safely(pos_filepath, pos_headers)
        
        for pos in positions_to_add:
            as_of = pos.get("as_of_date")
            broker = pos.get("broker_account_id", "iol_broker")
            asset_id = str(pos.get("asset_id", "")).strip().upper()
            currency = pos.get("currency", "USD")
            qty = float(pos.get("quantity", 0))
            mv_orig = float(pos.get("market_value_original", 0))
            cost_orig = float(pos.get("cost_basis_original", 0))
            snapshot_date = get_last_day_of_month(as_of)
            fx = float(pos.get("fx_to_usd", get_fx_rate(as_of, currency)))
            mv_usd = round(mv_orig * fx, 2) if currency != "USD" else mv_orig
            pnl_usd = round((mv_orig - cost_orig) * fx, 2) if cost_orig > 0 else 0.0
            
            new_row = {
                "snapshot_date": snapshot_date,
                "as_of_date": as_of,
                "broker_account_id": broker,
                "asset_id": asset_id,
                "asset_name": pos.get("asset_name", asset_id),
                "asset_class": pos.get("asset_class", "other"),
                "quantity": qty,
                "currency": currency,
                "cost_basis_original": cost_orig,
                "market_value_original": mv_orig,
                "fx_to_usd": fx,
                "market_value_usd": mv_usd,
                "unrealized_pnl_usd": pnl_usd,
                "notes": pos.get("notes", "")
            }
            
            # Check for duplicates (same snapshot_date, broker_account_id, asset_id)
            duplicate_mask = (
                (df_pos["snapshot_date"] == snapshot_date) & 
                (df_pos["broker_account_id"] == broker) & 
                (df_pos["asset_id"] == asset_id)
            )
            if duplicate_mask.any():
                df_pos = df_pos[~duplicate_mask]
            df_pos = pd.concat([df_pos, pd.DataFrame([new_row])], ignore_index=True)
            
        os.makedirs(NORMALIZED_DIR, exist_ok=True)
        df_pos.to_csv(pos_filepath, index=False)
        print(f"📈 Positions: {len(positions_to_add)} positions updated in investment_positions.csv")

def main():
    parser = argparse.ArgumentParser(description="Generic PDF Parser for V1 Financials (Agent-in-the-Loop Mode)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--extract", help="Path to the PDF file to extract text from")
    group.add_argument("--normalize", help="Path to the LLM response JSON file to parse and normalize")
    
    parser.add_argument("--account", help="Account ID context for extraction (e.g. galicia_ars, schwab_broker)")
    parser.add_argument("--output", help="Custom output path for the prompt request file (defaults to prompt_request.txt next to PDF)")
    parser.add_argument("--source-file", help="Original source filename to log (defaults to JSON filename or PDF filename)")
    
    args = parser.parse_args()
    
    if args.extract:
        if not args.account:
            print("❌ Error: --account <account_id> is required in --extract mode.")
            sys.exit(1)
            
        pdf_path = args.extract
        output_path = args.output
        if not output_path:
            pdf_dir = os.path.dirname(pdf_path)
            pdf_name = os.path.basename(pdf_path)
            output_path = os.path.join(pdf_dir if pdf_dir else ".", f"prompt_{os.path.splitext(pdf_name)[0]}.txt")
            
        print(f"📖 Reading PDF: {pdf_path}...")
        pdf_text = extract_pdf_text(pdf_path)
        print(f"⚡ Extracted {len(pdf_text)} characters of text.")
        generate_prompt_request(pdf_text, args.account, output_path)
        
    elif args.normalize:
        json_path = args.normalize
        source_name = args.source_file
        if not source_name:
            source_name = os.path.basename(json_path)
            
        print(f"⚙️ Normalizing LLM JSON: {json_path}...")
        normalize_response(json_path, source_name)
        print("✅ Data normalization completed.")

if __name__ == "__main__":
    main()
