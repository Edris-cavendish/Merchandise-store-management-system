from __future__ import annotations

from app.db.database import DatabaseManager
from app.services.attendance_service import AttendanceService
from app.services.expenses_service import ExpensesService
from app.services.inventory_service import InventoryService
from app.services.sales_service import SalesService


class DashboardService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.attendance_service = AttendanceService(database)
        self.inventory_service = InventoryService(database)
        self.sales_service = SalesService(database)
        self.expenses_service = ExpensesService(database)

    def stats(self, current_user: dict) -> dict:
        if current_user.get("role") == "Administrator":
            return self._admin_stats()
        return self._personal_stats(int(current_user["id"]))

    def _admin_stats(self) -> dict:
        employees_row = self.database.fetch_one("SELECT COUNT(*) AS total FROM employees WHERE is_active = 1")
        products_row = self.database.fetch_one("SELECT COUNT(*) AS total FROM products")
        sales_today = self.sales_service.sales_today_total()
        expenses_today = self.expenses_service.expenses_today_total()
        cogs_today_row = self.database.fetch_one(
            """
            SELECT COALESCE(SUM(si.cost_total), 0) AS total
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            WHERE date(s.created_at, 'localtime') = date('now', 'localtime')
            """
        )
        cogs_today = round(float(cogs_today_row["total"]) if cogs_today_row else 0, 2)
        return {
            "mode": "admin",
            "employees": int(employees_row["total"]) if employees_row else 0,
            "products": int(products_row["total"]) if products_row else 0,
            "present_today": self.attendance_service.present_today_count(),
            "sales_today": sales_today,
            "expenses_today": expenses_today,
            "profit_today": round(sales_today - cogs_today - expenses_today, 2),
            "inventory_value": self.inventory_service.inventory_value(),
            "low_stock": len(self.inventory_service.low_stock_products()),
            "recent_sales": self.sales_service.recent_sales(),
            "recent_attendance": self.attendance_service.list_attendance(limit=8),
            "recent_products": self.inventory_service.recent_products(limit=8),
        }

    def _personal_stats(self, user_id: int) -> dict:
        sales_today = self.sales_service.sales_today_total(cashier_id=user_id)
        receipts_today = self.sales_service.sales_count_today(cashier_id=user_id)
        recent_sales = self.sales_service.recent_sales(limit=8, cashier_id=user_id)
        return {
            "mode": "personal",
            "my_receipts_today": receipts_today,
            "my_sales_today": sales_today,
            "new_products": self.inventory_service.recent_products_count(days=7),
            "product_updates": self.inventory_service.recent_products(limit=8),
            "recent_sales": recent_sales,
            "recent_attendance": self.attendance_service.list_attendance(limit=8),
        }
