"""
Audit and test script for the financial dashboard metrics and integrity.
"""
import sys
from pathlib import Path

# Add dashboard to sys.path
dash_dir = Path(__file__).resolve().parent
if str(dash_dir) not in sys.path:
    sys.path.insert(0, str(dash_dir))

from modules.data_loader import load_all_data
from modules.financial_math import (
    calculate_holdings_metrics,
    calculate_portfolio_kpis,
    reconstruct_historical_curve,
    calculate_asset_allocation,
    calculate_dividend_history,
)
from utils.formatting import format_currency, format_percent, format_number


def run_audit():
    print("=== FINANCIAL DASHBOARD AUDIT & VERIFICATION ===")
    data = load_all_data()

    # 1. Check data loading
    positions = data["positions"]
    cashflows = data["cashflows"]
    balances = data["balances"]
    accounts = data["accounts"]

    assert not positions.empty, "Positions dataframe is empty!"
    assert not cashflows.empty, "Cashflows dataframe is empty!"
    assert len(cashflows) == 337, f"Expected 337 cashflow transactions, got {len(cashflows)}"
    print(f"✓ Cashflows count: {len(cashflows)} transactions (exact match)")

    # 2. Check KPIs
    kpis = calculate_portfolio_kpis(positions, cashflows, balances)
    print(f"✓ Market Value: ${kpis['total_market_value']:,.2f} USD (Expected: $164,598.90 USD)")
    assert round(kpis["total_market_value"], 2) == 164598.90, "Market value mismatch"

    print(f"✓ Cost Basis: ${kpis['total_cost_basis']:,.2f} USD (Expected: $118,953.42 USD)")
    assert round(kpis["total_cost_basis"], 2) == 118953.42, "Cost basis mismatch"

    print(f"✓ Unrealized PnL: ${kpis['unrealized_pnl_usd']:,.2f} USD (Expected: $45,645.48 USD)")
    assert round(kpis["unrealized_pnl_usd"], 2) == 45645.48, "Unrealized PnL mismatch"

    print(f"✓ Unrealized PnL %: {kpis['unrealized_pnl_pct']:.2f}% (Expected: +38.37%)")
    assert round(kpis["unrealized_pnl_pct"], 2) == 38.37, "Unrealized PnL % mismatch"

    print(f"✓ Broker Cash: ${kpis['broker_cash']:,.2f} USD (Expected: $175.80 USD)")
    assert round(kpis["broker_cash"], 2) == 175.80, "Broker cash mismatch"

    print(f"✓ Net Worth: ${kpis['total_net_worth']:,.2f} USD (Expected: $164,774.70 USD)")
    assert round(kpis["total_net_worth"], 2) == 164774.70, "Total net worth mismatch"

    # 3. Check historical curve
    curve = reconstruct_historical_curve(cashflows, positions)
    assert not curve.empty, "Historical curve is empty"
    initial_net_deposits = curve.iloc[0]["net_deposits"]
    ending_val = curve.iloc[-1]["portfolio_valuation"]
    print(f"✓ Historical curve start (2023-03): ${initial_net_deposits:,.2f} USD net deposits (Expected: $50,000.00)")
    assert initial_net_deposits == 50000.0, "Initial deposits mismatch"
    print(f"✓ Historical curve end (2026-09): ${ending_val:,.2f} USD valuation (Expected: $164,598.90)")
    assert ending_val == 164598.90, "Ending valuation mismatch"

    # 4. Check dividends and NRA tax
    div_q = calculate_dividend_history(cashflows, freq="Q")
    total_gross_div = div_q["gross_dividend"].sum()
    total_nra_tax = div_q["nra_tax"].sum()
    print(f"✓ Total gross dividends: ${total_gross_div:,.2f} USD")
    print(f"✓ Total NRA tax fees: ${total_nra_tax:,.2f} USD")
    assert round(total_gross_div, 2) == 6581.78, "Gross dividends mismatch"
    assert round(total_nra_tax, 2) == 1975.18, "NRA tax fees mismatch"

    # 5. Check Asset Allocation
    alloc = calculate_asset_allocation(positions, by_class=False)
    total_weight = alloc["weight_pct"].sum()
    print(f"✓ Total Asset Allocation weight sum: {total_weight:.2f}% (Expected: 100%)")
    assert round(total_weight, 2) == 100.0, "Asset allocation sum mismatch"

    # 6. Check Privacy Mode
    masked_curr = format_currency(164598.90, privacy_mode=True)
    unmasked_curr = format_currency(164598.90, privacy_mode=False)
    assert masked_curr == "$ ••••••", f"Privacy mode failed: {masked_curr}"
    assert "$164,598.90 USD" in unmasked_curr, f"Unmasked currency failed: {unmasked_curr}"
    print(f"✓ Privacy mode formatting verified: {masked_curr}")

    print("\nALL AUDIT CHECKS PASSED WITH 100% SUCCESS!")


if __name__ == "__main__":
    run_audit()
