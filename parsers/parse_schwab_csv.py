import os
import sys
import re
import io
import hashlib
import pandas as pd
from datetime import datetime

# Define directories relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")

POSITIONS_HEADERS = [
    "snapshot_date", "as_of_date", "broker_account_id", "asset_id", 
    "asset_name", "asset_class", "quantity", "currency", 
    "cost_basis_original", "market_value_original", "fx_to_usd", 
    "market_value_usd", "unrealized_pnl_usd", "notes"
]

CASHFLOWS_HEADERS = [
    "event_date", "broker_account_id", "asset_id", "event_type", 
    "quantity", "price_original", "gross_amount_original", "currency", 
    "fx_to_usd", "gross_amount_usd", "fees_original", "source_file", "notes"
]

BALANCE_HEADERS = [
    "snapshot_date", "as_of_date", "account_id", "currency", 
    "balance_original", "fx_to_usd", "balance_usd", 
    "liquidity_tier", "source_type", "source_file", "notes"
]

def load_csv_safely(filepath, headers):
    """Loads a CSV file or initializes it with headers if missing."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                return pd.read_csv(filepath)
        except Exception:
            pass
    return pd.DataFrame(columns=headers)

def clean_num(val, default=0.0):
    """Parses numeric strings with $, %, commas into float."""
    if pd.isna(val) or val is None:
        return default
    s = str(val).strip().replace("$", "").replace(",", "").replace("%", "")
    if not s or s in ["--", "N/A", "-"]:
        return default
    try:
        return float(s)
    except ValueError:
        return default

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

def parse_schwab_date(date_str):
    """
    Parses Schwab date strings like '09/08/2026' or '03/11/2026 as of 03/10/2026'.
    Returns effective date in YYYY-MM-DD format.
    """
    s = str(date_str).strip()
    if " as of " in s:
        parts = s.split(" as of ")
        effective_part = parts[1].strip()
        dt = datetime.strptime(effective_part, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    dt = datetime.strptime(s, "%m/%d/%Y")
    return dt.strftime("%Y-%m-%d")

def map_asset_class(asset_type_str):
    """Maps Schwab asset type to normalized asset_class."""
    t = str(asset_type_str).lower()
    if "etf" in t or "closed end" in t:
        return "etf"
    elif "equity" in t or "stock" in t:
        return "stock"
    elif "bond" in t or "fixed income" in t:
        return "bond"
    elif "cash" in t or "money market" in t:
        return "cash_equivalent"
    return "other"

def map_action_to_event_type(action_str, amount):
    """Maps Schwab transaction action to normalized event_type."""
    a = str(action_str).strip().lower()
    if a in ["buy", "reinvest shares"]:
        return "buy"
    elif a in ["sell"]:
        return "sell"
    elif a in ["reinvest dividend", "cash dividend", "pr yr cash div", "cash in lieu"]:
        return "dividend"
    elif a in ["moneylink transfer", "wire received", "moneylink adj"]:
        return "withdrawal" if amount < 0 else "deposit"
    elif a in ["credit interest", "interest adj"]:
        return "interest"
    elif a in ["nra tax adj", "pr yr nra tax"]:
        return "fee"
    elif a in ["stock split"]:
        return "stock_split"
    return "unknown"

def parse_positions(file_path, file_name=None, dry_run=False):
    """
    Parses Schwab Positions CSV export.
    Populates investment_positions.csv and cash balance in account_balances.csv.
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    if not file_name:
        file_name = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return False, f"Error reading positions file: {e}"

    if not lines:
        return False, "Positions file is empty"

    # Line 1 usually contains as_of_date
    header_line = lines[0]
    date_match = re.search(r"as of [^,]+,\s*(\d{4}/\d{2}/\d{2})", header_line)
    if date_match:
        as_of_date = date_match.group(1).replace("/", "-")
    else:
        # Fallback to current date or filename date
        fn_match = re.search(r"(\d{4}-\d{2}-\d{2})", file_name)
        as_of_date = fn_match.group(1) if fn_match else datetime.now().strftime("%Y-%m-%d")

    snapshot_date = get_last_day_of_month(as_of_date)

    # Find the line where CSV table headers start
    header_idx = -1
    for idx, line in enumerate(lines[:10]):
        if '"Symbol"' in line or 'Symbol' in line:
            header_idx = idx
            break

    if header_idx == -1:
        return False, "Could not find table headers in Schwab positions file."

    csv_data = "".join(lines[header_idx:])
    try:
        df = pd.read_csv(io.StringIO(csv_data))
    except Exception as e:
        return False, f"Error parsing CSV table: {e}"

    # Required columns check
    if "Symbol" not in df.columns or "Mkt Val (Market Value)" not in df.columns:
        return False, "Missing expected columns ('Symbol', 'Mkt Val') in Schwab positions export."

    positions_added = 0
    cash_balance = None

    positions_rows = []

    for _, row in df.iterrows():
        sym = str(row.get("Symbol", "")).strip()
        if not sym or sym in ["Positions Total", "--", "nan"]:
            continue

        desc = str(row.get("Description", "")).strip()
        asset_type = str(row.get("Asset Type", "")).strip()
        mkt_val = clean_num(row.get("Mkt Val (Market Value)"))

        # Check if cash row
        if sym == "Cash & Cash Investments" or "Cash and Money Market" in asset_type:
            cash_balance = mkt_val
            continue

        qty = clean_num(row.get("Qty (Quantity)"))
        cost_basis = clean_num(row.get("Cost Basis"))
        gain_loss = clean_num(row.get("Gain $ (Gain/Loss $)"))
        asset_class = map_asset_class(asset_type)

        positions_rows.append({
            "snapshot_date": snapshot_date,
            "as_of_date": as_of_date,
            "broker_account_id": "schwab_broker",
            "asset_id": sym,
            "asset_name": desc,
            "asset_class": asset_class,
            "quantity": qty,
            "currency": "USD",
            "cost_basis_original": cost_basis,
            "market_value_original": mkt_val,
            "fx_to_usd": 1.0,
            "market_value_usd": mkt_val,
            "unrealized_pnl_usd": gain_loss,
            "notes": f"Asset Type: {asset_type}" if asset_type and asset_type != "--" else ""
        })
        positions_added += 1

    if dry_run:
        print(f"🔍 [Dry-Run] Extracted {positions_added} positions and Cash=${cash_balance} for as_of_date={as_of_date}:")
        for p in positions_rows:
            print(f"   - {p['asset_id']}: Qty={p['quantity']}, MktVal=${p['market_value_usd']}, CostBasis=${p['cost_basis_original']}, Gain=${p['unrealized_pnl_usd']}")
        if cash_balance is not None:
            print(f"   - Cash Balance: ${cash_balance} USD (liquidity_tier=invested)")
        return True, f"Dry-Run: Extracted {positions_added} positions and cash=${cash_balance}."

    # Write positions to investment_positions.csv
    pos_file = os.path.join(NORMALIZED_DIR, "investment_positions.csv")
    df_pos = load_csv_safely(pos_file, POSITIONS_HEADERS)

    # Idempotence: Replace existing positions for same snapshot_date, schwab_broker and asset_ids
    if not df_pos.empty:
        mask = (df_pos["snapshot_date"] == snapshot_date) & (df_pos["broker_account_id"] == "schwab_broker")
        df_pos = df_pos[~mask]

    df_pos = pd.concat([df_pos, pd.DataFrame(positions_rows)], ignore_index=True)
    os.makedirs(NORMALIZED_DIR, exist_ok=True)
    df_pos.to_csv(pos_file, index=False)

    # Write Cash balance to account_balances.csv
    if cash_balance is not None:
        bal_file = os.path.join(NORMALIZED_DIR, "account_balances.csv")
        df_bal = load_csv_safely(bal_file, BALANCE_HEADERS)

        cash_row = {
            "snapshot_date": snapshot_date,
            "as_of_date": as_of_date,
            "account_id": "schwab_broker",
            "currency": "USD",
            "balance_original": cash_balance,
            "fx_to_usd": 1.0,
            "balance_usd": cash_balance,
            "liquidity_tier": "invested",
            "source_type": "csv",
            "source_file": file_name,
            "notes": "Schwab uninvested cash / cash investments"
        }

        if not df_bal.empty:
            bal_mask = (
                (df_bal["snapshot_date"] == snapshot_date) & 
                (df_bal["account_id"] == "schwab_broker") & 
                (df_bal["currency"] == "USD")
            )
            df_bal = df_bal[~bal_mask]

        df_bal = pd.concat([df_bal, pd.DataFrame([cash_row])], ignore_index=True)
        df_bal.to_csv(bal_file, index=False)

    return True, f"Successfully parsed {positions_added} positions and Cash balance (${cash_balance} USD)."

def parse_transactions(file_path, file_name=None, dry_run=False):
    """
    Parses Schwab Transactions CSV export.
    Populates investment_cashflows.csv.
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    if not file_name:
        file_name = os.path.basename(file_path)

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return False, f"Error reading transactions file: {e}"

    req_cols = ["Date", "Action", "Description"]
    for c in req_cols:
        if c not in df.columns:
            return False, f"Missing column '{c}' in Schwab transactions CSV"

    cashflows_file = os.path.join(NORMALIZED_DIR, "investment_cashflows.csv")
    df_cf = load_csv_safely(cashflows_file, CASHFLOWS_HEADERS)

    # To ensure idempotence and prevent duplicates, compute deterministic row signatures
    existing_hashes = set()
    if not df_cf.empty:
        for _, r in df_cf.iterrows():
            sig = f"{r.get('event_date')}_{r.get('broker_account_id')}_{r.get('asset_id')}_{r.get('event_type')}_{r.get('quantity')}_{r.get('gross_amount_original')}_{r.get('notes')}"
            existing_hashes.add(sig)

    new_rows = []
    added_count = 0
    skipped_count = 0

    for _, row in df.iterrows():
        raw_date = row.get("Date")
        if pd.isna(raw_date):
            continue

        try:
            event_date = parse_schwab_date(raw_date)
        except Exception:
            continue

        action = str(row.get("Action", "")).strip()
        sym = str(row.get("Symbol", "")).strip()
        if pd.isna(row.get("Symbol")) or sym.lower() == "nan" or not sym:
            sym = "-"

        desc = str(row.get("Description", "")).strip()
        qty = clean_num(row.get("Quantity"))
        price = clean_num(row.get("Price"))
        fees = clean_num(row.get("Fees & Comm"))
        amt = clean_num(row.get("Amount"))

        event_type = map_action_to_event_type(action, amt)
        gross_amt = abs(amt)

        notes_parts = []
        if action:
            notes_parts.append(f"Action: {action}")
        if desc:
            notes_parts.append(desc)
        if " as of " in str(raw_date):
            notes_parts.append(f"Original Date: {raw_date}")
        notes = " | ".join(notes_parts)

        row_sig = f"{event_date}_schwab_broker_{sym}_{event_type}_{qty}_{gross_amt}_{notes}"
        if row_sig in existing_hashes:
            skipped_count += 1
            continue

        existing_hashes.add(row_sig)
        new_rows.append({
            "event_date": event_date,
            "broker_account_id": "schwab_broker",
            "asset_id": sym,
            "event_type": event_type,
            "quantity": qty,
            "price_original": price,
            "gross_amount_original": gross_amt,
            "currency": "USD",
            "fx_to_usd": 1.0,
            "gross_amount_usd": gross_amt,
            "fees_original": fees,
            "source_file": file_name,
            "notes": notes
        })
        added_count += 1

    if dry_run:
        print(f"🔍 [Dry-Run] Processed {len(df)} transactions: {added_count} to add, {skipped_count} skipped (duplicates).")
        for r in new_rows[:5]:
            print(f"   - {r['event_date']} [{r['event_type']}] {r['asset_id']}: Qty={r['quantity']}, Amt=${r['gross_amount_usd']}, Notes={r['notes']}")
        if len(new_rows) > 5:
            print(f"   ... and {len(new_rows) - 5} more records.")
        return True, f"Dry-Run: {added_count} to add, {skipped_count} skipped."

    if new_rows:
        df_cf = pd.concat([df_cf, pd.DataFrame(new_rows)], ignore_index=True)
        # Sort chronologically
        df_cf = df_cf.sort_values(by=["event_date"], ascending=True)
        os.makedirs(NORMALIZED_DIR, exist_ok=True)
        df_cf.to_csv(cashflows_file, index=False)

    return True, f"Successfully parsed transactions: {added_count} added, {skipped_count} skipped (duplicates)."
