"""UI components and custom styling for Streamlit financial dashboard."""
import streamlit as st

def inject_custom_css():
    """Inject subtle, elegant CSS styles matching the dark dashboard aesthetic."""
    st.markdown(
        """
        <style>
        /* Global layout tweaks */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 96%;
        }

        /* Glassmorphism Metric Card */
        .kpi-card {
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.75), rgba(15, 23, 42, 0.85));
            border: 1px solid rgba(56, 189, 248, 0.15);
            border-radius: 12px;
            padding: 1.1rem 1.25rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .kpi-card:hover {
            border-color: rgba(56, 189, 248, 0.35);
            transform: translateY(-2px);
        }
        .kpi-title {
            color: #94A3B8;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.4rem;
        }
        .kpi-value {
            color: #F8FAFC;
            font-size: 1.7rem;
            font-weight: 700;
            line-height: 1.2;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .kpi-subtitle {
            color: #64748B;
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }
        .kpi-delta-positive {
            color: #10B981;
            font-weight: 600;
            font-size: 0.88rem;
            margin-top: 0.35rem;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .kpi-delta-negative {
            color: #EF4444;
            font-weight: 600;
            font-size: 0.88rem;
            margin-top: 0.35rem;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* Status Badges */
        .badge-audited {
            display: inline-flex;
            align-items: center;
            background-color: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 9999px;
            padding: 0.25rem 0.75rem;
            font-size: 0.78rem;
            font-weight: 500;
        }
        .badge-pill {
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-buy { background-color: rgba(56, 189, 248, 0.2); color: #38BDF8; }
        .badge-dividend { background-color: rgba(16, 185, 129, 0.2); color: #34D399; }
        .badge-fee { background-color: rgba(245, 158, 11, 0.2); color: #FBBF24; }
        .badge-deposit { background-color: rgba(139, 92, 246, 0.2); color: #A78BFA; }

        /* Custom Header styling */
        .header-title-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 1.25rem;
        }
        .header-title {
            font-size: 1.85rem;
            font-weight: 800;
            background: linear-gradient(90deg, #F8FAFC 0%, #38BDF8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .header-subtitle {
            color: #94A3B8;
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }
        .header-nw-container {
            text-align: right;
        }
        .header-nw-label {
            color: #94A3B8;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .header-nw-value {
            font-size: 1.9rem;
            font-weight: 800;
            color: #38BDF8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(title: str, value: str, subtitle: str = None, delta: str = None, is_positive: bool = True):
    """Renders an aesthetic KPI card with HTML/CSS."""
    delta_html = ""
    if delta:
        css_class = "kpi-delta-positive" if is_positive else "kpi-delta-negative"
        arrow = "▲" if is_positive else "▼"
        delta_html = f'<div class="{css_class}">{arrow} {delta}</div>'

    sub_html = f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ""

    html = (
        f'<div class="kpi-card">'
        f'<div class="kpi-title">{title}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}'
        f'{sub_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
