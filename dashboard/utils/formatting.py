"""Formatting utilities for currency, percentages, numbers, and privacy mode."""

def format_currency(val, currency="USD", privacy_mode=False, decimals=2, show_sign=False) -> str:
    """
    Format numeric value as currency.
    If privacy_mode is True, returns masked string '$ ••••••'.
    """
    if privacy_mode:
        return "$ ••••••"
    if val is None:
        return "$0.00"
    try:
        num = float(val)
    except (ValueError, TypeError):
        return "$0.00"

    sign = ""
    if show_sign and num > 0:
        sign = "+"
    elif num < 0:
        sign = "-"
        num = abs(num)

    formatted_num = f"{num:,.{decimals}f}"
    if currency:
        return f"{sign}${formatted_num} {currency}".strip()
    return f"{sign}${formatted_num}".strip()


def format_percent(val, decimals=2, show_sign=True, privacy_mode=False) -> str:
    """
    Format numeric value as percentage.
    """
    if privacy_mode:
        return "•••%"
    if val is None:
        return "0.00%"
    try:
        num = float(val)
    except (ValueError, TypeError):
        return "0.00%"

    sign = ""
    if show_sign and num > 0:
        sign = "+"
    elif num < 0:
        sign = "-"
        num = abs(num)

    return f"{sign}{num:.{decimals}f}%"


def format_number(val, decimals=4) -> str:
    """
    Format numeric values like quantity of shares.
    """
    if val is None:
        return "0"
    try:
        num = float(val)
        # If integer, can return cleaner representation if desired, or fixed decimals
        return f"{num:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)
