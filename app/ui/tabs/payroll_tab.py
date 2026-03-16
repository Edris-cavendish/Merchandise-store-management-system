from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.widgets import ScrollablePage, make_labeled_entry


class PayrollTab(ScrollablePage):
    def __init__(self, parent, current_user: dict, payroll_service, settings_service) -> None:
        super().__init__(parent, padding=14)
        self.current_user = current_user
        self.payroll_service = payroll_service
        self.settings_service = settings_service

        self.body.columnconfigure(0, weight=1)

        start_date, end_date = self.payroll_service.month_bounds()
        self.start_date_var = tk.StringVar(value=start_date)
        self.end_date_var = tk.StringVar(value=end_date)
        self.employee_var = tk.StringVar(value="")
        self.pay_type_var = tk.StringVar(value="")
        self.period_var = tk.StringVar(value="")
        self.base_pay_var = tk.StringVar(value="")
        self.overtime_pay_var = tk.StringVar(value="")
        self.gross_pay_var = tk.StringVar(value="")
        self.hours_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        ttk.Label(self.body, text="My Pay Overview", style="Headline.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(
            self.body,
            text="View your payroll summary and recent attendance records used for this pay period.",
            style="MutedBg.TLabel",
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 14))

        self.info_frame = ttk.LabelFrame(self.body, text="Pay Summary", padding=18)
        self.info_frame.grid(row=2, column=0, sticky="ew")
        self.info_frame.columnconfigure(0, weight=1)
        self.info_frame.columnconfigure(1, weight=1)

        make_labeled_entry(self.info_frame, "📅 Period Start", self.start_date_var, 0, 0)
        make_labeled_entry(self.info_frame, "📅 Period End", self.end_date_var, 0, 1)
        ttk.Button(self.info_frame, text="Refresh Pay Summary", style="Primary.TButton", command=self.refresh).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(4, 14)
        )

        details = ttk.Frame(self.info_frame, style="Card.TFrame", padding=18)
        details.grid(row=3, column=0, columnspan=2, sticky="ew")
        details.columnconfigure(1, weight=1)

        rows = (
            ("Employee", self.employee_var, "CardTitle.TLabel"),
            ("Pay Type", self.pay_type_var, "CardTitle.TLabel"),
            ("Period", self.period_var, "CardTitle.TLabel"),
            ("Base Pay", self.base_pay_var, "CardTitle.TLabel"),
            ("Overtime Pay", self.overtime_pay_var, "CardTitle.TLabel"),
            ("Estimated Gross", self.gross_pay_var, "AccentValue.TLabel"),
            ("Hours", self.hours_var, "CardTitle.TLabel"),
            ("Status", self.status_var, "CardTitle.TLabel"),
        )
        for row_index, (label, variable, vstyle) in enumerate(rows):
            ttk.Label(details, text=label, style="CardTitle.TLabel").grid(row=row_index, column=0, sticky="w", pady=4)
            ttk.Label(details, textvariable=variable, style=vstyle, wraplength=520, justify="right").grid(
                row=row_index, column=1, sticky="e", pady=4
            )

        self.log_frame = ttk.LabelFrame(self.body, text="Recent Attendance Used For Pay", padding=16)
        self.log_frame.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        columns = ("date", "clock_in", "clock_out", "hours", "ot")
        self.attendance_tree = ttk.Treeview(self.log_frame, columns=columns, show="headings", height=12)
        for key, title, width in (
            ("date", "Date", 110),
            ("clock_in", "Clock In", 160),
            ("clock_out", "Clock Out", 160),
            ("hours", "Hours", 90),
            ("ot", "Overtime", 90),
        ):
            self.attendance_tree.heading(key, text=title)
            self.attendance_tree.column(key, width=width, anchor="center")
        self.attendance_tree.grid(row=0, column=0, sticky="nsew")
        log_y = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.attendance_tree.yview)
        log_y.grid(row=0, column=1, sticky="ns")
        log_x = ttk.Scrollbar(self.log_frame, orient="horizontal", command=self.attendance_tree.xview)
        log_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.attendance_tree.configure(yscrollcommand=log_y.set, xscrollcommand=log_x.set)

        self.refresh()

    def refresh(self) -> None:
        for item in self.attendance_tree.get_children():
            self.attendance_tree.delete(item)

        summary = self.payroll_service.summary_for_user(
            self.current_user,
            self.start_date_var.get().strip() or None,
            self.end_date_var.get().strip() or None,
        )
        if summary is None:
            self.employee_var.set("No linked employee profile")
            self.pay_type_var.set("Not available")
            self.period_var.set("No payroll access")
            self.base_pay_var.set("-")
            self.overtime_pay_var.set("-")
            self.gross_pay_var.set("-")
            self.hours_var.set("-")
            self.status_var.set("Ask an administrator to link this account to a staff record.")
            return

        currency_settings = self.settings_service.get_currency_settings()
        self.employee_var.set(summary["employee"]["full_name"])
        self.pay_type_var.set(summary["employee"]["pay_type"].title())
        self.period_var.set(f"{summary['period_start']} to {summary['period_end']}")
        self.base_pay_var.set(self.settings_service.format_money(summary["base_pay"], currency_settings))
        self.overtime_pay_var.set(self.settings_service.format_money(summary["overtime_pay"], currency_settings))
        self.gross_pay_var.set(self.settings_service.format_money(summary["gross_pay"], currency_settings))
        self.hours_var.set(f"Regular {summary['regular_hours']:.2f} | OT {summary['overtime_hours']:.2f}")
        self.status_var.set("Open shift running now" if summary["open_shift"] else "No open shift right now")

        for record in summary["recent_attendance"]:
            self.attendance_tree.insert(
                "",
                "end",
                values=(
                    record["attendance_date"],
                    record["clock_in"][:16],
                    record["clock_out"][:16] if record["clock_out"] else "Active",
                    f"{record['hours_worked']:.2f}",
                    f"{record['overtime_hours']:.2f}",
                ),
            )
