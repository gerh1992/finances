"""Data loader for the Financial Dashboard, reading canonical CSV files from data/normalized/."""
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import streamlit as st


def get_data_dir() -> Path:
    """Resolve the directory containing data/normalized/ deterministically."""
    # Try relative to this file: ../../../data/normalized
    module_path = Path(__file__).resolve()
    candidate = module_path.parents[2] / "data" / "normalized"
    if candidate.exists():
        return candidate

    # Try relative to cwd
    cwd = Path.cwd()
    if (cwd / "data" / "normalized").exists():
        return cwd / "data" / "normalized"
    if (cwd / "finances" / "data" / "normalized").exists():
        return cwd / "finances" / "data" / "normalized"

    return candidate


@st.cache_data(ttl=5)
def load_all_data() -> Dict[str, pd.DataFrame]:
    """
    Loads all normalized financial CSV datasets.
    Returns a dictionary of DataFrames.
    """
    data_dir = get_data_dir()

    data: Dict[str, pd.DataFrame] = {}

    def _read_csv(filename: str) -> pd.DataFrame:
        file_path = data_dir / filename
        if file_path.exists():
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                st.error(f"Error loading {filename}: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    data["positions"] = _read_csv("investment_positions.csv")
    data["cashflows"] = _read_csv("investment_cashflows.csv")
    data["balances"] = _read_csv("account_balances.csv")
    data["accounts"] = _read_csv("accounts.csv")
    data["monthly_expenses"] = _read_csv("monthly_expense_summary.csv")
    data["transactions"] = _read_csv("transactions_normalized.csv")
    data["fx_rates"] = _read_csv("fx_rates.csv")
    data["historical_valuations"] = _read_csv("historical_portfolio_valuations.csv")
    data["historical_prices"] = _read_csv("historical_prices.csv")

    # Parse dates
    if not data["cashflows"].empty and "event_date" in data["cashflows"].columns:
        data["cashflows"]["event_date"] = pd.to_datetime(data["cashflows"]["event_date"])

    if not data["transactions"].empty and "txn_date" in data["transactions"].columns:
        data["transactions"]["txn_date"] = pd.to_datetime(data["transactions"]["txn_date"])

    if not data["historical_valuations"].empty and "date" in data["historical_valuations"].columns:
        data["historical_valuations"]["date"] = pd.to_datetime(data["historical_valuations"]["date"])

    return data

