"""
Audit and test script for the financial dashboard metrics and integrity.
"""
import sys
from pathlib import Path
import pandas as pd

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
    hist_val = data.get("historical_valuations", pd.DataFrame())
    hist_prices = data.get("historical_prices", pd.DataFrame())

    assert not positions.empty, "Positions dataframe is empty!"
    assert not cashflows.empty, "Cashflows dataframe is empty!"
    assert not hist_val.empty, "Historical valuations dataframe is empty!"
    assert not hist_prices.empty, "Historical prices dataframe is empty!"
    assert len(cashflows) == 806, f"Expected 806 cashflow transactions, got {len(cashflows)}"
    schwab_cf = cashflows[cashflows["broker_account_id"] == "schwab_broker"]
    assert len(schwab_cf) == 340, f"Expected 340 Schwab cashflows, got {len(schwab_cf)}"
    binance_cf = cashflows[cashflows["broker_account_id"] == "binance_crypto"]
    assert len(binance_cf) == 139, f"Expected 139 Binance cashflows, got {len(binance_cf)}"
    print(f"✓ Cashflows count: {len(cashflows)} transactions (340 Schwab + 327 IOL + 139 Binance)")

    # 2. Check Schwab KPIs
    schwab_pos = positions[positions["broker_account_id"] == "schwab_broker"]
    kpis = calculate_portfolio_kpis(schwab_pos, schwab_cf, balances, broker_account_id="schwab_broker")
    print(f"✓ Schwab Market Value: ${kpis['total_market_value']:,.2f} USD (Expected: $169,711.91 USD)")
    assert round(kpis["total_market_value"], 2) == 169711.91, f"Market value mismatch: got {kpis['total_market_value']}"

    print(f"✓ Schwab Cost Basis: ${kpis['total_cost_basis']:,.2f} USD (Expected: $123,953.42 USD)")
    assert round(kpis["total_cost_basis"], 2) == 123953.42, f"Cost basis mismatch: got {kpis['total_cost_basis']}"

    print(f"✓ Schwab Unrealized PnL: ${kpis['unrealized_pnl_usd']:,.2f} USD (Expected: $45,758.49 USD)")
    assert round(kpis["unrealized_pnl_usd"], 2) == 45758.49, f"Unrealized PnL mismatch: got {kpis['unrealized_pnl_usd']}"

    print(f"✓ Schwab Unrealized PnL %: {kpis['unrealized_pnl_pct']:.2f}% (Expected: +36.92%)")
    assert round(kpis["unrealized_pnl_pct"], 2) == 36.92, f"Unrealized PnL % mismatch: got {kpis['unrealized_pnl_pct']}"

    print(f"✓ Schwab Broker Cash: ${kpis['broker_cash']:,.2f} USD (Expected: $175.80 USD)")
    assert round(kpis["broker_cash"], 2) == 175.80, "Broker cash mismatch"

    print(f"✓ Schwab Net Worth: ${kpis['total_net_worth']:,.2f} USD (Expected: $169,887.71 USD)")
    assert round(kpis["total_net_worth"], 2) == 169887.71, f"Total net worth mismatch: got {kpis['total_net_worth']}"

    # 3. Check Binance KPIs
    binance_pos = positions[positions["broker_account_id"] == "binance_crypto"]
    b_kpis = calculate_portfolio_kpis(binance_pos, binance_cf, balances, broker_account_id="binance_crypto")
    print(f"✓ Binance Market Value: ${b_kpis['total_market_value']:,.2f} USD (Expected: $18,685.78 USD)")
    assert round(b_kpis["total_market_value"], 2) == 18685.78, f"Binance market value mismatch: got {b_kpis['total_market_value']}"

    print(f"✓ Binance Cost Basis: ${b_kpis['total_cost_basis']:,.2f} USD (Expected: $9,231.44 USD)")
    assert round(b_kpis["total_cost_basis"], 2) == 9231.44, f"Binance cost basis mismatch: got {b_kpis['total_cost_basis']}"

    print(f"✓ Binance Unrealized PnL: ${b_kpis['unrealized_pnl_usd']:,.2f} USD (Expected: $9,454.34 USD)")
    assert round(b_kpis["unrealized_pnl_usd"], 2) == 9454.34, f"Binance Unrealized PnL mismatch: got {b_kpis['unrealized_pnl_usd']}"

    print(f"✓ Binance Unrealized PnL %: {b_kpis['unrealized_pnl_pct']:.2f}% (Expected: +102.41%)")
    assert round(b_kpis["unrealized_pnl_pct"], 2) == 102.41, f"Binance Unrealized PnL % mismatch: got {b_kpis['unrealized_pnl_pct']}"

    # Check Multi-currency Cost Basis (cost_basis_usd vs cost_basis_original)
    assert "cost_basis_usd" in positions.columns, "Missing cost_basis_usd column in investment_positions.csv"
    
    # Schwab: cost_basis_usd == cost_basis_original
    for _, r in schwab_pos.iterrows():
        assert r["cost_basis_usd"] == r["cost_basis_original"], f"Schwab {r['asset_id']} cost mismatch"
    
    # IOL positions: check currency separation
    iol_pos = positions[positions["broker_account_id"] == "iol_broker"].set_index("asset_id")
    assert round(float(iol_pos.loc["GOOGL", "cost_basis_usd"]), 2) == 1514.77, "GOOGL cost_basis_usd mismatch"
    assert round(float(iol_pos.loc["GOOGL", "cost_basis_original"]), 2) == 590782.50, "GOOGL cost_basis_original mismatch (should be in ARS)"
    assert iol_pos.loc["GOOGL", "currency"] == "ARS"

    assert round(float(iol_pos.loc["SPY", "cost_basis_usd"]), 2) == 8493.49, "IOL SPY cost_basis_usd mismatch"
    assert round(float(iol_pos.loc["XLE", "cost_basis_usd"]), 2) == 449.57, "IOL XLE cost_basis_usd mismatch"
    assert round(float(iol_pos.loc["ADCGLOA", "cost_basis_usd"]), 2) == 100.0, "IOL ADCGLOA cost_basis_usd mismatch"

    # Consolidated KPIs cost basis check
    cons_kpis = calculate_portfolio_kpis(positions, cashflows, balances)
    expected_cons_cost = 123953.42 + 1514.77 + 8493.49 + 449.57 + 100.00 + 9231.44  # 143,742.69
    print(f"✓ Consolidated Cost Basis: ${cons_kpis['total_cost_basis']:,.2f} USD (Expected: ${expected_cons_cost:,.2f} USD)")
    assert round(cons_kpis["total_cost_basis"], 2) == round(expected_cons_cost, 2), "Consolidated cost basis mismatch"


    # 4. Check real historical curve
    curve_schwab = reconstruct_historical_curve(schwab_cf, schwab_pos, hist_val, broker_account_id="schwab_broker")
    assert not curve_schwab.empty, "Schwab historical curve is empty"
    initial_net_deposits = curve_schwab.iloc[0]["net_deposits"]
    ending_val = curve_schwab.iloc[-1]["portfolio_valuation"]
    print(f"✓ Schwab Historical curve start (2023-03): ${initial_net_deposits:,.2f} USD net deposits (Expected: $50,000.00)")
    assert initial_net_deposits == 50000.0, "Initial deposits mismatch"
    print(f"✓ Schwab Historical curve end (2026-09): ${ending_val:,.2f} USD valuation (Expected: $169,887.71)")
    assert ending_val == 169887.71, f"Ending valuation mismatch: got {ending_val}"

    # Consolidated historical curve
    curve_cons = reconstruct_historical_curve(cashflows, positions, hist_val, broker_account_id="consolidated")
    assert not curve_cons.empty, "Consolidated historical curve is empty"
    ending_cons = curve_cons.iloc[-1]["portfolio_valuation"]
    print(f"✓ Consolidated Historical curve end (2026-09): ${ending_cons:,.2f} USD (Expected: $200,266.42)")
    assert ending_cons == 200266.42, f"Ending consolidated mismatch: got {ending_cons}"

    # 4. Check dividends and NRA tax
    div_q = calculate_dividend_history(schwab_cf, freq="Q")
    total_gross_div = div_q["gross_dividend"].sum()
    total_nra_tax = div_q["nra_tax"].sum()
    print(f"✓ Schwab gross dividends: ${total_gross_div:,.2f} USD")
    print(f"✓ Schwab NRA tax fees: ${total_nra_tax:,.2f} USD")
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

    # 7. Check Liquidity Tiers & Consolidated 360 Net Worth
    from modules.financial_math import calculate_liquidity_tiers
    tiers = calculate_liquidity_tiers(balances, positions)
    print(f"✓ Immediate Liquidity: ${tiers['immediate']:,.2f} USD (Expected: $639,794.34 USD)")
    assert round(tiers["immediate"], 2) == 639794.34, f"Immediate liquidity mismatch: {tiers['immediate']}"

    print(f"✓ Short-Term Liquidity: ${tiers['short_term']:,.2f} USD (Expected: $94,300.00 USD)")
    assert round(tiers["short_term"], 2) == 94300.00, f"Short term liquidity mismatch: {tiers['short_term']}"

    print(f"✓ Invested Assets: ${tiers['invested']:,.2f} USD (Expected: $200,266.42 USD)")
    assert round(tiers["invested"], 2) == 200266.42, f"Invested mismatch: {tiers['invested']}"

    expected_total_nw = 639794.34 + 94300.00 + 200266.42
    print(f"✓ Total Consolidated Net Worth: ${tiers['total']:,.2f} USD (Expected: ${expected_total_nw:,.2f} USD)")
    assert round(tiers["total"], 2) == round(expected_total_nw, 2), f"Total net worth mismatch: {tiers['total']}"

    print("\nALL AUDIT CHECKS PASSED WITH 100% SUCCESS!")


if __name__ == "__main__":
    run_audit()


