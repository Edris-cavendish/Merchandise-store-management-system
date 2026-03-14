from __future__ import annotations

from datetime import date

from app.db.database import DatabaseManager


class InventoryService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def list_categories(self) -> list[dict]:
        rows = self.database.fetch_all("SELECT * FROM categories ORDER BY name")
        return [dict(row) for row in rows]

    def create_category(self, name: str, description: str = "") -> int:
        return self.database.execute(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            (name.strip(), description.strip()),
        )

    def list_products(self) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT
                products.id,
                products.sku,
                products.name,
                products.supplier,
                products.cost_price,
                products.unit_price,
                products.stock_qty,
                products.low_stock_threshold,
                products.description,
                categories.name AS category_name,
                categories.id AS category_id,
                products.updated_at,
                (
                    SELECT payment_type
                    FROM stock_purchases sp
                    WHERE sp.product_id = products.id
                    ORDER BY sp.purchase_date DESC, sp.id DESC
                    LIMIT 1
                ) AS last_payment_type,
                (
                    SELECT purchase_date
                    FROM stock_purchases sp
                    WHERE sp.product_id = products.id
                    ORDER BY sp.purchase_date DESC, sp.id DESC
                    LIMIT 1
                ) AS last_purchase_date,
                (
                    SELECT CASE WHEN sp.total_cost - sp.amount_paid > 0 THEN sp.total_cost - sp.amount_paid ELSE 0 END
                    FROM stock_purchases sp
                    WHERE sp.product_id = products.id
                    ORDER BY sp.purchase_date DESC, sp.id DESC
                    LIMIT 1
                ) AS last_pending_amount
            FROM products
            LEFT JOIN categories ON categories.id = products.category_id
            ORDER BY products.name
            """
        )
        return [dict(row) for row in rows]

    def get_product(self, product_id: int) -> dict:
        row = self.database.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
        if row is None:
            raise ValueError("Product not found.")
        return dict(row)

    def create_product(self, payload: dict) -> int:
        return self.database.execute(
            """
            INSERT INTO products (
                sku, name, category_id, supplier, cost_price, unit_price, stock_qty, low_stock_threshold, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["sku"],
                payload["name"],
                payload.get("category_id"),
                payload.get("supplier", ""),
                payload.get("cost_price", 0.0),
                payload["unit_price"],
                payload["stock_qty"],
                payload["low_stock_threshold"],
                payload.get("description", ""),
            ),
        )

    def update_product(self, product_id: int, payload: dict) -> None:
        self.database.execute(
            """
            UPDATE products
            SET sku = ?, name = ?, category_id = ?, supplier = ?, cost_price = ?, unit_price = ?, stock_qty = ?,
                low_stock_threshold = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                payload["sku"],
                payload["name"],
                payload.get("category_id"),
                payload.get("supplier", ""),
                payload.get("cost_price", 0.0),
                payload["unit_price"],
                payload["stock_qty"],
                payload["low_stock_threshold"],
                payload.get("description", ""),
                product_id,
            ),
        )

    def delete_product(self, product_id: int) -> None:
        self.database.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def create_stock_purchase(self, payload: dict, actor_user_id: int | None = None) -> int:
        product_id = int(payload["product_id"])
        supplier_name = payload.get("supplier_name", "").strip()
        purchase_date = payload.get("purchase_date", "").strip() or date.today().isoformat()
        quantity = int(payload.get("quantity", 0))
        unit_cost = float(payload.get("unit_cost", 0))
        payment_type = payload.get("payment_type", "cash")
        amount_paid = float(payload.get("amount_paid", 0))
        notes = payload.get("notes", "").strip()

        if not supplier_name:
            raise ValueError("Supplier name is required for stock purchases.")
        if quantity <= 0 or unit_cost < 0:
            raise ValueError("Purchase quantity must be greater than zero and unit cost cannot be negative.")
        if payment_type not in {"cash", "credit"}:
            raise ValueError("Payment type must be cash or credit.")

        total_cost = round(quantity * unit_cost, 2)
        if payment_type == "cash":
            amount_paid = total_cost
        elif amount_paid < 0 or amount_paid > total_cost:
            raise ValueError("Credit purchases can only record a paid amount between zero and the total cost.")

        self.get_product(product_id)
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO stock_purchases (
                    product_id, supplier_name, purchase_date, quantity, unit_cost, total_cost,
                    payment_type, amount_paid, notes, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    supplier_name,
                    purchase_date,
                    quantity,
                    unit_cost,
                    total_cost,
                    payment_type,
                    amount_paid,
                    notes,
                    actor_user_id,
                ),
            )
            purchase_id = int(cursor.lastrowid)

            if amount_paid > 0:
                connection.execute(
                    """
                    INSERT INTO supplier_payments (purchase_id, payment_date, amount, notes, created_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        purchase_id,
                        purchase_date,
                        amount_paid,
                        "Initial payment at stock purchase",
                        actor_user_id,
                    ),
                )

            connection.execute(
                """
                UPDATE products
                SET supplier = ?, cost_price = ?, stock_qty = stock_qty + ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (supplier_name, unit_cost, quantity, product_id),
            )

        return purchase_id

    def list_stock_purchases(self, outstanding_only: bool = False, limit: int = 250) -> list[dict]:
        where_clause = "WHERE sp.total_cost - sp.amount_paid > 0.009" if outstanding_only else ""
        rows = self.database.fetch_all(
            f"""
            SELECT
                sp.id,
                sp.product_id,
                p.name AS product_name,
                p.sku,
                sp.supplier_name,
                sp.purchase_date,
                sp.quantity,
                sp.unit_cost,
                sp.total_cost,
                sp.payment_type,
                sp.amount_paid,
                CASE WHEN sp.total_cost - sp.amount_paid > 0 THEN sp.total_cost - sp.amount_paid ELSE 0 END AS outstanding_amount,
                sp.notes,
                sp.created_at
            FROM stock_purchases sp
            JOIN products p ON p.id = sp.product_id
            {where_clause}
            ORDER BY sp.purchase_date DESC, sp.id DESC
            LIMIT {int(limit)}
            """
        )
        return [dict(row) for row in rows]

    def get_stock_purchase(self, purchase_id: int) -> dict:
        row = self.database.fetch_one(
            """
            SELECT
                sp.*,
                p.name AS product_name,
                p.sku
            FROM stock_purchases sp
            JOIN products p ON p.id = sp.product_id
            WHERE sp.id = ?
            """,
            (purchase_id,),
        )
        if row is None:
            raise ValueError("Stock purchase record not found.")
        purchase = dict(row)
        purchase["outstanding_amount"] = round(max(float(purchase["total_cost"]) - float(purchase["amount_paid"]), 0), 2)
        return purchase

    def record_stock_payment(self, purchase_id: int, amount: float, payment_date: str, notes: str = "", actor_user_id: int | None = None) -> None:
        purchase = self.get_stock_purchase(purchase_id)
        outstanding = float(purchase["outstanding_amount"])
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        if amount > outstanding:
            raise ValueError("Payment amount cannot be greater than the outstanding balance.")
        if not payment_date.strip():
            raise ValueError("Payment date is required.")

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO supplier_payments (purchase_id, payment_date, amount, notes, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (purchase_id, payment_date.strip(), amount, notes.strip(), actor_user_id),
            )
            connection.execute(
                "UPDATE stock_purchases SET amount_paid = amount_paid + ? WHERE id = ?",
                (amount, purchase_id),
            )

    def supplier_payment_history(self, purchase_id: int) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT payment_date, amount, notes, created_at
            FROM supplier_payments
            WHERE purchase_id = ?
            ORDER BY payment_date DESC, id DESC
            """,
            (purchase_id,),
        )
        return [dict(row) for row in rows]

    def recent_products(self, limit: int = 8) -> list[dict]:
        rows = self.database.fetch_all(
            f"""
            SELECT sku, name, supplier, created_at, updated_at
            FROM products
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT {int(limit)}
            """
        )
        return [dict(row) for row in rows]

    def recent_products_count(self, days: int = 7) -> int:
        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM products
            WHERE date(created_at, 'localtime') >= date('now', ?, 'localtime')
            """,
            (f"-{int(days)} day",),
        )
        return int(row["total"]) if row else 0

    def low_stock_products(self) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT
                products.id,
                products.name,
                products.sku,
                products.stock_qty,
                products.low_stock_threshold,
                products.supplier
            FROM products
            WHERE stock_qty <= low_stock_threshold
            ORDER BY stock_qty ASC, name
            """
        )
        return [dict(row) for row in rows]

    def inventory_value(self) -> float:
        row = self.database.fetch_one(
            "SELECT COALESCE(SUM(stock_qty * unit_price), 0) AS total_value FROM products"
        )
        return round(float(row["total_value"]) if row else 0, 2)

    def inventory_cost_value(self) -> float:
        row = self.database.fetch_one(
            "SELECT COALESCE(SUM(stock_qty * cost_price), 0) AS total_value FROM products"
        )
        return round(float(row["total_value"]) if row else 0, 2)

    def outstanding_supplier_balance(self) -> float:
        row = self.database.fetch_one(
            "SELECT COALESCE(SUM(CASE WHEN total_cost - amount_paid > 0 THEN total_cost - amount_paid ELSE 0 END), 0) AS total_outstanding FROM stock_purchases"
        )
        return round(float(row["total_outstanding"]) if row else 0, 2)
