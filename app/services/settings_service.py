from __future__ import annotations

from app.config import STORE_NAME
from app.db.database import DatabaseManager
from app.utils.currency import DEFAULT_CURRENCY_SYMBOL, DEFAULT_USE_DECIMALS, format_money, normalize_currency_symbol, normalize_use_decimals


class SettingsService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def get_store_name(self) -> str:
        row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("store_name",))
        return row["value"] if row else STORE_NAME

    def get_currency_settings(self) -> dict:
        symbol_row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("currency_symbol",))
        decimals_row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("use_decimals",))
        return {
            "currency_symbol": normalize_currency_symbol(symbol_row["value"] if symbol_row else DEFAULT_CURRENCY_SYMBOL),
            "use_decimals": normalize_use_decimals(decimals_row["value"] if decimals_row else DEFAULT_USE_DECIMALS),
        }

    def get_app_settings(self) -> dict:
        currency = self.get_currency_settings()
        return {
            "store_name": self.get_store_name(),
            **currency,
        }

    def update_branding(self, store_name: str, currency_symbol: str, use_decimals: bool) -> dict:
        cleaned_store_name = store_name.strip()
        if not cleaned_store_name:
            raise ValueError("Store name cannot be empty.")

        normalized_symbol = normalize_currency_symbol(currency_symbol)
        normalized_decimals = normalize_use_decimals(use_decimals)
        updates = (
            ("store_name", cleaned_store_name),
            ("currency_symbol", normalized_symbol),
            ("use_decimals", "1" if normalized_decimals else "0"),
        )
        for key, value in updates:
            self.database.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
        return {
            "store_name": cleaned_store_name,
            "currency_symbol": normalized_symbol,
            "use_decimals": normalized_decimals,
        }

    def format_money(self, amount: float | int, currency_settings: dict | None = None) -> str:
        settings = currency_settings or self.get_currency_settings()
        return format_money(amount, settings.get("currency_symbol"), settings.get("use_decimals"))

    # ── Measurement units ─────────────────────────────────────────────────────

    def get_measurement_units(self) -> list[str]:
        rows = self.database.fetch_all("SELECT name FROM measurement_units ORDER BY name")
        return [row["name"] for row in rows]

    def add_measurement_unit(self, name: str) -> None:
        name = name.strip().lower()
        if not name:
            raise ValueError("Unit name cannot be empty.")
        existing = {u.lower() for u in self.get_measurement_units()}
        if name in existing:
            raise ValueError(f"Unit '{name}' already exists.")
        self.database.execute("INSERT INTO measurement_units (name) VALUES (?)", (name,))

    def remove_measurement_unit(self, name: str) -> None:
        self.database.execute("DELETE FROM measurement_units WHERE name = ?", (name,))
