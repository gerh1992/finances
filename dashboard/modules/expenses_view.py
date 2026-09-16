"""Módulo de Gastos y Flujo Mensual para el Financial Dashboard."""
from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.formatting import format_currency
from utils.ui_components import render_kpi_card


def render_expenses_view(data: Dict[str, pd.DataFrame], privacy_mode: bool = False):
    """Renders the expenses and monthly cashflow view."""
    st.markdown("### 💸 Gastos y Flujo Mensual (Fase 2)")

    monthly_exp_df = data.get("monthly_expenses", pd.DataFrame())
    txns_df = data.get("transactions", pd.DataFrame())

    # Aggregate outflows from normalized transactions if available
    has_txns = not txns_df.empty and "direction" in txns_df.columns
    outflows = txns_df[txns_df["direction"] == "outflow"].copy() if has_txns else pd.DataFrame()

    total_expense_ars = abs(outflows["amount_original"].sum()) if not outflows.empty else 0.0
    # Estimated conversion using average FX or reference
    total_expense_usd = total_expense_ars / 1350.0 if total_expense_ars > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi_card(
            title="Gasto Registrado (Período)",
            value=format_currency(total_expense_usd, privacy_mode=privacy_mode),
            subtitle=f"{format_currency(total_expense_ars, currency='ARS', privacy_mode=privacy_mode)} en moneda local",
        )
    with col2:
        render_kpi_card(
            title="Estructura de Gasto",
            value="Discrecional (85%)" if not privacy_mode else "••••••",
            subtitle="Fijos: 15% | Variables: 85%",
        )
    with col3:
        render_kpi_card(
            title="Movimientos Egresos",
            value=f"{len(outflows)} transacciones",
            subtitle="Fuente: MercadoPago / Cuentas operativas",
        )

    st.markdown("---")

    row2_c1, row2_c2 = st.columns([1, 1])

    with row2_c1:
        st.markdown("#### 🛒 Desglose por Buckets de Gasto")
        if not outflows.empty and "expense_bucket" in outflows.columns:
            bucket_summary = (
                outflows.groupby("expense_bucket")["amount_original"]
                .apply(lambda s: abs(s.sum()))
                .reset_index()
            )
            bucket_summary.columns = ["Bucket", "Monto ARS"]
            fig_bucket = px.bar(
                bucket_summary,
                x="Bucket",
                y="Monto ARS",
                color="Bucket",
                template="plotly_dark",
                text_auto=True,
            )
            fig_bucket.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                yaxis=dict(showticklabels=not privacy_mode),
            )
            st.plotly_chart(fig_bucket, use_container_width=True)
        else:
            st.info("Sin registros de categorías en el período.")

    with row2_c2:
        st.markdown("#### 📑 Detalle de Transacciones Recientes de Gasto")
        if not outflows.empty:
            disp_out = outflows[["txn_date", "description_raw", "amount_original", "currency", "expense_type"]].copy()
            disp_out["txn_date"] = pd.to_datetime(disp_out["txn_date"]).dt.strftime("%Y-%m-%d")
            disp_out["amount_original"] = disp_out.apply(
                lambda r: format_currency(abs(r["amount_original"]), currency=r["currency"], privacy_mode=privacy_mode),
                axis=1,
            )
            disp_out.columns = ["Fecha", "Descripción", "Monto", "Moneda", "Tipo"]
            st.dataframe(disp_out.head(15), use_container_width=True, hide_index=True)
        else:
            st.info("Sin transacciones de egreso.")
