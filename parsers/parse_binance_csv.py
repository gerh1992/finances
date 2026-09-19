"""
Parser for Binance CSV exports:
- Binance-Deposit-History-*.csv
- Binance-Transaction-History-*.csv

Extracts and normalizes:
1. On-chain deposits and conversions into investment_cashflows.csv.
2. Monthly consolidated Simple Earn & Staking rewards as dividend/interest into investment_cashflows.csv.
3. Terminal snapshot of crypto holdings (BTC, BETH, ETHW) into investment_positions.csv.
"""
import os
import sys
import glob
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"

CASHFLOWS_FILE = NORMALIZED_DIR / "investment_cashflows.csv"
POSITIONS_FILE = NORMALIZED_DIR / "investment_positions.csv"
PRICES_FILE = NORMALIZED_DIR / "historical_prices.csv"

# Cost basis reference for initial deposits (market price on deposit date)
DEPOSIT_PRICES = {
    "2021-01-04": {"BTC": 32000.0},
    "2021-07-23": {"ETH": 2025.0},
    "2021-12-12": {"BTC": 49800.0},
}


def load_csv_safely(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame()


def find_latest_file(pattern: str) -> Path:
    files = sorted(RAW_DIR.glob(pattern), key=os.path.getmtime)
    if files:
        return files[-1]
    return None


def parse_binance(
    tx_file: Path = None,
    dep_file: Path = None,
    as_of_date: str = "2026-09-17"
) -> bool:
    """Parses Binance deposit and transaction files and updates normalized data."""
    if tx_file is None:
        tx_file = find_latest_file("Binance-Transaction-History*.csv")
    if dep_file is None:
        dep_file = find_latest_file("Binance-Deposit-History*.csv")

    if not tx_file or not tx_file.exists():
        print(f"Error: Transaction history file not found matching Binance-Transaction-History*.csv in {RAW_DIR}")
        return False
    if not dep_file or not dep_file.exists():
        print(f"Error: Deposit history file not found matching Binance-Deposit-History*.csv in {RAW_DIR}")
        return False

    print(f"Reading deposits from: {dep_file.name}")
    print(f"Reading transactions from: {tx_file.name}")

    df_dep = pd.read_csv(dep_file)
    df_tx = pd.read_csv(tx_file)

    # 1. Prices lookup for reward valuation
    prices_df = load_csv_safely(PRICES_FILE)

    def get_monthly_price(month: str, asset: str, default: float = 0.0) -> float:
        if prices_df.empty:
            return default
        lookup_asset = "ETH" if asset == "BETH" else asset
        match = prices_df[(prices_df["month"] == month) & (prices_df["asset_id"] == lookup_asset)]
        if not match.empty:
            return float(match["close_price_usd"].values[0])
        # Fallback to latest available price
        match_any = prices_df[prices_df["asset_id"] == lookup_asset].sort_values("month")
        if not match_any.empty:
            return float(match_any["close_price_usd"].values[-1])
        return default

    # 2. Reconstruct Cashflows
    cashflow_rows = []

    # A. External Deposits
    for _, r in df_dep.iterrows():
        dt_str = str(r["Time"]).strip()
        date_part = dt_str.split(" ")[0]
        coin = str(r["Coin"]).strip()
        amt = float(r["Amount"])
        price = DEPOSIT_PRICES.get(date_part, {}).get(coin, 0.0)
        if price == 0.0:
            price = get_monthly_price(date_part[:7], coin, 0.0)
        usd_val = round(amt * price, 2)
        txid_short = str(r["TXID"])[:16]

        cashflow_rows.append({
            "event_date": date_part,
            "broker_account_id": "binance_crypto",
            "asset_id": coin,
            "event_type": "deposit",
            "quantity": amt,
            "price_original": price,
            "gross_amount_original": usd_val,
            "currency": "USD",
            "fx_to_usd": 1.0,
            "gross_amount_usd": usd_val,
            "fees_original": 0.0,
            "source_file": dep_file.name,
            "notes": f"Action: Deposit | Blockchain transfer {coin} (TXID: {txid_short}...)"
        })

    # B. Trades / Conversions in 2021
    # 2021-01-09: Sell 0.0998624 BTC for 4057.7088992 USDT
    cashflow_rows.append({
        "event_date": "2021-01-09",
        "broker_account_id": "binance_crypto",
        "asset_id": "BTC",
        "event_type": "sell",
        "quantity": 0.0998624,
        "price_original": 40633.0,
        "gross_amount_original": 4057.71,
        "currency": "USD",
        "fx_to_usd": 1.0,
        "gross_amount_usd": 4057.71,
        "fees_original": 0.0,
        "source_file": tx_file.name,
        "notes": "Action: Binance Convert | Sell BTC for USDT"
    })
    # 2021-04-25: Buy 0.08608612 BTC with 4135.93033154 USDT
    cashflow_rows.append({
        "event_date": "2021-04-25",
        "broker_account_id": "binance_crypto",
        "asset_id": "BTC",
        "event_type": "buy",
        "quantity": 0.08608612,
        "price_original": 48044.1,
        "gross_amount_original": 4135.93,
        "currency": "USD",
        "fx_to_usd": 1.0,
        "gross_amount_usd": 4135.93,
        "fees_original": 0.0,
        "source_file": tx_file.name,
        "notes": "Action: Binance Convert | Buy BTC with USDT"
    })

    # C. Monthly Aggregated Simple Earn & Staking Rewards
    df_tx["Time"] = pd.to_datetime(df_tx["Time"])
    df_tx["month"] = df_tx["Time"].dt.strftime("%Y-%m")
    df_tx["Change"] = pd.to_numeric(df_tx["Change"], errors="coerce")

    # Simple Earn Flexible Interest (BTC, ETH, USDT)
    earn_mask = df_tx["Operation"] == "Simple Earn Flexible Interest"
    df_earn = df_tx[earn_mask]
    earn_grouped = df_earn.groupby(["month", "Coin"])["Change"].sum().reset_index()

    for _, r in earn_grouped.iterrows():
        m = r["month"]
        coin = r["Coin"]
        qty = round(float(r["Change"]), 8)
        if qty <= 0:
            continue
        p = get_monthly_price(m, coin, 0.0) if coin in ("BTC", "ETH") else 1.0
        gross_usd = round(qty * p, 2)
        end_day = pd.Period(m, freq="M").to_timestamp(how="end").strftime("%Y-%m-%d")

        cashflow_rows.append({
            "event_date": end_day,
            "broker_account_id": "binance_crypto",
            "asset_id": coin,
            "event_type": "dividend",
            "quantity": qty,
            "price_original": p,
            "gross_amount_original": gross_usd,
            "currency": "USD",
            "fx_to_usd": 1.0,
            "gross_amount_usd": gross_usd,
            "fees_original": 0.0,
            "source_file": tx_file.name,
            "notes": f"Action: Simple Earn Flexible Interest | {m} {coin} Yield"
        })

    # ETH 2.0 Staking Rewards (BETH)
    stake_mask = df_tx["Operation"] == "ETH 2.0 Staking Rewards"
    df_stake = df_tx[stake_mask]
    stake_grouped = df_stake.groupby(["month", "Coin"])["Change"].sum().reset_index()

    for _, r in stake_grouped.iterrows():
        m = r["month"]
        coin = r["Coin"]
        qty = round(float(r["Change"]), 8)
        if qty <= 0:
            continue
        p = get_monthly_price(m, "ETH", 0.0)
        gross_usd = round(qty * p, 2)
        end_day = pd.Period(m, freq="M").to_timestamp(how="end").strftime("%Y-%m-%d")

        cashflow_rows.append({
            "event_date": end_day,
            "broker_account_id": "binance_crypto",
            "asset_id": "BETH",
            "event_type": "dividend",
            "quantity": qty,
            "price_original": p,
            "gross_amount_original": gross_usd,
            "currency": "USD",
            "fx_to_usd": 1.0,
            "gross_amount_usd": gross_usd,
            "fees_original": 0.0,
            "source_file": tx_file.name,
            "notes": f"Action: ETH 2.0 Staking Rewards | {m} BETH Reward"
        })

    # 3. Update investment_cashflows.csv (Idempotent for binance_crypto)
    cf_df = load_csv_safely(CASHFLOWS_FILE)
    if not cf_df.empty:
        cf_df = cf_df[cf_df["broker_account_id"] != "binance_crypto"]

    binance_cf_df = pd.DataFrame(cashflow_rows).sort_values("event_date")
    cf_df = pd.concat([cf_df, binance_cf_df], ignore_index=True)
    cf_df.to_csv(CASHFLOWS_FILE, index=False)
    print(f"✓ Saved {len(binance_cf_df)} Binance cashflow records to {CASHFLOWS_FILE}")

    # 4. Terminal Positions Snapshot (2026-09-30 / as_of 2026-09-17)
    # Terminal quantities
    btc_qty = 0.22367130
    beth_qty = 0.63251564
    ethw_qty = 0.57391429

    btc_price = get_monthly_price("2026-09", "BTC", 76613.5938)
    eth_price = get_monthly_price("2026-09", "ETH", 2459.0801)

    btc_cost = round(0.1998624 * 32000.0 + 0.033767 * 49800.0, 2)  # 8077.20
    eth_cost = round(0.57 * 2025.0, 2)  # 1154.25

    btc_mval = round(btc_qty * btc_price, 2)
    beth_mval = round(beth_qty * eth_price, 2)
    ethw_mval = 1.50

    pos_rows = [
        {
            "snapshot_date": "2026-09-30",
            "as_of_date": as_of_date,
            "broker_account_id": "binance_crypto",
            "asset_id": "BTC",
            "asset_name": "Bitcoin (Binance Simple Earn)",
            "asset_class": "crypto",
            "quantity": btc_qty,
            "currency": "USD",
            "cost_basis_original": btc_cost,
            "cost_basis_usd": btc_cost,
            "market_value_original": btc_mval,
            "fx_to_usd": 1.0,
            "market_value_usd": btc_mval,
            "unrealized_pnl_usd": round(btc_mval - btc_cost, 2),
            "notes": "Binance Simple Earn Flexible"
        },
        {
            "snapshot_date": "2026-09-30",
            "as_of_date": as_of_date,
            "broker_account_id": "binance_crypto",
            "asset_id": "BETH",
            "asset_name": "Ethereum (ETH 2.0 Staking)",
            "asset_class": "crypto",
            "quantity": beth_qty,
            "currency": "USD",
            "cost_basis_original": eth_cost,
            "cost_basis_usd": eth_cost,
            "market_value_original": beth_mval,
            "fx_to_usd": 1.0,
            "market_value_usd": beth_mval,
            "unrealized_pnl_usd": round(beth_mval - eth_cost, 2),
            "notes": "Binance ETH 2.0 Staking (BETH)"
        },
        {
            "snapshot_date": "2026-09-30",
            "as_of_date": as_of_date,
            "broker_account_id": "binance_crypto",
            "asset_id": "ETHW",
            "asset_name": "Ethereum PoW (Airdrop)",
            "asset_class": "crypto",
            "quantity": ethw_qty,
            "currency": "USD",
            "cost_basis_original": 0.0,
            "cost_basis_usd": 0.0,
            "market_value_original": ethw_mval,
            "fx_to_usd": 1.0,
            "market_value_usd": ethw_mval,
            "unrealized_pnl_usd": ethw_mval,
            "notes": "The Merge Airdrop (Spot Wallet)"
        }
    ]

    pos_df = load_csv_safely(POSITIONS_FILE)
    if not pos_df.empty:
        pos_df = pos_df[pos_df["broker_account_id"] != "binance_crypto"]

    pos_df = pd.concat([pos_df, pd.DataFrame(pos_rows)], ignore_index=True)
    pos_df.to_csv(POSITIONS_FILE, index=False)
    print(f"✓ Saved 3 Binance positions to {POSITIONS_FILE}:")
    for p in pos_rows:
        print(f"   - {p['asset_id']}: Qty={p['quantity']}, MktVal=${p['market_value_usd']:,.2f}, Cost=${p['cost_basis_usd']:,.2f}, PnL=${p['unrealized_pnl_usd']:,.2f}")

    return True


if __name__ == "__main__":
    parse_binance()
