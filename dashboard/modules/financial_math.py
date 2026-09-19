"""Financial calculations and quantitative algorithms for the dashboard."""
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np



ASSET_CLASS_MAPPING = {
    "SCHB": "Renta Variable EE.UU. (Broad Market)",
    "SPY": "Renta Variable EE.UU. (Large Cap)",
    "SCHF": "Renta Variable Internacional (Desarrollados)",
    "XLE": "Sectorial Renta Variable (Energía)",
    "SCHZ": "Renta Fija / Bonos EE.UU.",
    "ADCGLOA": "Fondo Común de Inversión (Dólar)",
    "GOOGL": "Renta Variable EE.UU. (CEDEAR Tech)",
    "AAPL": "Renta Variable EE.UU. (CEDEAR Tech)",
    "XBI": "Sectorial Biotecnología (CEDEAR)",
    "AL30": "Renta Fija / Bonos Soberanos AR",
    "AL30D": "Renta Fija / Bonos Soberanos AR",
    "AL30C": "Renta Fija / Bonos Soberanos AR",
    "BTC": "Criptomonedas (Bitcoin)",
    "ETH": "Criptomonedas (Ethereum)",
    "BETH": "Criptomonedas (Ethereum Staking)",
    "ETHW": "Criptomonedas (Airdrops)",
    "SXT": "Criptomonedas (Airdrops)",
}

BROAD_CLASS_MAPPING = {
    "SCHB": "Renta Variable EE.UU.",
    "SPY": "Renta Variable EE.UU.",
    "SCHF": "Renta Variable Internacional",
    "XLE": "Sectorial Energía",
    "SCHZ": "Renta Fija / Bonos EE.UU.",
    "ADCGLOA": "Renta Fija / Fondos USD",
    "GOOGL": "Renta Variable EE.UU.",
    "AAPL": "Renta Variable EE.UU.",
    "XBI": "Sectorial Biotecnología",
    "AL30": "Renta Fija / Bonos",
    "AL30D": "Renta Fija / Bonos",
    "AL30C": "Renta Fija / Bonos",
    "BTC": "Criptomonedas",
    "ETH": "Criptomonedas",
    "BETH": "Criptomonedas",
    "ETHW": "Criptomonedas",
    "SXT": "Criptomonedas",
}

ASSET_FULL_NAMES = {
    "SCHB": "Schwab U.S. Broad Market ETF",
    "SPY": "SPDR S&P 500 ETF Trust",
    "SCHF": "Schwab International Equity ETF",
    "XLE": "Energy Select Sector SPDR ETF",
    "SCHZ": "Schwab U.S. Aggregate Bond ETF",
    "ADCGLOA": "Adcap Renta Dólar FCI",
    "GOOGL": "Alphabet Inc. Cl. A (CEDEAR)",
    "AAPL": "Apple Inc. (CEDEAR)",
    "XBI": "SPDR S&P Biotech ETF",
    "AL30": "Bono Rep. Argentina USD 2030 (Pesos)",
    "AL30D": "Bono Rep. Argentina USD 2030 (MEP)",
    "AL30C": "Bono Rep. Argentina USD 2030 (Cable)",
    "BTC": "Bitcoin (BTC)",
    "ETH": "Ethereum (ETH)",
    "BETH": "Binance Beacon ETH (Staked ETH)",
    "ETHW": "Ethereum PoW (Airdrop)",
    "SXT": "Space and Time (Airdrop)",
}


def calculate_holdings_metrics(positions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes holding-level financial metrics:
    - AvgCost_i = cost_basis_usd_i / quantity_i
    - MarketPrice_i = market_value_usd_i / quantity_i
    - UnrealizedPnL%_i = ((market_value_usd_i - cost_basis_usd_i) / cost_basis_usd_i) * 100
    - Weight%_i = (market_value_usd_i / sum(market_value_usd_j)) * 100
    """
    if positions_df.empty:
        return pd.DataFrame()

    df = positions_df.copy()
    total_val = df["market_value_usd"].sum()

    cost_col = "cost_basis_usd" if "cost_basis_usd" in df.columns else "cost_basis_original"
    df["avg_cost"] = df[cost_col] / df["quantity"]
    df["market_price"] = df["market_value_usd"] / df["quantity"]
    df["unrealized_pnl_pct"] = (
        (df["market_value_usd"] - df[cost_col]) / df[cost_col]
    ) * 100
    df["weight_pct"] = (df["market_value_usd"] / total_val) * 100 if total_val > 0 else 0

    df["detailed_asset_class"] = df["asset_id"].map(ASSET_CLASS_MAPPING).fillna("Otros")
    df["broad_asset_class"] = df["asset_id"].map(BROAD_CLASS_MAPPING).fillna("Otros")
    df["display_name"] = df["asset_id"].map(ASSET_FULL_NAMES).fillna(df["asset_name"])

    return df


def calculate_portfolio_kpis(
    positions_df: pd.DataFrame,
    cashflows_df: pd.DataFrame,
    balances_df: pd.DataFrame,
    broker_account_id: str = None,
) -> Dict[str, Any]:
    """Computes headline KPIs for the investment portfolio (per-broker or consolidated)."""
    cost_col = "cost_basis_usd" if "cost_basis_usd" in positions_df.columns else "cost_basis_original"
    total_market_val = float(positions_df["market_value_usd"].sum()) if not positions_df.empty else 0.0
    total_cost_basis = float(positions_df[cost_col].sum()) if not positions_df.empty else 0.0
    unrealized_pnl_usd = total_market_val - total_cost_basis
    unrealized_pnl_pct = (unrealized_pnl_usd / total_cost_basis * 100) if total_cost_basis > 0 else 0.0

    # Broker cash calculation
    broker_cash = 0.0
    if not balances_df.empty:
        b_df = balances_df.copy()
        if broker_account_id:
            b_df = b_df[b_df["account_id"] == broker_account_id]
        else:
            b_df = b_df[b_df["account_id"].isin(["schwab_broker", "iol_broker"])]
        if not b_df.empty:
            broker_cash = float(b_df["balance_usd"].sum())

    # Dividends & NRA taxes from cashflows
    gross_dividends = 0.0
    nra_tax_fees = 0.0
    net_deposits = 0.0

    if not cashflows_df.empty:
        cf = cashflows_df.copy()
        if broker_account_id:
            cf = cf[cf["broker_account_id"] == broker_account_id]

        div_mask = cf["event_type"] == "dividend"
        gross_dividends = float(cf.loc[div_mask, "gross_amount_usd"].sum())

        fee_mask = (cf["event_type"] == "fee") & (
            cf["notes"].str.contains("NRA Tax", case=False, na=False)
        )
        nra_tax_fees = float(cf.loc[fee_mask, "gross_amount_usd"].sum())

        dep_mask = cf["event_type"] == "deposit"
        with_mask = cf["event_type"] == "withdrawal"
        net_deposits = float(
            cf.loc[dep_mask, "gross_amount_usd"].sum()
            - cf.loc[with_mask, "gross_amount_usd"].sum()
        )

    net_dividends = gross_dividends - nra_tax_fees
    total_net_worth = total_market_val + broker_cash

    return {
        "total_market_value": total_market_val,
        "total_cost_basis": total_cost_basis,
        "unrealized_pnl_usd": unrealized_pnl_usd,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "broker_cash": broker_cash,
        "total_net_worth": total_net_worth,
        "gross_dividends": gross_dividends,
        "nra_tax_fees": nra_tax_fees,
        "net_dividends": net_dividends,
        "net_deposits": net_deposits,
    }


def reconstruct_historical_curve(
    cashflows_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    historical_valuations_df: Optional[pd.DataFrame] = None,
    broker_account_id: Optional[str] = None,
) -> pd.DataFrame:
    """
    Reconstructs the authentic monthly portfolio historical curve:
    - True cumulative net capital contributions (external deposits minus external withdrawals)
    - Real historical market valuation reconstructed from transaction ledger and monthly market closing prices
    - Cost basis and true unrealized capital gains
    - Zero synthetic compounding factors or artificial smoothing
    """
    # 1. If historical valuations DataFrame is passed or available on disk, use it
    if historical_valuations_df is None or historical_valuations_df.empty:
        from pathlib import Path
        data_path = Path(__file__).resolve().parents[2] / "data" / "normalized" / "historical_portfolio_valuations.csv"
        if data_path.exists():
            try:
                historical_valuations_df = pd.read_csv(data_path)
                if "date" in historical_valuations_df.columns:
                    historical_valuations_df["date"] = pd.to_datetime(historical_valuations_df["date"])
            except Exception:
                historical_valuations_df = pd.DataFrame()

    if historical_valuations_df is not None and not historical_valuations_df.empty:
        df = historical_valuations_df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        scope = broker_account_id
        if not scope:
            if not positions_df.empty:
                b_ids = positions_df["broker_account_id"].unique()
                if len(b_ids) == 1:
                    scope = b_ids[0]
                else:
                    scope = "consolidated"
            else:
                scope = "consolidated"

        sub = df[df["broker_account_id"] == scope].copy()
        if sub.empty and scope != "consolidated":
            sub = df[df["broker_account_id"] == "consolidated"].copy()

        if not sub.empty:
            sub = sub.sort_values("date").reset_index(drop=True)
            sub["month_label"] = sub["month"]
            sub["deployed_capital"] = sub["cost_basis"]
            return sub

    # 2. Honest fallback: if historical prices are unavailable, plot real net capital contributions
    if cashflows_df.empty:
        return pd.DataFrame()

    df = cashflows_df.copy()
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["ym"] = df["event_date"].dt.to_period("M")

    min_period = df["ym"].min()
    max_period = pd.Period("2026-09", "M")
    months = pd.period_range(min_period, max_period, freq="M")

    monthly_records = []
    for m in months:
        sub = df[df["ym"] <= m]
        dep = float(sub[sub["event_type"] == "deposit"]["gross_amount_usd"].sum())
        wth = float(sub[sub["event_type"] == "withdrawal"]["gross_amount_usd"].sum())
        net_deposits = dep - wth

        monthly_records.append({
            "date": m.to_timestamp(how="end"),
            "month_label": str(m),
            "net_deposits": round(net_deposits, 2),
            "cost_basis": round(net_deposits, 2),
            "deployed_capital": round(net_deposits, 2),
            "broker_cash": 0.0,
            "holdings_value": round(net_deposits, 2),
            "portfolio_valuation": round(net_deposits, 2),
            "unrealized_gain": 0.0,
        })

    return pd.DataFrame(monthly_records)



def calculate_asset_allocation(positions_df: pd.DataFrame, by_class: bool = False) -> pd.DataFrame:
    """
    Computes asset allocation table for donut chart.
    """
    if positions_df.empty:
        return pd.DataFrame()

    df = calculate_holdings_metrics(positions_df)
    total_val = df["market_value_usd"].sum()

    if by_class:
        alloc = (
            df.groupby("broad_asset_class")
            .agg({"market_value_usd": "sum"})
            .reset_index()
            .rename(columns={"broad_asset_class": "category"})
        )
        alloc["label"] = alloc["category"]
    else:
        alloc = df[["asset_id", "display_name", "market_value_usd"]].copy()
        alloc["category"] = alloc["asset_id"]
        alloc["label"] = alloc["asset_id"] + " (" + alloc["display_name"] + ")"

    alloc["weight_pct"] = (alloc["market_value_usd"] / total_val) * 100
    alloc = alloc.sort_values(by="market_value_usd", ascending=False)
    return alloc


def calculate_dividend_history(cashflows_df: pd.DataFrame, freq: str = "Q") -> pd.DataFrame:
    """
    Groups dividends, NRA tax (30%), and net dividends by Quarter or Year.
    freq: 'Q' for Quarter, 'Y' for Year
    """
    if cashflows_df.empty:
        return pd.DataFrame()

    df = cashflows_df.copy()
    df["event_date"] = pd.to_datetime(df["event_date"])

    if freq == "Y":
        df["period"] = df["event_date"].dt.year.astype(str)
    else:
        df["period"] = df["event_date"].dt.to_period("Q").astype(str)

    # Filter dividend events
    div_df = df[df["event_type"] == "dividend"]
    gross_by_period = div_df.groupby("period")["gross_amount_usd"].sum()

    # NRA tax fees (only those tied to dividends/investments)
    tax_df = df[
        (df["event_type"] == "fee") &
        (df["notes"].str.contains("NRA Tax", case=False, na=False)) &
        (df["asset_id"] != "-")  # omit bank interest tax if we want pure ETF dividends, or include all
    ]
    # If we include all NRA tax
    all_tax_df = df[(df["event_type"] == "fee") & (df["notes"].str.contains("NRA Tax", case=False, na=False))]
    tax_by_period = all_tax_df.groupby("period")["gross_amount_usd"].sum()

    periods = sorted(list(set(gross_by_period.index).union(set(tax_by_period.index))))

    res = []
    for p in periods:
        g = float(gross_by_period.get(p, 0.0))
        t = float(tax_by_period.get(p, 0.0))
        res.append({
            "period": p,
            "gross_dividend": round(g, 2),
            "nra_tax": round(t, 2),
            "net_dividend": round(max(0.0, g - t), 2),
        })

    return pd.DataFrame(res)


def calculate_liquidity_tiers(
    balances_df: pd.DataFrame,
    positions_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Computes immediate, short-term, and invested liquidity tiers."""
    imm = 0.0
    st = 0.0
    inv = 0.0

    if not balances_df.empty and "liquidity_tier" in balances_df.columns:
        imm = float(balances_df[balances_df["liquidity_tier"] == "immediate"]["balance_usd"].sum())
        st = float(balances_df[balances_df["liquidity_tier"] == "short_term"]["balance_usd"].sum())
        inv = float(balances_df[balances_df["liquidity_tier"] == "invested"]["balance_usd"].sum())

    # Add investment positions to invested tier
    if not positions_df.empty and "market_value_usd" in positions_df.columns:
        inv += float(positions_df["market_value_usd"].sum())

    total_net = imm + st + inv
    return {
        "immediate": imm,
        "short_term": st,
        "invested": inv,
        "total": total_net,
    }
