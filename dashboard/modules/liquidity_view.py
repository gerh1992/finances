"""Módulo de Liquidez y Cuentas para el Financial Dashboard."""
from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.formatting import format_currency
from utils.ui_components import render_kpi_card
from modules.financial_math import calculate_liquidity_tiers


def render_liquidity_view(data: Dict[str, pd.DataFrame], privacy_mode: bool = False):
    """Renders the liquidity and accounts module."""
    st.markdown("### 💧 Liquidez y Distribución de Cuentas")

    balances_df = data.get("balances", pd.DataFrame())
    accounts_df = data.get("accounts", pd.DataFrame())
    positions_df = data.get("positions", pd.DataFrame())

    tiers = calculate_liquidity_tiers(balances_df, positions_df)

    # Assumed benchmark monthly living expenses for runway calculation
    monthly_fixed_burn = 2500.0  # USD benchmark
    runway_months = (tiers["immediate"] / monthly_fixed_burn) if monthly_fixed_burn > 0 else 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card(
            title="Liquidez Inmediata",
            value=format_currency(tiers["immediate"], privacy_mode=privacy_mode),
            subtitle="Cuentas operativas a la vista",
        )
    with col2:
        render_kpi_card(
            title="Liquidez Corto Plazo",
            value=format_currency(tiers["short_term"], privacy_mode=privacy_mode),
            subtitle="Fondos monetarios y plataformas",
        )
    with col3:
        render_kpi_card(
            title="Capital Invertido",
            value=format_currency(tiers["invested"], privacy_mode=privacy_mode),
            subtitle="Portafolio bursátil (Schwab)",
        )
    with col4:
        render_kpi_card(
            title="Runway Estimado",
            value=f"{runway_months:.1f} meses" if not privacy_mode else "•• meses",
            subtitle=f"Basado en {format_currency(monthly_fixed_burn, privacy_mode=privacy_mode)}/mes fijo",
        )

    st.markdown("---")

    # Tier breakdown chart
    row2_c1, row2_c2 = st.columns([1, 1])

    with row2_c1:
        st.markdown("#### 🎯 Distribución por Tiers de Liquidez")
        tier_data = pd.DataFrame([
            {"Tier": "Inmediata (Día a día)", "Monto": tiers["immediate"], "Color": "#10B981"},
            {"Tier": "Corto Plazo", "Monto": tiers["short_term"], "Color": "#38BDF8"},
            {"Tier": "Invertida (Largo Plazo)", "Monto": tiers["invested"], "Color": "#818CF8"},
        ])
        fig_tiers = go.Figure(
            data=[
                go.Pie(
                    labels=tier_data["Tier"],
                    values=tier_data["Monto"],
                    hole=0.6,
                    marker=dict(colors=tier_data["Color"].tolist(), line=dict(color="#0B0F17", width=2)),
                    textinfo="percent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        + "Monto: "
                        + ("$ ••••••" if privacy_mode else "$%{value:,.2f} USD")
                        + "<br>Porcentaje: %{percent}<extra></extra>"
                    ),
                )
            ]
        )
        fig_tiers.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_tiers, use_container_width=True)

    with row2_c2:
        st.markdown("#### 🏦 Catálogo de Cuentas del Sistema")
        if not accounts_df.empty:
            acc_summary = accounts_df[["account_name", "institution", "country", "account_type", "default_currency"]].copy()
            acc_summary.columns = ["Cuenta", "Institución", "País", "Tipo", "Moneda"]
            st.dataframe(acc_summary, use_container_width=True, hide_index=True)
        else:
            st.info("Sin cuentas registradas en `accounts.csv`.")

    st.markdown("---")
    st.markdown("#### 💳 Saldos Registrados por Cuenta")
    if not balances_df.empty:
        disp_bal = balances_df[["account_id", "currency", "balance_original", "balance_usd", "liquidity_tier", "notes"]].copy()
        disp_bal["balance_original"] = disp_bal.apply(
            lambda r: format_currency(r["balance_original"], currency=r["currency"], privacy_mode=privacy_mode),
            axis=1,
        )
        disp_bal["balance_usd"] = disp_bal["balance_usd"].apply(
            lambda v: format_currency(v, privacy_mode=privacy_mode)
        )
        disp_bal.columns = ["Cuenta ID", "Moneda", "Saldo Original", "Saldo USD", "Tier Liquidez", "Detalle"]
        st.dataframe(disp_bal, use_container_width=True, hide_index=True)
    else:
        st.info("Sin saldos registrados en `account_balances.csv`.")
