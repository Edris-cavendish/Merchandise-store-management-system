from __future__ import annotations

from datetime import date

from app.db.database import DatabaseManager


class ExpensesService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def list_expenses(self, limit: int = 250) -> list[dict]:
        rows = self.database.fetch_all(
            f"""
            SELECT id, expense_date, category, title, amount, notes, created_at
            FROM expenses
            ORDER BY expense_date DESC, id DESC
            LIMIT {int(limit)}
            """
        )
        return [dict(row) for row in rows]

    def create_expense(self, payload: dict, actor_user_id: int | None = None) -> int:
        expense_date = payload.get("expense_date", "").strip() or date.today().isoformat()
        category = payload.get("category", "").strip()
        title = payload.get("title", "").strip()
        amount = float(payload.get("amount", 0))
        notes = payload.get("notes", "").strip()

        if not category or not title:
            raise ValueError("Expense category and title are required.")
        if amount <= 0:
            raise ValueError("Expense amount must be greater than zero.")

        return self.database.execute(
            """
            INSERT INTO expenses (expense_date, category, title, amount, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (expense_date, category, title, amount, notes, actor_user_id),
        )

    def delete_expense(self, expense_id: int) -> None:
        self.database.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))

    def expenses_total(self, start_date: str | None = None, end_date: str | None = None) -> float:
        query = "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses"
        params: list[str] = []
        clauses: list[str] = []
        if start_date:
            clauses.append("expense_date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("expense_date <= ?")
            params.append(end_date)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        row = self.database.fetch_one(query, tuple(params))
        return round(float(row["total"]) if row else 0, 2)

    def expenses_today_total(self) -> float:
        row = self.database.fetch_one(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE date(expense_date, 'localtime') = date('now', 'localtime')
            """
        )
        return round(float(row["total"]) if row else 0, 2)
