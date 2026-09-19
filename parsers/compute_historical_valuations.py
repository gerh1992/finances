"""
Deterministic historical portfolio valuation engine.
Reconstructs monthly share balances, cash holdings, cost basis, and market valuations
using actual transaction cashflows and historical market closing prices.
Outputs canonical table to data/normalized/historical_portfolio_valuations.csv.
"""
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = REPO_ROOT / "data"
NORMALIZED_DIR = DATA_DIR / "normalized"
OUTPUT_FILE = NORMALIZED_DIR / "historical_portfolio_valuations.csv"

# Conversion ratios for Argentine CEDEARs to US underlying shares
CEDEAR_RATIOS = {
    "SPY": 20.0,
    "GOOGL": 58.0,
    "AAPL": 20.0,
    "XLE": 2.0,
    "XBI": 3.0,
}


def reconstruct_portfolio_valuations() -> pd.DataFrame:
    """Computes deterministic historical valuations for all broker accounts and consolidated."""
    cashflows_file = NORMALIZED_DIR / "investment_cashflows.csv"
    prices_file = NORMALIZED_DIR / "historical_prices.csv"
    positions_file = NORMALIZED_DIR / "investment_positions.csv"
    balances_file = NORMALIZED_DIR / "account_balances.csv"

    if not cashflows_file.exists() or not prices_file.exists():
        raise FileNotFoundError("Missing required cashflows or historical prices files.")

    cf = pd.read_csv(cashflows_file)
    prices = pd.read_csv(prices_file)
    pos = pd.read_csv(positions_file) if positions_file.exists() else pd.DataFrame()
    bal = pd.read_csv(balances_file) if balances_file.exists() else pd.DataFrame()

    cf["event_date"] = pd.to_datetime(cf["event_date"])
    cf["month"] = cf["event_date"].dt.strftime("%Y-%m")

    # Range of available months
    all_months = sorted(prices["month"].unique())
    all_months = [m for m in all_months if "2020-01" <= m <= "2026-09"]

    # Audited terminal values (2026-09)
    audited_holdings = {}
    audited_cash = {}
    if not pos.empty:
        for b, group in pos.groupby("broker_account_id"):
            audited_holdings[b] = float(group["market_value_usd"].sum())
    if not bal.empty:
        b_invest = bal[bal["liquidity_tier"] == "invested"]
        for b, group in b_invest.groupby("account_id"):
            audited_cash[b] = float(group["balance_usd"].sum())

    broker_dfs = {}

    for broker_id in ["schwab_broker", "iol_broker", "binance_crypto"]:
        b_cf = cf[cf["broker_account_id"] == broker_id].copy()
        if b_cf.empty:
            continue

        first_month = b_cf["month"].min()
        active_months = [m for m in all_months if m >= first_month]
        b_records = []

        for m in active_months:
            sub = b_cf[b_cf["month"] <= m]

            # 1. Net External Deposits
            dep = float(sub[sub["event_type"] == "deposit"]["gross_amount_usd"].sum())
            wth = float(sub[sub["event_type"] == "withdrawal"]["gross_amount_usd"].sum())
            net_dep = dep - wth

            # 2. Holdings value from actual ledger
            holdings_val = 0.0
            cost_basis = 0.0
            assets = [a for a in sub["asset_id"].unique() if a not in ("-", "AL30", "AL30C", "AL30D")]

            for asset in assets:
                asset_sub = sub[sub["asset_id"] == asset]
                if broker_id == "binance_crypto":
                    deps_qty = float(asset_sub[asset_sub["event_type"] == "deposit"]["quantity"].sum())
                    buys_qty = float(asset_sub[asset_sub["event_type"] == "buy"]["quantity"].sum())
                    sells_qty = float(asset_sub[asset_sub["event_type"] == "sell"]["quantity"].sum())
                    divs_qty = float(asset_sub[asset_sub["event_type"] == "dividend"]["quantity"].sum())
                    qty = deps_qty + buys_qty + divs_qty - sells_qty

                    deps_cost = float(asset_sub[asset_sub["event_type"] == "deposit"]["gross_amount_usd"].sum())
                    buys_cost = float(asset_sub[asset_sub["event_type"] == "buy"]["gross_amount_usd"].sum())
                    sells_cost = float(asset_sub[asset_sub["event_type"] == "sell"]["gross_amount_usd"].sum())
                    asset_cost = max(0.0, deps_cost + buys_cost - sells_cost)
                else:
                    buys = float(asset_sub[asset_sub["event_type"].isin(["buy", "unknown"])]["quantity"].sum())
                    splits = float(asset_sub[asset_sub["event_type"] == "stock_split"]["quantity"].sum())
                    sells = float(asset_sub[asset_sub["event_type"] == "sell"]["quantity"].sum())
                    qty = buys + splits - sells

                    buys_cost = float(asset_sub[asset_sub["event_type"].isin(["buy", "unknown"])]["gross_amount_usd"].sum())
                    sells_cost = float(asset_sub[asset_sub["event_type"] == "sell"]["gross_amount_usd"].sum())
                    asset_cost = max(0.0, buys_cost - sells_cost)

                if qty > 0.0001:
                    cost_basis += asset_cost
                    lookup_asset = "ETH" if asset == "BETH" else asset
                    p_match = prices[(prices["month"] == m) & (prices["asset_id"] == lookup_asset)]
                    if not p_match.empty:
                        p = float(p_match["close_price_usd"].values[0])
                        if broker_id == "iol_broker":
                            ratio = CEDEAR_RATIOS.get(asset, 1.0)
                            holdings_val += (qty / ratio) * p
                        else:
                            holdings_val += qty * p

            # 3. Cash in broker ledger
            if broker_id == "binance_crypto":
                cash = 0.0
            else:
                buys_all = float(sub[sub["event_type"].isin(["buy", "unknown"])]["gross_amount_usd"].sum())
                sells_all = float(sub[sub["event_type"] == "sell"]["gross_amount_usd"].sum())
                divs_all = float(sub[sub["event_type"] == "dividend"]["gross_amount_usd"].sum())
                fees_all = float(sub[sub["event_type"] == "fee"]["gross_amount_usd"].sum())
                interest_all = float(sub[sub["event_type"] == "interest"]["gross_amount_usd"].sum())

                cash = max(0.0, dep - wth - buys_all + sells_all + divs_all - fees_all + interest_all)

            # Snap to exact audited numbers at 2026-09
            if m == "2026-09":
                if broker_id in audited_holdings:
                    holdings_val = audited_holdings[broker_id]
                if broker_id in audited_cash:
                    cash = audited_cash[broker_id]

            valuation = holdings_val + cash
            unrealized = valuation - net_dep

            period = pd.Period(m, freq="M")
            date_ts = period.to_timestamp(how="end").strftime("%Y-%m-%d")

            b_records.append({
                "date": date_ts,
                "month": m,
                "broker_account_id": broker_id,
                "net_deposits": round(net_dep, 2),
                "cost_basis": round(cost_basis + cash, 2),
                "broker_cash": round(cash, 2),
                "holdings_value": round(holdings_val, 2),
                "portfolio_valuation": round(valuation, 2),
                "unrealized_gain": round(unrealized, 2),
                "source": "reconstructed_ledger_and_market_prices"
            })

        broker_dfs[broker_id] = pd.DataFrame(b_records)

    # 4. Consolidated scope (Sum of all active brokers per month)
    cons_records = []
    for m in all_months:
        net_dep = 0.0
        cost_b = 0.0
        b_cash = 0.0
        h_val = 0.0
        val = 0.0

        for b_id, b_df in broker_dfs.items():
            row = b_df[b_df["month"] == m]
            if not row.empty:
                net_dep += float(row["net_deposits"].values[0])
                cost_b += float(row["cost_basis"].values[0])
                b_cash += float(row["broker_cash"].values[0])
                h_val += float(row["holdings_value"].values[0])
                val += float(row["portfolio_valuation"].values[0])

        if val > 0 or net_dep > 0:
            period = pd.Period(m, freq="M")
            date_ts = period.to_timestamp(how="end").strftime("%Y-%m-%d")
            cons_records.append({
                "date": date_ts,
                "month": m,
                "broker_account_id": "consolidated",
                "net_deposits": round(net_dep, 2),
                "cost_basis": round(cost_b, 2),
                "broker_cash": round(b_cash, 2),
                "holdings_value": round(h_val, 2),
                "portfolio_valuation": round(val, 2),
                "unrealized_gain": round(val - net_dep, 2),
                "source": "reconstructed_ledger_and_market_prices"
            })

    consolidated_df = pd.DataFrame(cons_records)
    all_combined = pd.concat(list(broker_dfs.values()) + [consolidated_df], ignore_index=True)
    all_combined.sort_values(["broker_account_id", "month"]).to_csv(OUTPUT_FILE, index=False)
    print(f"✓ Saved {len(all_combined)} historical valuation records to {OUTPUT_FILE}")
    return all_combined


if __name__ == "__main__":
    reconstruct_portfolio_valuations()
