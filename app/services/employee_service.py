from __future__ import annotations

from datetime import datetime

from app.config import OVERTIME_MULTIPLIER, STANDARD_MONTHLY_HOURS
from app.db.database import DatabaseManager


class EmployeeService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def list_employees(self) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT *
            FROM employees
            ORDER BY full_name
            """
        )
        return [dict(row) for row in rows]

    def get_employee(self, employee_id: int) -> dict:
        row = self.database.fetch_one("SELECT * FROM employees WHERE id = ?", (employee_id,))
        if row is None:
            raise ValueError("Employee not found.")
        return dict(row)

    def create_employee(self, payload: dict) -> int:
        return self.database.execute(
            """
            INSERT INTO employees (
                employee_code, full_name, phone, role, pay_type,
                hourly_rate, monthly_salary, overtime_rate, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["employee_code"],
                payload["full_name"],
                payload.get("phone", ""),
                payload["role"],
                payload["pay_type"],
                payload.get("hourly_rate", 0.0),
                payload.get("monthly_salary", 0.0),
                payload.get("overtime_rate", 0.0),
                1 if payload.get("is_active", True) else 0,
            ),
        )

    def update_employee(self, employee_id: int, payload: dict) -> None:
        self.database.execute(
            """
            UPDATE employees
            SET employee_code = ?, full_name = ?, phone = ?, role = ?, pay_type = ?,
                hourly_rate = ?, monthly_salary = ?, overtime_rate = ?, is_active = ?
            WHERE id = ?
            """,
            (
                payload["employee_code"],
                payload["full_name"],
                payload.get("phone", ""),
                payload["role"],
                payload["pay_type"],
                payload.get("hourly_rate", 0.0),
                payload.get("monthly_salary", 0.0),
                payload.get("overtime_rate", 0.0),
                1 if payload.get("is_active", True) else 0,
                employee_id,
            ),
        )
        self.database.execute(
            "UPDATE users SET full_name = ? WHERE employee_id = ?",
            (payload["full_name"], employee_id),
        )

    def delete_employee(self, employee_id: int) -> None:
        self.database.execute("UPDATE users SET employee_id = NULL WHERE employee_id = ?", (employee_id,))
        self.database.execute("DELETE FROM employees WHERE id = ?", (employee_id,))

    def calculate_salary(self, employee_id: int, start_date: str, end_date: str) -> dict:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Payroll dates must use the YYYY-MM-DD format.") from exc
        if start_dt > end_dt:
            raise ValueError("Payroll start date cannot be later than payroll end date.")

        employee = self.get_employee(employee_id)
        hours_row = self.database.fetch_one(
            """
            SELECT
                COALESCE(SUM(hours_worked), 0) AS total_hours,
                COALESCE(SUM(overtime_hours), 0) AS overtime_hours
            FROM attendance
            WHERE employee_id = ? AND attendance_date BETWEEN ? AND ?
            """,
            (employee_id, start_date, end_date),
        )

        total_hours = float(hours_row["total_hours"])
        overtime_hours = float(hours_row["overtime_hours"])
        regular_hours = max(total_hours - overtime_hours, 0)

        if employee["pay_type"] == "hourly":
            base_pay = regular_hours * float(employee["hourly_rate"])
            overtime_rate = float(employee["overtime_rate"] or employee["hourly_rate"] * OVERTIME_MULTIPLIER)
            overtime_pay = overtime_hours * overtime_rate
        else:
            base_pay = float(employee["monthly_salary"])
            overtime_rate = float(employee["overtime_rate"] or 0)
            overtime_pay = overtime_hours * overtime_rate if overtime_rate > 0 else 0.0

        return {
            "employee": employee,
            "regular_hours": round(regular_hours, 2),
            "overtime_hours": round(overtime_hours, 2),
            "base_pay": round(base_pay, 2),
            "overtime_pay": round(overtime_pay, 2),
            "gross_pay": round(base_pay + overtime_pay, 2),
            "overtime_rate": round(overtime_rate, 2),
            "period_start": start_date,
            "period_end": end_date,
        }

    def derived_hourly_rate(self, employee: dict) -> float:
        if employee["pay_type"] == "hourly":
            return float(employee["hourly_rate"])
        monthly_salary = float(employee["monthly_salary"])
        return monthly_salary / STANDARD_MONTHLY_HOURS if STANDARD_MONTHLY_HOURS else 0.0
