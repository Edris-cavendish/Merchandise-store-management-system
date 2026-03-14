from __future__ import annotations

from datetime import datetime
from typing import Any

from app.config import DEFAULT_VAT_RATE, STORE_NAME
from app.db.database import DatabaseManager
from app.utils.currency import DEFAULT_CURRENCY_SYMBOL, DEFAULT_USE_DECIMALS
from app.utils.receipts import build_receipt_text, export_receipt_pdf, export_receipt_text


class SalesService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def calculate_totals(self, cart_items: list[dict], discount: float, tax_rate: float = DEFAULT_VAT_RATE) -> dict:
        subtotal = round(sum(item["quantity"] * item["unit_price"] for item in cart_items), 2)
        discount_amount = round(min(max(discount, 0), subtotal), 2)
        taxable_amount = max(subtotal - discount_amount, 0)
        tax_amount = round(taxable_amount * tax_rate, 2)
        total = round(taxable_amount + tax_amount, 2)
        return {
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "total": total,
        }

    def create_sale(
        self,
        cashier_id: int,
        payment_method: str,
        cart_items: list[dict],
        discount: float,
        tax_rate: float = DEFAULT_VAT_RATE,
    ) -> dict[str, Any]:
        if not cart_items:
            raise ValueError("Add at least one item before checkout.")

        prepared_items: list[dict] = []
        for item in cart_items:
            product = self.database.fetch_one(
                "SELECT stock_qty, name, cost_price FROM products WHERE id = ?",
                (item["product_id"],),
            )
            if product is None:
                raise ValueError("One of the selected products no longer exists.")
            if int(product["stock_qty"]) < int(item["quantity"]):
                raise ValueError(f"Insufficient stock for {product['name']}.")
            prepared_items.append(
                {
                    **item,
                    "unit_cost": float(product["cost_price"] or 0),
                }
            )

        totals = self.calculate_totals(prepared_items, discount, tax_rate)
        created_at = datetime.now()
        receipt_no = f"EDR-{created_at.strftime('%Y%m%d-%H%M%S')}"
        settings = self._currency_and_store_settings()
        cashier_row = self.database.fetch_one("SELECT full_name FROM users WHERE id = ?", (cashier_id,))
        cashier_name = cashier_row["full_name"] if cashier_row else "System User"

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sales (
                    receipt_no, cashier_id, cashier_name, store_name, currency_symbol, use_decimals,
                    subtotal, tax_amount, discount_amount, total_amount, payment_method
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_no,
                    cashier_id,
                    cashier_name,
                    settings["store_name"],
                    settings["currency_symbol"],
                    1 if settings["use_decimals"] else 0,
                    totals["subtotal"],
                    totals["tax_amount"],
                    totals["discount_amount"],
                    totals["total"],
                    payment_method,
                ),
            )
            sale_id = int(cursor.lastrowid)

            for item in prepared_items:
                line_total = round(item["quantity"] * item["unit_price"], 2)
                cost_total = round(item["quantity"] * item["unit_cost"], 2)
                connection.execute(
                    """
                    INSERT INTO sale_items (
                        sale_id, product_id, product_name, quantity, unit_price, line_total, unit_cost, cost_total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        item["product_id"],
                        item["name"],
                        item["quantity"],
                        item["unit_price"],
                        line_total,
                        item["unit_cost"],
                        cost_total,
                    ),
                )
                connection.execute(
                    """
                    UPDATE products
                    SET stock_qty = stock_qty - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (item["quantity"], item["product_id"]),
                )

        return {
            "sale_id": sale_id,
            "store_name": settings["store_name"],
            "currency_symbol": settings["currency_symbol"],
            "use_decimals": settings["use_decimals"],
            "receipt_no": receipt_no,
            "date_time": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "cashier_name": cashier_name,
            "payment_method": payment_method,
            "items": [
                {
                    "name": item["name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "line_total": round(item["quantity"] * item["unit_price"], 2),
                }
                for item in prepared_items
            ],
            **totals,
        }

    def save_receipt(self, receipt_payload: dict, output_path: str) -> None:
        if output_path.lower().endswith(".pdf"):
            export_receipt_pdf(receipt_payload, output_path)
        else:
            export_receipt_text(receipt_payload, output_path)

    def receipt_preview(self, receipt_payload: dict) -> str:
        return build_receipt_text(receipt_payload)

    def sales_today_total(self, cashier_id: int | None = None) -> float:
        return self.sales_total_for_date(datetime.now().strftime("%Y-%m-%d"), cashier_id)

    def sales_total_for_date(self, date_value: str, cashier_id: int | None = None) -> float:
        params: list[Any] = [date_value]
        query = (
            "SELECT COALESCE(SUM(total_amount), 0) AS sales_total FROM sales "
            "WHERE date(created_at, 'localtime') = ?"
        )
        if cashier_id is not None:
            query += " AND cashier_id = ?"
            params.append(cashier_id)
        row = self.database.fetch_one(query, tuple(params))
        return round(float(row["sales_total"]) if row else 0, 2)

    def sales_count_today(self, cashier_id: int | None = None) -> int:
        params: list[Any] = []
        query = "SELECT COUNT(*) AS total FROM sales WHERE date(created_at, 'localtime') = date('now', 'localtime')"
        if cashier_id is not None:
            query += " AND cashier_id = ?"
            params.append(cashier_id)
        row = self.database.fetch_one(query, tuple(params))
        return int(row["total"]) if row else 0

    def recent_sales(self, limit: int = 10, cashier_id: int | None = None) -> list[dict]:
        where_clause = "WHERE cashier_id = ?" if cashier_id is not None else ""
        params: tuple[Any, ...] = (cashier_id,) if cashier_id is not None else ()
        rows = self.database.fetch_all(
            f"""
            SELECT receipt_no, total_amount, payment_method, created_at
            FROM sales
            {where_clause}
            ORDER BY id DESC
            LIMIT {int(limit)}
            """,
            params,
        )
        return [dict(row) for row in rows]

    def list_receipts(self, limit: int = 250, cashier_id: int | None = None) -> list[dict]:
        where_clause = "WHERE cashier_id = ?" if cashier_id is not None else ""
        params: tuple[Any, ...] = (cashier_id,) if cashier_id is not None else ()
        rows = self.database.fetch_all(
            f"""
            SELECT
                id,
                receipt_no,
                cashier_id,
                cashier_name,
                store_name,
                currency_symbol,
                use_decimals,
                payment_method,
                total_amount,
                created_at
            FROM sales
            {where_clause}
            ORDER BY id DESC
            LIMIT {int(limit)}
            """,
            params,
        )
        return [dict(row) for row in rows]

    def get_receipt_payload(self, sale_id: int, cashier_id: int | None = None) -> dict[str, Any]:
        params: list[Any] = [sale_id]
        query = (
            "SELECT id, receipt_no, cashier_id, cashier_name, store_name, currency_symbol, use_decimals, "
            "payment_method, subtotal, tax_amount, discount_amount, total_amount, created_at "
            "FROM sales WHERE id = ?"
        )
        if cashier_id is not None:
            query += " AND cashier_id = ?"
            params.append(cashier_id)
        sale = self.database.fetch_one(query, tuple(params))
        if sale is None:
            raise ValueError("Receipt record not found or you do not have access to it.")

        items = self.database.fetch_all(
            """
            SELECT product_name, quantity, unit_price, line_total
            FROM sale_items
            WHERE sale_id = ?
            ORDER BY id
            """,
            (sale_id,),
        )
        sale_row = dict(sale)
        return {
            "sale_id": int(sale_row["id"]),
            "store_name": sale_row.get("store_name") or STORE_NAME,
            "currency_symbol": sale_row.get("currency_symbol") or DEFAULT_CURRENCY_SYMBOL,
            "use_decimals": bool(sale_row.get("use_decimals", 1)),
            "receipt_no": sale_row["receipt_no"],
            "date_time": sale_row["created_at"],
            "cashier_name": sale_row.get("cashier_name") or "System User",
            "payment_method": sale_row["payment_method"],
            "items": [
                {
                    "name": item["product_name"] or "Unknown Product",
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "line_total": item["line_total"],
                }
                for item in items
            ],
            "subtotal": sale_row["subtotal"],
            "discount_amount": sale_row["discount_amount"],
            "tax_amount": sale_row["tax_amount"],
            "total": sale_row["total_amount"],
        }

    def _currency_and_store_settings(self) -> dict:
        store_row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("store_name",))
        currency_row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("currency_symbol",))
        decimals_row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("use_decimals",))
        return {
            "store_name": store_row["value"] if store_row else STORE_NAME,
            "currency_symbol": currency_row["value"] if currency_row else DEFAULT_CURRENCY_SYMBOL,
            "use_decimals": (decimals_row["value"] if decimals_row else ("1" if DEFAULT_USE_DECIMALS else "0"))
            not in {"0", "false", "False"},
        }
