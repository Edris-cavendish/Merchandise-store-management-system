from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import DATABASE_PATH, STORE_NAME
from app.db.schema import DEFAULT_CATEGORIES, SCHEMA_SQL
from app.utils.currency import DEFAULT_CURRENCY_SYMBOL, DEFAULT_USE_DECIMALS
from app.utils.security import hash_password


DEFAULT_THEME = "Yellow & White"
VALID_THEMES = (
    "Green & White",
    "Dark Blue & White",
    "Yellow & White",
    "Brown & White",
)


class DatabaseManager:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or DATABASE_PATH)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            self._ensure_schema_migrations(connection)
            self._seed_defaults(connection)

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as connection:
            cursor = connection.execute(query, params)
            return cursor.fetchall()

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.connect() as connection:
            cursor = connection.execute(query, params)
            return cursor.fetchone()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self.connect() as connection:
            cursor = connection.execute(query, params)
            return int(cursor.lastrowid)

    def execute_many(self, query: str, rows: list[tuple[Any, ...]]) -> None:
        with self.connect() as connection:
            connection.executemany(query, rows)

    def _ensure_schema_migrations(self, connection: sqlite3.Connection) -> None:
        user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        if "is_active" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        if "theme_name" not in user_columns:
            connection.execute(f"ALTER TABLE users ADD COLUMN theme_name TEXT NOT NULL DEFAULT '{DEFAULT_THEME}'")
        if "employee_id" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN employee_id INTEGER")

        connection.execute("UPDATE users SET is_active = COALESCE(is_active, 1)")
        connection.execute(
            """
            UPDATE users
            SET theme_name = CASE
                WHEN theme_name IN (?, ?, ?, ?) THEN theme_name
                ELSE ?
            END
            """,
            (*VALID_THEMES, DEFAULT_THEME),
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_employee_id ON users(employee_id) WHERE employee_id IS NOT NULL"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS user_permissions (user_id INTEGER NOT NULL, permission_key TEXT NOT NULL, PRIMARY KEY (user_id, permission_key), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)"
        )

        product_columns = {row["name"] for row in connection.execute("PRAGMA table_info(products)").fetchall()}
        if "supplier" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN supplier TEXT")
        if "cost_price" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0")
        connection.execute("UPDATE products SET supplier = COALESCE(supplier, '')")
        connection.execute("UPDATE products SET cost_price = COALESCE(cost_price, 0)")

        sales_columns = {row["name"] for row in connection.execute("PRAGMA table_info(sales)").fetchall()}
        if "cashier_name" not in sales_columns:
            connection.execute("ALTER TABLE sales ADD COLUMN cashier_name TEXT")
        if "store_name" not in sales_columns:
            connection.execute("ALTER TABLE sales ADD COLUMN store_name TEXT NOT NULL DEFAULT ''")
        if "currency_symbol" not in sales_columns:
            connection.execute(
                f"ALTER TABLE sales ADD COLUMN currency_symbol TEXT NOT NULL DEFAULT '{DEFAULT_CURRENCY_SYMBOL}'"
            )
        if "use_decimals" not in sales_columns:
            connection.execute(
                f"ALTER TABLE sales ADD COLUMN use_decimals INTEGER NOT NULL DEFAULT {1 if DEFAULT_USE_DECIMALS else 0}"
            )

        sale_item_columns = {row["name"] for row in connection.execute("PRAGMA table_info(sale_items)").fetchall()}
        if "product_name" not in sale_item_columns:
            connection.execute("ALTER TABLE sale_items ADD COLUMN product_name TEXT NOT NULL DEFAULT ''")
        if "unit_cost" not in sale_item_columns:
            connection.execute("ALTER TABLE sale_items ADD COLUMN unit_cost REAL NOT NULL DEFAULT 0")
        if "cost_total" not in sale_item_columns:
            connection.execute("ALTER TABLE sale_items ADD COLUMN cost_total REAL NOT NULL DEFAULT 0")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                supplier_name TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_cost REAL NOT NULL,
                total_cost REAL NOT NULL,
                payment_type TEXT NOT NULL CHECK(payment_type IN ('cash', 'credit')),
                amount_paid REAL NOT NULL DEFAULT 0,
                notes TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE RESTRICT,
                FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS supplier_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_id INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(purchase_id) REFERENCES stock_purchases(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        store_name = self._setting_value(connection, "store_name", STORE_NAME)
        currency_symbol = self._setting_value(connection, "currency_symbol", DEFAULT_CURRENCY_SYMBOL)
        use_decimals = "1" if self._setting_value(connection, "use_decimals", "1") not in {"0", "false", "False"} else "0"

        connection.execute("UPDATE sales SET store_name = COALESCE(NULLIF(store_name, ''), ?)", (store_name,))
        connection.execute(
            "UPDATE sales SET currency_symbol = COALESCE(NULLIF(currency_symbol, ''), ?)",
            (currency_symbol,),
        )
        connection.execute(
            "UPDATE sales SET use_decimals = COALESCE(use_decimals, ?)",
            (int(use_decimals),),
        )
        connection.execute(
            """
            UPDATE sales
            SET cashier_name = COALESCE(
                NULLIF(cashier_name, ''),
                (SELECT full_name FROM users WHERE users.id = sales.cashier_id),
                'System User'
            )
            """
        )
        connection.execute(
            """
            UPDATE sale_items
            SET product_name = COALESCE(
                NULLIF(product_name, ''),
                (SELECT name FROM products WHERE products.id = sale_items.product_id),
                'Unknown Product'
            )
            """
        )
        connection.execute(
            """
            UPDATE sale_items
            SET unit_cost = COALESCE(
                NULLIF(unit_cost, 0),
                (SELECT COALESCE(cost_price, 0) FROM products WHERE products.id = sale_items.product_id),
                0
            )
            """
        )
        connection.execute(
            "UPDATE sale_items SET cost_total = CASE WHEN cost_total > 0 THEN cost_total ELSE COALESCE(unit_cost, 0) * quantity END"
        )

    def _seed_defaults(self, connection: sqlite3.Connection) -> None:
        existing_admin = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()
        if existing_admin is None:
            connection.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, is_active, theme_name)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("admin", hash_password("admin123"), "Ssemujju Edris", "Administrator", 1, DEFAULT_THEME),
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET role = COALESCE(role, 'Administrator'),
                    is_active = COALESCE(is_active, 1),
                    theme_name = CASE
                        WHEN theme_name IN (?, ?, ?, ?) THEN theme_name
                        ELSE ?
                    END
                WHERE username = 'admin'
                """,
                (*VALID_THEMES, DEFAULT_THEME),
            )

        default_settings = (
            ("store_name", STORE_NAME),
            ("currency_symbol", DEFAULT_CURRENCY_SYMBOL),
            ("use_decimals", "1" if DEFAULT_USE_DECIMALS else "0"),
        )
        for key, value in default_settings:
            connection.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING",
                (key, value),
            )

        for name, description in DEFAULT_CATEGORIES:
            connection.execute(
                """
                INSERT INTO categories (name, description)
                VALUES (?, ?)
                ON CONFLICT(name) DO NOTHING
                """,
                (name, description),
            )

    def _setting_value(self, connection: sqlite3.Connection, key: str, default: str) -> str:
        row = connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
