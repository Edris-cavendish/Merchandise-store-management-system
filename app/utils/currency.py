from __future__ import annotations

DEFAULT_CURRENCY_SYMBOL = "$"
DEFAULT_USE_DECIMALS = True


def normalize_currency_symbol(currency_symbol: str | None) -> str:
    cleaned = (currency_symbol or "").strip()
    return cleaned or DEFAULT_CURRENCY_SYMBOL


def normalize_use_decimals(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", ""}
    return DEFAULT_USE_DECIMALS


def format_money(amount: float | int, currency_symbol: str | None = None, use_decimals=True) -> str:
    symbol = normalize_currency_symbol(currency_symbol)
    decimals = normalize_use_decimals(use_decimals)
    numeric = float(amount or 0)
    precision = 2 if decimals else 0
    number = f"{numeric:,.{precision}f}"
    if not decimals:
        number = number.split(".")[0]

    separator = "" if len(symbol) == 1 and not symbol.isalnum() else " "
    return f"{symbol}{separator}{number}".strip()
