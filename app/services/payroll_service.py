from __future__ import annotations

from datetime import date

from app.db.database import DatabaseManager
from app.services.attendance_service import AttendanceService
from app.services.employee_service import EmployeeService


class PayrollService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.employee_service = EmployeeService(database)
        self.attendance_service = AttendanceService(database)

    def month_bounds(self) -> tuple[str, str]:
        today = date.today()
        return today.replace(day=1).isoformat(), today.isoformat()

    def summary_for_user(self, user: dict, start_date: str | None = None, end_date: str | None = None) -> dict | None:
        employee_id = user.get("employee_id")
        if not employee_id:
            return None

        if not start_date or not end_date:
            default_start, default_end = self.month_bounds()
            start_date = start_date or default_start
            end_date = end_date or default_end

        summary = self.employee_service.calculate_salary(int(employee_id), start_date, end_date)
        summary["recent_attendance"] = self.attendance_service.list_attendance_for_employee(int(employee_id), limit=10)
        summary["open_shift"] = self.attendance_service.get_open_shift(int(employee_id)) is not None
        return summary
