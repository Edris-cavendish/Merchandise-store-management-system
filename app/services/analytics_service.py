from __future__ import annotations

from datetime import date, timedelta

from app.db.database import DatabaseManager
from app.services.expenses_service import ExpensesService
from app.services.inventory_service import InventoryService


class AnalyticsService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.expenses_service = ExpensesService(database)
        self.inventory_service = InventoryService(database)

    def summary_cards(self) -> dict:
        revenue_today = self._sales_total_for_day(date.today().isoformat())
        cogs_today = self._cogs_total_for_day(date.today().isoformat())
        expenses_today = self.expenses_service.expenses_today_total()
        return {
            "revenue_today": revenue_today,
            "cogs_today": cogs_today,
            "expenses_today": expenses_today,
            "net_profit_today": round(revenue_today - cogs_today - expenses_today, 2),
            "outstanding_supplier": self.inventory_service.outstanding_supplier_balance(),
            "inventory_value": self.inventory_service.inventory_value(),
        }

    def employee_performance(self, limit: int = 6) -> list[dict]:
        rows = self.database.fetch_all(
            f"""
            SELECT
                COALESCE(cashier_name, 'System User') AS label,
                COUNT(*) AS receipt_count,
                COALESCE(SUM(total_amount), 0) AS total_amount
            FROM sales
            GROUP BY COALESCE(cashier_name, 'System User')
            ORDER BY total_amount DESC, receipt_count DESC
            LIMIT {int(limit)}
            """
        )
        return [dict(row) for row in rows]

    def product_performance(self, limit: int = 6) -> list[dict]:
        rows = self.database.fetch_all(
            f"""
            SELECT
                product_name AS label,
                COALESCE(SUM(quantity), 0) AS quantity_sold,
                COALESCE(SUM(line_total), 0) AS revenue,
                COALESCE(SUM(cost_total), 0) AS cost_total
            FROM sale_items
            GROUP BY product_name
            ORDER BY revenue DESC, quantity_sold DESC
            LIMIT {int(limit)}
            """
        )
        return [dict(row) for row in rows]

    def daily_financials(self, days: int = 7) -> list[dict]:
        entries: list[dict] = []
        start = date.today() - timedelta(days=days - 1)
        for index in range(days):
            day = start + timedelta(days=index)
            day_key = day.isoformat()
            revenue = self._sales_total_for_day(day_key)
            cogs = self._cogs_total_for_day(day_key)
            expenses = self.expenses_service.expenses_total(day_key, day_key)
            entries.append(
                {
                    "label": day.strftime("%a"),
                    "date": day_key,
                    "revenue": revenue,
                    "expenses": expenses,
                    "net_profit": round(revenue - cogs - expenses, 2),
                }
            )
        return entries

    def report_snapshot(self, start_date: str | None = None, end_date: str | None = None) -> dict:
        if start_date is None:
            today = date.today()
            start_date = today.replace(day=1).isoformat()
        if end_date is None:
            end_date = date.today().isoformat()

        revenue = self.sales_total(start_date, end_date)
        cogs = self.cogs_total(start_date, end_date)
        expenses = self.expenses_service.expenses_total(start_date, end_date)
        top_employee = self.employee_performance(limit=1)
        top_product = self.product_performance(limit=1)
        outstanding = self.inventory_service.outstanding_supplier_balance()
        return {
            "start_date": start_date,
            "end_date": end_date,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": round(revenue - cogs, 2),
            "expenses": expenses,
            "net_profit": round(revenue - cogs - expenses, 2),
            "outstanding_supplier": outstanding,
            "top_employee": top_employee[0] if top_employee else None,
            "top_product": top_product[0] if top_product else None,
        }

    def report_text(self, start_date: str | None = None, end_date: str | None = None) -> str:
        snapshot = self.report_snapshot(start_date, end_date)
        top_employee = snapshot["top_employee"]
        top_product = snapshot["top_product"]
        lines = [
            "Admin Profit & Performance Report",
            "=" * 60,
            f"Period: {snapshot['start_date']} to {snapshot['end_date']}",
            f"Revenue: {snapshot['revenue']:.2f}",
            f"Cost of Goods Sold: {snapshot['cogs']:.2f}",
            f"Gross Profit: {snapshot['gross_profit']:.2f}",
            f"Operating Expenses: {snapshot['expenses']:.2f}",
            f"Net Profit: {snapshot['net_profit']:.2f}",
            f"Outstanding Supplier Payables: {snapshot['outstanding_supplier']:.2f}",
            "-" * 60,
            "Top Employee:",
            (
                f"{top_employee['label']} | Receipts: {int(top_employee['receipt_count'])} | Sales: {float(top_employee['total_amount']):.2f}"
                if top_employee
                else "No employee sales data yet."
            ),
            "Top Product:",
            (
                f"{top_product['label']} | Qty Sold: {int(top_product['quantity_sold'])} | Revenue: {float(top_product['revenue']):.2f}"
                if top_product
                else "No product sales data yet."
            ),
        ]
        return "\n".join(lines)

    def sales_total(self, start_date: str, end_date: str) -> float:
        row = self.database.fetch_one(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM sales
            WHERE date(created_at, 'localtime') BETWEEN ? AND ?
            """,
            (start_date, end_date),
        )
        return round(float(row["total"]) if row else 0, 2)

    def cogs_total(self, start_date: str, end_date: str) -> float:
        row = self.database.fetch_one(
            """
            SELECT COALESCE(SUM(si.cost_total), 0) AS total
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            WHERE date(s.created_at, 'localtime') BETWEEN ? AND ?
            """,
            (start_date, end_date),
        )
        return round(float(row["total"]) if row else 0, 2)

    def _sales_total_for_day(self, date_value: str) -> float:
        return self.sales_total(date_value, date_value)

    def _cogs_total_for_day(self, date_value: str) -> float:
        return self.cogs_total(date_value, date_value)
