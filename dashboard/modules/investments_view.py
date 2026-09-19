"""Módulo de Inversiones (Consolidado, Charles Schwab e Invertir Online) para el Financial Dashboard."""
from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.formatting import format_currency, format_percent, format_number
from utils.ui_components import render_kpi_card
from modules.financial_math import (
    calculate_holdings_metrics,
    calculate_portfolio_kpis,
    reconstruct_historical_curve,
    calculate_asset_allocation,
    calculate_dividend_history,
)

# Custom color palette for assets
ASSET_COLOR_MAP = {
    "SCHB": "#38BDF8",  # Sky blue
    "SCHF": "#818CF8",  # Indigo
    "SPY": "#34D399",   # Emerald green
    "XLE": "#F59E0B",   # Amber / Gold
    "SCHZ": "#A78BFA",  # Violet
    "ADCGLOA": "#EC4899", # Rose / Pink
    "GOOGL": "#06B6D4", # Cyan
    "AAPL": "#94A3B8",  # Slate
    "XBI": "#F97316",   # Orange
    "AL30": "#EAB308",  # Yellow
    "BTC": "#F7931A",   # Bitcoin Orange
    "ETH": "#627EEA",   # Ethereum Blue
    "BETH": "#818CF8",  # Staked ETH
    "ETHW": "#94A3B8",  # Slate
    "SXT": "#10B981",   # Emerald
    "Renta Variable EE.UU.": "#38BDF8",
    "Renta Variable Internacional": "#818CF8",
    "Sectorial Energía": "#F59E0B",
    "Renta Fija / Bonos EE.UU.": "#A78BFA",
    "Renta Fija / Fondos USD": "#EC4899",
    "Sectorial Biotecnología": "#F97316",
    "Renta Fija / Bonos": "#EAB308",
    "Criptomonedas": "#F7931A",
    "Criptomonedas (Bitcoin)": "#F7931A",
    "Criptomonedas (Ethereum)": "#627EEA",
    "Criptomonedas (Ethereum Staking)": "#818CF8",
    "Criptomonedas (Airdrops)": "#94A3B8",
}


def render_investments_view(data: Dict[str, pd.DataFrame], privacy_mode: bool = False):
    """Renders the comprehensive investments module with broker selector and multi-currency awareness."""
    positions_df = data.get("positions", pd.DataFrame())
    cashflows_df = data.get("cashflows", pd.DataFrame())
    balances_df = data.get("balances", pd.DataFrame())

    if positions_df.empty:
        st.warning("No se encontraron posiciones de inversión en `data/normalized/investment_positions.csv`.")
        return

    # Broker Selector Controls
    broker_options = {
        "🌐 Consolidado (Todas las Cuentas)": None,
        "🇺🇸 Charles Schwab (EE.UU.)": "schwab_broker",
        "🇦🇷 Invertir Online (IOL Argentina)": "iol_broker",
        "🟡 Binance (Criptomonedas)": "binance_crypto",
    }

    st.markdown("### 📈 Portafolio de Inversiones")
    selected_label = st.radio(
        "Seleccionar Cuenta / Broker:",
        options=list(broker_options.keys()),
        horizontal=True,
        index=0,
        label_visibility="collapsed",
    )
    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)


    selected_broker_id = broker_options[selected_label]

    # Filter positions, cashflows, and balances
    if selected_broker_id:
        f_positions = positions_df[positions_df["broker_account_id"] == selected_broker_id].copy()
        f_cashflows = cashflows_df[cashflows_df["broker_account_id"] == selected_broker_id].copy()
        f_balances = balances_df[balances_df["account_id"] == selected_broker_id].copy()
    else:
        f_positions = positions_df.copy()
        f_cashflows = cashflows_df.copy()
        f_balances = balances_df[balances_df["account_id"].isin(["schwab_broker", "iol_broker", "binance_crypto"])].copy()

    # Calculate headline KPIs
    kpis = calculate_portfolio_kpis(f_positions, f_cashflows, f_balances, selected_broker_id)

    # Subtitle for cash
    if selected_broker_id == "schwab_broker":
        cash_subtitle = "USD líquido en comitente"
    elif selected_broker_id == "iol_broker":
        cash_subtitle = "USD + ARS líquido (en USD)"
    elif selected_broker_id == "binance_crypto":
        cash_subtitle = "Stablecoins / USDT disponible"
    else:
        cash_subtitle = "Liquidez total en brokers/exchanges"

    # 1. Headline KPI Cards
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        render_kpi_card(
            title="Valuación de Cartera",
            value=format_currency(kpis["total_market_value"], privacy_mode=privacy_mode),
            subtitle=f"Aportes Netos: {format_currency(kpis['net_deposits'], privacy_mode=privacy_mode)}",
        )

    with col2:
        render_kpi_card(
            title="Ganancia No Realizada",
            value=format_currency(kpis["unrealized_pnl_usd"], privacy_mode=privacy_mode, show_sign=True),
            delta=format_percent(kpis["unrealized_pnl_pct"], privacy_mode=privacy_mode),
            is_positive=kpis["unrealized_pnl_usd"] >= 0,
        )

    with col3:
        render_kpi_card(
            title="Dividendos Brutos",
            value=format_currency(kpis["gross_dividends"], privacy_mode=privacy_mode),
            subtitle=f"Neto: {format_currency(kpis['net_dividends'], privacy_mode=privacy_mode)}",
        )

    with col4:
        render_kpi_card(
            title="Retenciones Fiscales",
            value=format_currency(kpis["nra_tax_fees"], privacy_mode=privacy_mode),
            subtitle="Impuesto retenido en origen",
        )

    with col5:
        render_kpi_card(
            title="Caja en Broker",
            value=format_currency(kpis["broker_cash"], privacy_mode=privacy_mode),
            subtitle=cash_subtitle,
        )

    st.markdown("---")

    # 2. Charts Section (Curva Histórica y Asset Allocation)
    row2_col1, row2_col2 = st.columns([3, 2])

    with row2_col1:
        st.markdown(f"#### 📊 Curva Histórica Real: Aportes vs. Valuación ({selected_label})")
        hist_val_df = data.get("historical_valuations", pd.DataFrame())
        curve_df = reconstruct_historical_curve(
            f_cashflows,
            f_positions,
            historical_valuations_df=hist_val_df,
            broker_account_id=selected_broker_id or "consolidated",
        )

        if not curve_df.empty:
            fig_curve = go.Figure()

            # Area: Valuation
            fig_curve.add_trace(
                go.Scatter(
                    x=curve_df["date"],
                    y=curve_df["portfolio_valuation"],
                    customdata=curve_df["unrealized_gain"],
                    name="Valuación Real",
                    mode="lines",
                    line=dict(color="#10B981", width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(16, 185, 129, 0.12)",
                    hovertemplate=(
                        "<b>Fecha:</b> %{x|%b %Y}<br>"
                        "<b>Valuación:</b> "
                        + ("$ ••••••" if privacy_mode else "$%{y:,.2f} USD")
                        + "<br><b>Ganancia No Realizada:</b> "
                        + ("$ ••••••" if privacy_mode else "$%{customdata:,.2f} USD")
                        + "<extra></extra>"
                    ),
                )
            )

            # Line: Net Contributions / Net deposits
            fig_curve.add_trace(
                go.Scatter(
                    x=curve_df["date"],
                    y=curve_df["net_deposits"],
                    name="Aportes Netos Acumulados",
                    mode="lines",
                    line=dict(color="#38BDF8", width=2, dash="dash"),
                    hovertemplate=(
                        "<b>Aportes Netos:</b> "
                        + ("$ ••••••" if privacy_mode else "$%{y:,.2f} USD")
                        + "<extra></extra>"
                    ),
                )
            )


            fig_curve.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                margin=dict(l=20, r=20, t=25, b=20),
                height=340,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=11),
                ),
                xaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255, 255, 255, 0.07)",
                    zeroline=False,
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255, 255, 255, 0.07)",
                    zeroline=False,
                    tickprefix="" if privacy_mode else "$",
                    showticklabels=not privacy_mode,
                ),
            )
            st.plotly_chart(fig_curve, use_container_width=True)
        else:
            st.info("Sin datos históricos suficientes para graficar.")

    with row2_col2:
        st.markdown("#### 🍩 Distribución de Activos")
        alloc_mode = st.radio(
            "Agrupación:",
            options=["Por Activo", "Por Clase de Activo"],
            horizontal=True,
            label_visibility="collapsed",
        )
        by_class = alloc_mode == "Por Clase de Activo"
        alloc_df = calculate_asset_allocation(f_positions, by_class=by_class)

        if not alloc_df.empty:
            colors = [ASSET_COLOR_MAP.get(cat, "#94A3B8") for cat in alloc_df["category"]]

            fig_donut = go.Figure(
                data=[
                    go.Pie(
                        labels=alloc_df["label"],
                        values=alloc_df["market_value_usd"],
                        hole=0.58,
                        marker=dict(colors=colors, line=dict(color="#0B0F17", width=2)),
                        textinfo="percent",
                        textfont=dict(size=12, color="#F8FAFC"),
                        hoverinfo="label+percent+value",
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            + "Porcentaje: %{percent}<br>"
                            + "Valuación: "
                            + ("$ ••••••" if privacy_mode else "$%{value:,.2f} USD")
                            + "<extra></extra>"
                        ),
                    )
                ]
            )
            fig_donut.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=15, b=15),
                height=340,
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    font=dict(size=11),
                ),
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("---")

    # 3. Gráfico 3: Flujo de Dividendos y Retenciones Fiscales
    st.markdown("#### 💵 Flujo Histórico de Dividendos y Retenciones Fiscales")
    div_col_ctrl, div_col_chart = st.columns([1, 4])
    with div_col_ctrl:
        div_freq = st.selectbox(
            "Período de Agrupación:",
            options=["Trimestral (Q)", "Anual (Año)"],
            index=0,
        )
        freq_code = "Y" if "Anual" in div_freq else "Q"

    div_history_df = calculate_dividend_history(f_cashflows, freq=freq_code)

    with div_col_chart:
        if not div_history_df.empty:
            fig_divs = go.Figure()

            # Bar 1: Gross Dividends
            fig_divs.add_trace(
                go.Bar(
                    x=div_history_df["period"],
                    y=div_history_df["gross_dividend"],
                    name="Dividendo Bruto",
                    marker_color="#38BDF8",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Dividendo Bruto: "
                        + ("$ ••••••" if privacy_mode else "$%{y:,.2f} USD")
                        + "<extra></extra>"
                    ),
                )
            )

            # Bar 2: NRA Tax
            fig_divs.add_trace(
                go.Bar(
                    x=div_history_df["period"],
                    y=div_history_df["nra_tax"],
                    name="Retención Fiscal",
                    marker_color="#EF4444",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Retención Fiscal: "
                        + ("$ ••••••" if privacy_mode else "$%{y:,.2f} USD")
                        + "<extra></extra>"
                    ),
                )
            )

            # Bar 3: Net Dividend
            fig_divs.add_trace(
                go.Bar(
                    x=div_history_df["period"],
                    y=div_history_df["net_dividend"],
                    name="Dividendo Neto Cobrado",
                    marker_color="#10B981",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Dividendo Neto: "
                        + ("$ ••••••" if privacy_mode else "$%{y:,.2f} USD")
                        + "<extra></extra>"
                    ),
                )
            )

            fig_divs.update_layout(
                barmode="group",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=11),
                ),
                xaxis=dict(showgrid=False),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255, 255, 255, 0.07)",
                    tickprefix="" if privacy_mode else "$",
                    showticklabels=not privacy_mode,
                ),
            )
            st.plotly_chart(fig_divs, use_container_width=True)
        else:
            st.info("Sin registros de dividendos en esta selección.")

    st.markdown("---")

    # 4. Tabla de Posiciones Actuales (Holdings Ledger)
    st.markdown("#### 📋 Tenencias Actuales en Portafolio (Holdings Ledger)")
    holdings_df = calculate_holdings_metrics(f_positions)

    if not holdings_df.empty:
        disp_holdings = pd.DataFrame()
        disp_holdings["Broker"] = holdings_df["broker_account_id"].map({
            "schwab_broker": "Schwab",
            "iol_broker": "IOL",
            "binance_crypto": "Binance",
        }).fillna(holdings_df["broker_account_id"])
        disp_holdings["Ticker"] = holdings_df["asset_id"]
        disp_holdings["Instrumento"] = holdings_df["display_name"]
        disp_holdings["Clase de Activo"] = holdings_df["detailed_asset_class"]
        disp_holdings["Moneda"] = holdings_df["currency"]
        disp_holdings["Títulos"] = holdings_df["quantity"].apply(lambda q: format_number(q, decimals=4))
        disp_holdings["Precio Promedio"] = holdings_df["avg_cost"].apply(
            lambda v: format_currency(v, privacy_mode=privacy_mode) if v > 0 else "-"
        )
        disp_holdings["Precio Mercado"] = holdings_df["market_price"].apply(
            lambda v: format_currency(v, privacy_mode=privacy_mode)
        )
        cost_col = "cost_basis_usd" if "cost_basis_usd" in holdings_df.columns else "cost_basis_original"
        disp_holdings["Costo Base ($)"] = holdings_df[cost_col].apply(
            lambda v: format_currency(v, privacy_mode=privacy_mode) if v > 0 else "-"
        )
        disp_holdings["Valuación Mercado ($)"] = holdings_df["market_value_usd"].apply(
            lambda v: format_currency(v, privacy_mode=privacy_mode)
        )
        disp_holdings["P&L ($)"] = holdings_df["unrealized_pnl_usd"].apply(
            lambda v: format_currency(v, privacy_mode=privacy_mode, show_sign=True) if v != 0 else "-"
        )
        disp_holdings["Retorno (%)"] = holdings_df["unrealized_pnl_pct"].apply(
            lambda v: format_percent(v, privacy_mode=privacy_mode) if v != 0 else "-"
        )
        disp_holdings["Ponderación"] = holdings_df["weight_pct"].apply(lambda v: f"{v:.1f}%")

        st.dataframe(
            disp_holdings,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # 5. Libro Histórico de Transacciones (Transactions Ledger)
    st.markdown("#### 📜 Registro Detallado de Movimientos (Transactions Ledger)")

    if not f_cashflows.empty:
        col_filt1, col_filt2, col_filt3 = st.columns([2, 3, 1])

        with col_filt1:
            all_types = sorted(f_cashflows["event_type"].dropna().unique().tolist())
            type_options = ["Todos"] + all_types
            selected_type = st.selectbox("Filtrar por Tipo de Evento:", options=type_options, index=0)

        with col_filt2:
            search_query = st.text_input(
                "Buscar por Activo o Descripción:",
                placeholder="Ej: SCHB, SPY, dividend, Banco Industrial, Wire, etc.",
            )

        with col_filt3:
            page_size = st.selectbox("Filas por página:", options=[10, 25, 50, 100, "Todas"], index=1)

        # Apply filtering
        filtered_cf = f_cashflows.copy()

        if selected_type != "Todos":
            filtered_cf = filtered_cf[filtered_cf["event_type"] == selected_type]

        if search_query:
            q = search_query.strip().lower()
            filtered_cf = filtered_cf[
                filtered_cf["asset_id"].str.lower().str.contains(q, na=False)
                | filtered_cf["notes"].str.lower().str.contains(q, na=False)
                | filtered_cf["event_type"].str.lower().str.contains(q, na=False)
            ]

        total_txns = len(filtered_cf)
        total_original = len(f_cashflows)
        st.caption(f"Mostrando **{total_txns}** de **{total_original}** movimientos registrados.")

        disp_cf = pd.DataFrame()
        disp_cf["Fecha"] = pd.to_datetime(filtered_cf["event_date"]).dt.strftime("%Y-%m-%d")
        disp_cf["Broker"] = filtered_cf["broker_account_id"].map({
            "schwab_broker": "Schwab",
            "iol_broker": "IOL",
            "binance_crypto": "Binance",
        }).fillna(filtered_cf["broker_account_id"])
        disp_cf["Tipo"] = filtered_cf["event_type"].str.upper()
        disp_cf["Activo"] = filtered_cf["asset_id"]
        disp_cf["Cantidad"] = filtered_cf["quantity"].apply(
            lambda q: format_number(q, decimals=4) if q > 0 else "-"
        )
        disp_cf["Moneda"] = filtered_cf["currency"]
        disp_cf["Monto Original"] = filtered_cf.apply(
            lambda r: f"{r['currency']} {format_number(abs(r['gross_amount_original']), decimals=2)}",
            axis=1,
        )
        disp_cf["Monto USD ($)"] = filtered_cf["gross_amount_usd"].apply(
            lambda m: format_currency(m, privacy_mode=privacy_mode)
        )
        disp_cf["Comisión ($)"] = filtered_cf["fees_original"].apply(
            lambda f: format_currency(f, privacy_mode=privacy_mode) if f > 0 else "-"
        )
        disp_cf["Notas y Concepto"] = filtered_cf["notes"]

        if page_size == "Todas":
            paged_data = disp_cf
        else:
            paged_data = disp_cf.head(int(page_size))

        st.dataframe(
            paged_data,
            use_container_width=True,
            hide_index=True,
        )
