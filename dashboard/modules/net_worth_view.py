"""Módulo de Patrimonio Neto Consolidado para el Financial Dashboard."""
from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.formatting import format_currency, format_percent
from utils.ui_components import render_kpi_card
from modules.financial_math import calculate_portfolio_kpis, calculate_liquidity_tiers


def render_net_worth_view(data: Dict[str, pd.DataFrame], privacy_mode: bool = False):
    """Renders the consolidated Net Worth module."""
    st.markdown("### 🏛️ Patrimonio Neto Consolidado")

    positions_df = data.get("positions", pd.DataFrame())
    cashflows_df = data.get("cashflows", pd.DataFrame())
    balances_df = data.get("balances", pd.DataFrame())

    kpis = calculate_portfolio_kpis(positions_df, cashflows_df, balances_df)
    tiers = calculate_liquidity_tiers(balances_df, positions_df)

    total_assets = tiers["total"]
    total_liabilities = 0.0
    if not balances_df.empty and "balance_usd" in balances_df.columns:
        neg_mask = balances_df["balance_usd"] < 0
        if neg_mask.any():
            total_liabilities = float(abs(balances_df.loc[neg_mask, "balance_usd"].sum()))

    net_worth = total_assets - total_liabilities

    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi_card(
            title="Patrimonio Neto Total",
            value=format_currency(net_worth, privacy_mode=privacy_mode),
            subtitle="Activos consolidados menos pasivos",
        )
    with col2:
        render_kpi_card(
            title="Activos Totales",
            value=format_currency(total_assets, privacy_mode=privacy_mode),
            subtitle="Inversiones + Caja + Cuentas",
        )
    with col3:
        render_kpi_card(
            title="Pasivos Totales (Deuda)",
            value=format_currency(total_liabilities, privacy_mode=privacy_mode),
            subtitle=f"Deuda de tarjetas: {format_currency(total_liabilities, privacy_mode=privacy_mode)}",
        )


    st.markdown("---")

    row2_c1, row2_c2 = st.columns([1, 1])

    with row2_c1:
        st.markdown("#### 🥧 Composición del Patrimonio")
        nw_breakdown = pd.DataFrame([
            {"Componente": "Portafolio Inversiones", "Monto": kpis["total_market_value"], "Color": "#38BDF8"},
            {"Componente": "Liquidez Inmediata (Bancos & Efectivo)", "Monto": tiers["immediate"], "Color": "#10B981"},
            {"Componente": "Liquidez Corto Plazo (Plataformas)", "Monto": tiers["short_term"], "Color": "#F59E0B"},
            {"Componente": "Caja en Brokers", "Monto": kpis["broker_cash"], "Color": "#818CF8"},
        ])
        # Filter out zero components
        nw_breakdown = nw_breakdown[nw_breakdown["Monto"] > 0]

        fig_nw = go.Figure(
            data=[
                go.Pie(
                    labels=nw_breakdown["Componente"],
                    values=nw_breakdown["Monto"],
                    hole=0.55,
                    marker=dict(colors=nw_breakdown["Color"].tolist(), line=dict(color="#0B0F17", width=2)),
                    textinfo="percent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        + "Valuación: "
                        + ("$ ••••••" if privacy_mode else "$%{value:,.2f} USD")
                        + "<br>Ponderación: %{percent}<extra></extra>"
                    ),
                )
            ]
        )
        fig_nw.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=290,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_nw, use_container_width=True)

    with row2_c2:
        st.markdown("#### 📋 Balance Consolidado")
        bs_items = [
            {"Categoría": "Activo", "Ítem": "Portafolio Inversión (ETFs, CEDEARs, Cripto)", "Valuación USD": kpis["total_market_value"]},
            {"Categoría": "Activo", "Ítem": "Liquidez Inmediata (Bancos, Billeteras, Efectivo)", "Valuación USD": tiers["immediate"]},
            {"Categoría": "Activo", "Ítem": "Liquidez Corto Plazo (Deel, Payoneer)", "Valuación USD": tiers["short_term"]},
            {"Categoría": "Activo", "Ítem": "Caja no invertida en Brokers", "Valuación USD": kpis["broker_cash"]},
            {"Categoría": "Pasivo", "Ítem": "Deuda de tarjetas / Préstamos", "Valuación USD": total_liabilities},
        ]
        df_bs = pd.DataFrame(bs_items)
        df_bs["Valuación USD"] = df_bs["Valuación USD"].apply(
            lambda v: format_currency(v, privacy_mode=privacy_mode)
        )
        st.dataframe(df_bs, use_container_width=True, hide_index=True)

