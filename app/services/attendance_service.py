from __future__ import annotations

from datetime import datetime

from app.config import STANDARD_SHIFT_HOURS
from app.db.database import DatabaseManager


class AttendanceService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def list_attendance(self, limit: int = 50) -> list[dict]:
        rows = self.database.fetch_all(
            f"""
            SELECT
                attendance.id,
                employees.full_name,
                employees.employee_code,
                attendance.employee_id,
                attendance.attendance_date,
                attendance.clock_in,
                attendance.clock_out,
                attendance.hours_worked,
                attendance.overtime_hours,
                attendance.notes
            FROM attendance
            JOIN employees ON employees.id = attendance.employee_id
            ORDER BY attendance.id DESC
            LIMIT {int(limit)}
            """
        )
        return [dict(row) for row in rows]

    def list_attendance_for_employee(self, employee_id: int, limit: int = 20) -> list[dict]:
        rows = self.database.fetch_all(
            f"""
            SELECT
                attendance.id,
                employees.full_name,
                employees.employee_code,
                attendance.employee_id,
                attendance.attendance_date,
                attendance.clock_in,
                attendance.clock_out,
                attendance.hours_worked,
                attendance.overtime_hours,
                attendance.notes
            FROM attendance
            JOIN employees ON employees.id = attendance.employee_id
            WHERE attendance.employee_id = ?
            ORDER BY attendance.id DESC
            LIMIT {int(limit)}
            """,
            (employee_id,),
        )
        return [dict(row) for row in rows]

    def get_open_shift(self, employee_id: int) -> dict | None:
        row = self.database.fetch_one(
            """
            SELECT *
            FROM attendance
            WHERE employee_id = ? AND clock_out IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (employee_id,),
        )
        return dict(row) if row else None

    def clock_in(self, employee_id: int, notes: str = "") -> int:
        if self.get_open_shift(employee_id) is not None:
            raise ValueError("This employee already has an open attendance session.")

        now = datetime.now()
        return self.database.execute(
            """
            INSERT INTO attendance (employee_id, attendance_date, clock_in, notes)
            VALUES (?, ?, ?, ?)
            """,
            (employee_id, now.strftime("%Y-%m-%d"), now.isoformat(timespec="seconds"), notes.strip()),
        )

    def clock_out(self, employee_id: int) -> None:
        session = self.get_open_shift(employee_id)
        if session is None:
            raise ValueError("No open attendance session found for this employee.")

        now = datetime.now()
        clock_in = datetime.fromisoformat(session["clock_in"])
        hours_worked = round((now - clock_in).total_seconds() / 3600, 2)
        overtime_hours = round(max(hours_worked - STANDARD_SHIFT_HOURS, 0), 2)

        self.database.execute(
            """
            UPDATE attendance
            SET clock_out = ?, hours_worked = ?, overtime_hours = ?
            WHERE id = ?
            """,
            (now.isoformat(timespec="seconds"), hours_worked, overtime_hours, session["id"]),
        )

    def present_today_count(self) -> int:
        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM attendance
            WHERE attendance_date = date('now', 'localtime') AND clock_out IS NULL
            """
        )
        return int(row["total"]) if row else 0
