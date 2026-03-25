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

    def update_category(self, category_id: int, name: str, description: str = "") -> None:
        self.database.execute(
            "UPDATE categories SET name = ?, description = ? WHERE id = ?",
            (name.strip(), description.strip(), category_id),
        )

    def get_products_by_category(self, category_id: int) -> list[dict]:
        """Get all products in a specific category."""
        rows = self.database.fetch_all(
            "SELECT id, sku, name FROM products WHERE category_id = ? ORDER BY name",
            (category_id,)
        )
        return [dict(row) for row in rows]

    def transfer_products_to_category(self, from_category_id: int, to_category_id: int) -> int:
        """Transfer products and re-key SKUs to the target category prefix.

        Returns the number of moved products.
        """
        if from_category_id == to_category_id:
            raise ValueError("Source and target categories must be different.")

        with self.database.connect() as connection:
            source = connection.execute(
                "SELECT id, name FROM categories WHERE id = ?",
                (from_category_id,),
            ).fetchone()
            target = connection.execute(
                "SELECT id, name FROM categories WHERE id = ?",
                (to_category_id,),
            ).fetchone()
            if source is None:
                raise ValueError("Source category not found.")
            if target is None:
                raise ValueError("Target category not found.")

            rows = connection.execute(
                "SELECT id FROM products WHERE category_id = ? ORDER BY id",
                (from_category_id,),
            ).fetchall()
            product_ids = [int(row["id"]) for row in rows]
            if not product_ids:
                return 0

            prefix = str(target["name"])[:3].upper()
            used_rows = connection.execute(
                "SELECT sku FROM products WHERE sku LIKE ? AND category_id != ?",
                (f"{prefix}-%", from_category_id),
            ).fetchall()
            used_numbers: set[int] = set()
            for row in used_rows:
                sku = str(row["sku"] or "")
                if "-" not in sku:
                    continue
                try:
                    used_numbers.add(int(sku.split("-", 1)[1]))
                except ValueError:
                    continue

            next_number = 1
            for product_id in product_ids:
                temp_sku = f"__XFER__{product_id}"
                connection.execute(
                    "UPDATE products SET sku = ? WHERE id = ?",
                    (temp_sku, product_id),
                )

            for product_id in product_ids:
                while next_number in used_numbers:
                    next_number += 1
                new_sku = f"{prefix}-{next_number:03d}"
                used_numbers.add(next_number)
                next_number += 1
                connection.execute(
                    "UPDATE products SET category_id = ?, sku = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (to_category_id, new_sku, product_id),
                )

        return len(product_ids)

    def enforce_category_sku_alignment(self) -> list[tuple[str, str, str]]:
        """Fix products whose SKU prefix no longer matches their current category.

        Returns a list of (product_name, old_sku, new_sku) for changed rows.
        """
        changes: list[tuple[str, str, str]] = []
        with self.database.connect() as connection:
            category_rows = connection.execute("SELECT id, name FROM categories").fetchall()
            category_prefix: dict[int, str] = {
                int(row["id"]): str(row["name"] or "UNC")[:3].upper() for row in category_rows
            }

            product_rows = connection.execute(
                """
                SELECT id, name, sku, category_id
                FROM products
                WHERE category_id IS NOT NULL
                ORDER BY id
                """
            ).fetchall()

            by_category: dict[int, list[dict]] = {}
            for row in product_rows:
                cat_id = int(row["category_id"])
                by_category.setdefault(cat_id, []).append(dict(row))

            for cat_id, products in by_category.items():
                prefix = category_prefix.get(cat_id)
                if not prefix:
                    continue

                stable_products: list[dict] = []
                mismatched_products: list[dict] = []
                for product in products:
                    sku = str(product["sku"] or "")
                    if sku.startswith(f"{prefix}-"):
                        suffix = sku.split("-", 1)[1] if "-" in sku else ""
                        if suffix.isdigit():
                            stable_products.append(product)
                            continue
                    mismatched_products.append(product)

                if not mismatched_products:
                    continue

                used_numbers: set[int] = set()
                for product in stable_products:
                    sku = str(product["sku"])
                    used_numbers.add(int(sku.split("-", 1)[1]))

                for product in mismatched_products:
                    temp_sku = f"__ALIGN__{int(product['id'])}"
                    connection.execute(
                        "UPDATE products SET sku = ? WHERE id = ?",
                        (temp_sku, int(product["id"])),
                    )

                next_number = 1
                for product in mismatched_products:
                    while next_number in used_numbers:
                        next_number += 1
                    new_sku = f"{prefix}-{next_number:03d}"
                    used_numbers.add(next_number)
                    next_number += 1

                    old_sku = str(product["sku"] or "")
                    connection.execute(
                        "UPDATE products SET sku = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_sku, int(product["id"])),
                    )
                    changes.append((str(product["name"]), old_sku, new_sku))

        return changes

    def delete_category(self, category_id: int) -> None:
        self.database.execute("DELETE FROM categories WHERE id = ?", (category_id,))

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
                products.measurement_unit,
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
                sku, name, category_id, supplier, cost_price, unit_price, stock_qty, low_stock_threshold, description,
                measurement_unit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                payload.get("measurement_unit", "pcs"),
            ),
        )

    def update_product(self, product_id: int, payload: dict) -> None:
        self.database.execute(
            """
            UPDATE products
            SET sku = ?, name = ?, category_id = ?, supplier = ?, cost_price = ?, unit_price = ?, stock_qty = ?,
                low_stock_threshold = ?, description = ?, measurement_unit = ?, updated_at = CURRENT_TIMESTAMP
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
                payload.get("measurement_unit", "pcs"),
                product_id,
            ),
        )

    def delete_product(self, product_id: int) -> None:
        self.database.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def generate_sku_for_category(self, category_id: int, category_name: str, exclude_sku: str | None = None) -> str:
        """Generate an automatic SKU for a product in the given category.
        
        Format: First 3 letters of category (uppercase) + 3-digit sequential number
        Example: BEV-001, BEV-002 for Beverages
        
        Reuses deleted SKU numbers if available, otherwise continues from the highest number.
        Pass exclude_sku to treat that SKU slot as free (used when re-keying an existing product).
        """
        # Get category prefix (first 3 letters, uppercase)
        prefix = category_name[:3].upper()
        
        # Find all existing SKUs with this prefix
        rows = self.database.fetch_all(
            "SELECT sku FROM products WHERE sku LIKE ?",
            (f"{prefix}-%",)
        )
        
        # Extract all numeric parts, optionally ignoring the excluded SKU
        used_numbers = set()
        for row in rows:
            sku = row["sku"]
            if exclude_sku and sku == exclude_sku:
                continue
            if "-" in sku:
                try:
                    num_part = sku.split("-")[1]
                    num = int(num_part)
                    used_numbers.add(num)
                except (ValueError, IndexError):
                    continue
        
        # Find the smallest available number (reuse deleted SKUs)
        # Start from 1 and find the first gap, or use next sequential if no gaps
        next_number = 1
        while next_number in used_numbers:
            next_number += 1
        
        # Format as XXX-001
        return f"{prefix}-{next_number:03d}"

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
        allowed_payment_types = {"cash", "mobile money", "bank"}
        if payment_type not in allowed_payment_types:
            raise ValueError("Payment type must be cash, mobile money, or bank.")

        product = self.get_product(product_id)
        product_supplier = (product.get("supplier") or "").strip()
        if not product_supplier:
            raise ValueError("Selected product has no supplier in inventory. Set supplier on the product before recording supplier credit.")
        if supplier_name != product_supplier:
            raise ValueError("Supplier must match the supplier linked to the selected product in inventory.")

        total_cost = round(quantity * unit_cost, 2)
        if payment_type == "cash":
            amount_paid = total_cost
        elif amount_paid < 0 or amount_paid > total_cost:
            raise ValueError("Amount paid must be between zero and the total cost.")

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

    def ensure_supplier_payables_seeded(self) -> int:
        """Auto-create supplier payable records for inventory items missing them.

        This seeds one payable per product when all of the following are true:
        - Product has a supplier
        - Product has stock quantity > 0
        - Product has no stock_purchases record yet

        Returns number of created payable records.
        """
        created = 0
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.id,
                    p.supplier,
                    p.stock_qty,
                    p.cost_price,
                    date(COALESCE(p.created_at, CURRENT_TIMESTAMP), 'localtime') AS seed_date
                FROM products p
                WHERE COALESCE(TRIM(p.supplier), '') != ''
                  AND COALESCE(p.stock_qty, 0) > 0
                  AND NOT EXISTS (
                      SELECT 1 FROM stock_purchases sp WHERE sp.product_id = p.id
                  )
                """
            ).fetchall()

            for row in rows:
                product_id = int(row["id"])
                supplier_name = str(row["supplier"]).strip()
                quantity = int(row["stock_qty"])
                unit_cost = float(row["cost_price"] or 0)
                if quantity <= 0 or unit_cost < 0:
                    continue
                total_cost = round(quantity * unit_cost, 2)
                seed_date = str(row["seed_date"] or date.today().isoformat())

                connection.execute(
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
                        seed_date,
                        quantity,
                        unit_cost,
                        total_cost,
                        "bank",
                        0,
                        "Auto-generated from inventory to seed supplier payables",
                        None,
                    ),
                )
                created += 1

        return created

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

    def update_stock_purchase(self, purchase_id: int, payload: dict, actor_user_id: int | None = None) -> None:
        purchase = self.get_stock_purchase(purchase_id)
        old_quantity = int(purchase["quantity"])
        old_product_id = int(purchase["product_id"])

        product_id = int(payload.get("product_id", old_product_id))
        supplier_name = payload.get("supplier_name", "").strip()
        purchase_date = payload.get("purchase_date", "").strip()
        quantity = int(payload.get("quantity", 0))
        unit_cost = float(payload.get("unit_cost", 0))
        payment_type = payload.get("payment_type", "cash")
        notes = payload.get("notes", "").strip()

        if not supplier_name:
            raise ValueError("Supplier name is required for stock purchases.")
        if quantity <= 0 or unit_cost < 0:
            raise ValueError("Purchase quantity must be greater than zero and unit cost cannot be negative.")
        allowed_payment_types = {"cash", "mobile money", "bank"}
        if payment_type not in allowed_payment_types:
            raise ValueError("Payment type must be cash, mobile money, or bank.")

        product = self.get_product(product_id)
        product_supplier = (product.get("supplier") or "").strip()
        if not product_supplier:
            raise ValueError("Selected product has no supplier in inventory. Set supplier on the product before recording supplier credit.")
        if supplier_name != product_supplier:
            raise ValueError("Supplier must match the supplier linked to the selected product in inventory.")

        total_cost = round(quantity * unit_cost, 2)
        amount_paid = float(purchase["amount_paid"])

        # Ensure amount_paid doesn't exceed new total_cost
        if amount_paid > total_cost:
            raise ValueError(f"Cannot reduce total cost below already paid amount ({amount_paid:.2f}).")

        with self.database.connect() as connection:
            # Update the purchase record
            connection.execute(
                """
                UPDATE stock_purchases
                SET product_id = ?, supplier_name = ?, purchase_date = ?, quantity = ?, unit_cost = ?,
                    total_cost = ?, payment_type = ?, notes = ?
                WHERE id = ?
                """,
                (product_id, supplier_name, purchase_date, quantity, unit_cost, total_cost, payment_type, notes, purchase_id),
            )

            # Adjust product stock: remove old quantity, add new quantity
            quantity_diff = quantity - old_quantity
            if quantity_diff != 0 or product_id != old_product_id:
                # Update old product stock (remove old quantity)
                connection.execute(
                    "UPDATE products SET stock_qty = stock_qty - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (old_quantity, old_product_id),
                )
                # Update new product stock (add new quantity)
                connection.execute(
                    """
                    UPDATE products
                    SET supplier = ?, cost_price = ?, stock_qty = stock_qty + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (supplier_name, unit_cost, quantity, product_id),
                )

    def delete_stock_purchase(self, purchase_id: int) -> None:
        purchase = self.get_stock_purchase(purchase_id)
        product_id = int(purchase["product_id"])
        quantity = int(purchase["quantity"])

        with self.database.connect() as connection:
            # Remove stock added by this purchase
            connection.execute(
                "UPDATE products SET stock_qty = stock_qty - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (quantity, product_id),
            )
            # Delete associated payments first
            connection.execute("DELETE FROM supplier_payments WHERE purchase_id = ?", (purchase_id,))
            # Delete the purchase
            connection.execute("DELETE FROM stock_purchases WHERE id = ?", (purchase_id,))

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

    def supplier_payment_log(self, supplier_name: str | None = None, limit: int = 500) -> list[dict]:
        params: list[object] = []
        supplier_filter = ""
        if supplier_name and supplier_name.strip():
            supplier_filter = "WHERE sp.supplier_name = ?"
            params.append(supplier_name.strip())

        rows = self.database.fetch_all(
            f"""
            SELECT
                pay.id AS payment_id,
                pay.purchase_id,
                pay.payment_date,
                pay.amount,
                pay.notes,
                pay.created_at,
                COALESCE(u.full_name, 'System User') AS recorded_by,
                sp.supplier_name,
                sp.total_cost,
                sp.payment_type,
                p.name AS product_name,
                p.sku
            FROM supplier_payments pay
            JOIN stock_purchases sp ON sp.id = pay.purchase_id
            JOIN products p ON p.id = sp.product_id
            LEFT JOIN users u ON u.id = pay.created_by
            {supplier_filter}
            ORDER BY sp.supplier_name, pay.purchase_id, pay.payment_date ASC, pay.id ASC
            LIMIT {int(limit)}
            """,
            tuple(params),
        )

        running_paid_by_purchase: dict[int, float] = {}
        log_rows: list[dict] = []
        for row in rows:
            entry = dict(row)
            purchase_id = int(entry["purchase_id"])
            total_cost = float(entry["total_cost"])
            amount = float(entry["amount"])
            running_paid = running_paid_by_purchase.get(purchase_id, 0.0) + amount
            running_paid_by_purchase[purchase_id] = running_paid
            remaining = round(max(total_cost - running_paid, 0), 2)
            entry["remaining_after_payment"] = remaining
            entry["settlement_status"] = "Full" if remaining <= 0.009 else "Partial"
            entry["payment_reference"] = f"SUP-{purchase_id}-PAY-{entry['payment_id']}"
            log_rows.append(entry)

        return list(reversed(log_rows))

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

    def migrate_skus_to_new_format(self) -> list[tuple[str, str, str]]:
        """Migrate all existing product SKUs to the new category-based format.
        
        Returns a list of tuples (product_name, old_sku, new_sku) for the changes made.
        """
        changes = []
        
        # Get all products with their category info
        rows = self.database.fetch_all(
            """
            SELECT p.id, p.name, p.sku, c.id as category_id, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            ORDER BY c.name, p.id
            """
        )
        
        # Group products by category
        products_by_category: dict[int, list[dict]] = {}
        for row in rows:
            cat_id = row["category_id"]
            if cat_id not in products_by_category:
                products_by_category[cat_id] = []
            products_by_category[cat_id].append(dict(row))
        
        with self.database.connect() as connection:
            for cat_id, products in products_by_category.items():
                if not products:
                    continue
                
                category_name = products[0]["category_name"] or "UNC"
                prefix = category_name[:3].upper() if category_name else "UNC"
                
                # Renumber all products in this category starting from 001
                for index, product in enumerate(products, start=1):
                    old_sku = product["sku"]
                    new_sku = f"{prefix}-{index:03d}"
                    
                    if old_sku != new_sku:
                        connection.execute(
                            "UPDATE products SET sku = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (new_sku, product["id"])
                        )
                        changes.append((product["name"], old_sku, new_sku))
        
        return changes

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

    def list_suppliers(self) -> list[str]:
        """Get unique supplier names from inventory records.
        
        Returns a list of unique non-empty supplier names from both
        products and stock_purchases tables, sorted alphabetically.
        """
        # Get suppliers from products table
        product_suppliers = self.database.fetch_all(
            "SELECT DISTINCT supplier FROM products WHERE supplier IS NOT NULL AND supplier != ''"
        )
        
        # Get suppliers from stock_purchases table
        purchase_suppliers = self.database.fetch_all(
            "SELECT DISTINCT supplier_name FROM stock_purchases WHERE supplier_name IS NOT NULL AND supplier_name != ''"
        )
        
        # Combine and deduplicate
        suppliers = set()
        for row in product_suppliers:
            suppliers.add(row["supplier"])
        for row in purchase_suppliers:
            suppliers.add(row["supplier_name"])
        
        # Sort alphabetically and return as list
        return sorted(list(suppliers))
