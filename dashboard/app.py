"""
Personal Finance & Investment Portal
Entrypoint principal de la aplicación Streamlit.
Fase 1: Módulo de Inversiones (Charles Schwab) 100% operativo.
"""
import sys
from pathlib import Path

# Ensure dashboard directory is in sys.path
dashboard_dir = Path(__file__).resolve().parent
if str(dashboard_dir) not in sys.path:
    sys.path.insert(0, str(dashboard_dir))

import streamlit as st
import pandas as pd

from utils.ui_components import inject_custom_css
from utils.formatting import format_currency, format_percent
from modules.data_loader import load_all_data
from modules.financial_math import calculate_portfolio_kpis
from modules.investments_view import render_investments_view
from modules.liquidity_view import render_liquidity_view
from modules.expenses_view import render_expenses_view
from modules.net_worth_view import render_net_worth_view


def main():
    st.set_page_config(
        page_title="Personal Finance & Investment Portal",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Inject visual styling
    inject_custom_css()

    # Initialize session state for privacy mode
    if "privacy_mode" not in st.session_state:
        st.session_state["privacy_mode"] = False

    # Load canonical data from data/normalized/
    data = load_all_data()

    # Pre-calculate global KPIs
    positions_df = data.get("positions", pd.DataFrame())
    cashflows_df = data.get("cashflows", pd.DataFrame())
    balances_df = data.get("balances", pd.DataFrame())
    kpis = calculate_portfolio_kpis(positions_df, cashflows_df, balances_df)

    # Determine As Of Date from positions or default
    as_of_date = "September 16, 2026"
    if not positions_df.empty and "as_of_date" in positions_df.columns:
        date_val = str(positions_df["as_of_date"].iloc[0])
        as_of_date = pd.to_datetime(date_val).strftime("%B %d, %Y")

    # ==========================================
    # Global Header
    # ==========================================
    head_left, head_center, head_right = st.columns([4, 3, 3])

    with head_left:
        st.markdown(
            f"""
            <div>
                <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; background: linear-gradient(90deg, #F8FAFC, #38BDF8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    💼 Personal Finance & Investment Portal
                </h1>
                <div style="color: #94A3B8; font-size: 0.88rem; margin-top: 4px;">
                    Corte de datos: <b>{as_of_date}</b> &nbsp;|&nbsp;
                    <span class="badge-audited">✓ Source: data/normalized (Audited)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with head_center:
        nw_disp = format_currency(kpis["total_net_worth"], privacy_mode=st.session_state["privacy_mode"])
        ret_disp = format_percent(kpis["unrealized_pnl_pct"], privacy_mode=st.session_state["privacy_mode"])
        delta_color = "#10B981" if kpis["unrealized_pnl_usd"] >= 0 else "#EF4444"
        arrow = "▲" if kpis["unrealized_pnl_usd"] >= 0 else "▼"

        st.markdown(
            f"""
            <div style="text-align: right; padding-right: 15px;">
                <div style="color: #94A3B8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em;">
                    Patrimonio Neto Consolidado
                </div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; line-height: 1.2;">
                    {nw_disp}
                </div>
                <div style="color: {delta_color}; font-size: 0.85rem; font-weight: 600;">
                    {arrow} {ret_disp} retorno global
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with head_right:
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.5, 1.2, 1])
        with ctrl_col1:
            privacy_toggle = st.toggle(
                "🔒 Modo Privacidad",
                value=st.session_state["privacy_mode"],
                help="Enmascara todos los importes monetarios como $ •••••• para capturas o presentaciones.",
            )
            if privacy_toggle != st.session_state["privacy_mode"]:
                st.session_state["privacy_mode"] = privacy_toggle
                st.rerun()

        with ctrl_col2:
            st.markdown(
                """
                <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 6px 12px; text-align: center; margin-top: 4px;" title="Moneda base de consolidación">
                    <span style="color: #94A3B8; font-size: 0.75rem;">Moneda Base</span><br>
                    <b style="color: #38BDF8; font-size: 0.9rem;">USD ($)</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with ctrl_col3:
            if st.button("🔄", help="Recargar datos desde data/normalized/"):
                st.cache_data.clear()
                st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ==========================================
    # Navigation Tabs
    # ==========================================
    tab_inv, tab_liq, tab_exp, tab_nw = st.tabs([
        "📈 Inversiones (Schwab)",
        "💧 Liquidez & Cuentas",
        "💸 Gastos & Flujo",
        "🏛️ Patrimonio Neto",
    ])

    with tab_inv:
        render_investments_view(data, privacy_mode=st.session_state["privacy_mode"])

    with tab_liq:
        render_liquidity_view(data, privacy_mode=st.session_state["privacy_mode"])

    with tab_exp:
        render_expenses_view(data, privacy_mode=st.session_state["privacy_mode"])

    with tab_nw:
        render_net_worth_view(data, privacy_mode=st.session_state["privacy_mode"])


if __name__ == "__main__":
    main()
