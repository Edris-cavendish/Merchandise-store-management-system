from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from app.ui.widgets import ScrollablePage, make_labeled_entry, apply_treeview_stripes


class StaffTab(ScrollablePage):
    def __init__(self, parent, employee_service, attendance_service, settings_service) -> None:
        super().__init__(parent, padding=14)
        self.employee_service = employee_service
        self.attendance_service = attendance_service
        self.settings_service = settings_service
        self.selected_employee_id: int | None = None

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Staff, Attendance & Payroll", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            self.body,
            text="Manage employees, clock attendance, and calculate payroll from one workspace.",
            style="MutedBg.TLabel",
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 14))

        self.main_panel = ttk.Frame(self.body, style="App.TFrame")
        self.main_panel.grid(row=2, column=0, sticky="nsew")
        self.main_panel.columnconfigure(0, weight=3)
        self.main_panel.columnconfigure(1, weight=2)
        self.main_panel.rowconfigure(0, weight=1)

        self._build_employee_grid()
        self._build_side_panel()
        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh()

    # ── Employee directory (left) ─────────────────────────────────────────────

    def _build_employee_grid(self) -> None:
        self.directory_frame = ttk.LabelFrame(self.main_panel, text="Employee Directory", padding=14)
        self.directory_frame.columnconfigure(0, weight=1)
        self.directory_frame.rowconfigure(0, weight=1)

        columns = ("code", "name", "role", "pay_type", "hourly", "monthly")
        self.employee_tree = ttk.Treeview(self.directory_frame, columns=columns, show="headings", height=18)
        for key, title, width in (
            ("code",     "Code",      110),
            ("name",     "Full Name", 220),
            ("role",     "Role",      140),
            ("pay_type", "Pay Type",  110),
            ("hourly",   "Hourly",    130),
            ("monthly",  "Monthly",   140),
        ):
            self.employee_tree.heading(key, text=title)
            self.employee_tree.column(key, width=width, anchor="center")
        self.employee_tree.grid(row=0, column=0, sticky="nsew")
        self.employee_tree.bind("<<TreeviewSelect>>", self._load_selected_employee)

        employee_y = ttk.Scrollbar(self.directory_frame, orient="vertical", command=self.employee_tree.yview)
        employee_y.grid(row=0, column=1, sticky="ns")
        employee_x = ttk.Scrollbar(self.directory_frame, orient="horizontal", command=self.employee_tree.xview)
        employee_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.employee_tree.configure(yscrollcommand=employee_y.set, xscrollcommand=employee_x.set)

    # ── Side panel (right) ────────────────────────────────────────────────────

    def _build_side_panel(self) -> None:
        self.side_panel = ttk.Frame(self.main_panel, style="App.TFrame")
        self.side_panel.rowconfigure(2, weight=1)
        self._build_employee_form(self.side_panel)
        self._build_attendance_tools(self.side_panel)
        self._build_attendance_log(self.side_panel)

    def _build_employee_form(self, parent) -> None:
        self.form = ttk.LabelFrame(parent, text="Employee Form", padding=16)
        self.form.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for index in range(2):
            self.form.columnconfigure(index, weight=1)

        self.code_var = tk.StringVar()
        self.employee_name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.role_var = tk.StringVar()
        self.pay_type_var = tk.StringVar(value="hourly")
        self.hourly_rate_var = tk.StringVar(value="0")
        self.monthly_salary_var = tk.StringVar(value="0")
        self.overtime_rate_var = tk.StringVar(value="0")
        self.active_var = tk.BooleanVar(value=True)
        self.payroll_start_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.payroll_end_var = tk.StringVar(value=date.today().isoformat())
        self.payroll_hint_var = tk.StringVar(value="Hourly staff can use salary calculation with attendance and overtime.")

        # Group 1: Identity
        ttk.Label(self.form, text="IDENTITY", style="Kicker.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        make_labeled_entry(self.form, "Employee Code", self.code_var, 1, 0)
        make_labeled_entry(self.form, "Full Name", self.employee_name_var, 1, 1)
        make_labeled_entry(self.form, "Phone", self.phone_var, 3, 0)
        make_labeled_entry(self.form, "Role / Position", self.role_var, 3, 1)

        # Group 2: Compensation
        ttk.Separator(self.form, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        ttk.Label(self.form, text="COMPENSATION", style="Kicker.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        ttk.Label(self.form, text="Pay Type", style="FormLabel.TLabel").grid(row=7, column=0, sticky="w", pady=(0, 3))
        self.pay_type_box = ttk.Combobox(
            self.form, textvariable=self.pay_type_var, values=("hourly", "fixed"), state="readonly"
        )
        self.pay_type_box.grid(row=8, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        self.pay_type_box.bind("<<ComboboxSelected>>", self._update_payroll_controls)
        self.hourly_rate_entry = make_labeled_entry(self.form, "Hourly Rate", self.hourly_rate_var, 7, 1)
        self.monthly_salary_entry = make_labeled_entry(self.form, "Monthly Salary", self.monthly_salary_var, 9, 0)
        self.overtime_rate_entry = make_labeled_entry(self.form, "Overtime Rate", self.overtime_rate_var, 9, 1)
        ttk.Checkbutton(self.form, text="Employee is active", variable=self.active_var).grid(
            row=11, column=0, sticky="w", pady=(4, 10)
        )

        # Group 3: Actions
        ttk.Separator(self.form, orient="horizontal").grid(row=12, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        action_row = ttk.Frame(self.form, style="Surface.TFrame")
        action_row.grid(row=13, column=0, columnspan=2, sticky="ew")
        action_row.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(action_row, text="Clear", style="Secondary.TButton", command=self._reset_form).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(action_row, text="Delete", style="Secondary.TButton", command=self._delete_employee).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(action_row, text="Save Staff", style="Primary.TButton", command=self._save_employee).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

        # Group 4: Payroll calculation
        ttk.Separator(self.form, orient="horizontal").grid(row=14, column=0, columnspan=2, sticky="ew", pady=(10, 10))
        ttk.Label(self.form, text="PAYROLL CALCULATION", style="Kicker.TLabel").grid(
            row=15, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        payroll = ttk.Frame(self.form, style="Surface.TFrame")
        payroll.grid(row=16, column=0, columnspan=2, sticky="ew")
        payroll.columnconfigure((0, 1), weight=1)
        self.payroll_start_entry = make_labeled_entry(payroll, "📅 Period Start", self.payroll_start_var, 0, 0)
        self.payroll_end_entry = make_labeled_entry(payroll, "📅 Period End", self.payroll_end_var, 0, 1)
        ttk.Label(
            payroll,
            textvariable=self.payroll_hint_var,
            style="Muted.TLabel",
            wraplength=380,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.calculate_salary_button = ttk.Button(
            payroll, text="Calculate Salary", style="Secondary.TButton", command=self._calculate_salary
        )
        self.calculate_salary_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.overtime_rate_var.trace_add("write", self._handle_overtime_change)
        self._update_payroll_controls()

    def _build_attendance_tools(self, parent) -> None:
        self.tools = ttk.LabelFrame(parent, text="Attendance Controls", padding=14)
        self.tools.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(
            self.tools,
            text="Choose a staff member from the directory, then clock them in or out.",
            style="Muted.TLabel",
            wraplength=360,
        ).pack(anchor="w")
        actions = ttk.Frame(self.tools, style="Surface.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="  Clock In  ", style="Primary.TButton", command=self._clock_in).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(actions, text="  Clock Out  ", style="Secondary.TButton", command=self._clock_out).pack(
            side="left", fill="x", expand=True
        )

    def _build_attendance_log(self, parent) -> None:
        self.log_frame = ttk.LabelFrame(parent, text="Recent Attendance Log", padding=14)
        self.log_frame.grid(row=2, column=0, sticky="nsew")
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        columns = ("code", "name", "date", "in", "out", "hours", "ot")
        self.attendance_tree = ttk.Treeview(self.log_frame, columns=columns, show="headings", height=14)
        for key, title, width in (
            ("code",  "Code",      90),
            ("name",  "Name",     150),
            ("date",  "Date",      90),
            ("in",    "Clock In", 140),
            ("out",   "Clock Out",140),
            ("hours", "Hours",     70),
            ("ot",    "OT",        70),
        ):
            self.attendance_tree.heading(key, text=title)
            self.attendance_tree.column(key, width=width, anchor="center")
        self.attendance_tree.grid(row=0, column=0, sticky="nsew")
        attendance_y = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.attendance_tree.yview)
        attendance_y.grid(row=0, column=1, sticky="ns")
        attendance_x = ttk.Scrollbar(self.log_frame, orient="horizontal", command=self.attendance_tree.xview)
        attendance_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.attendance_tree.configure(yscrollcommand=attendance_y.set, xscrollcommand=attendance_x.set)
        self.attendance_tree.tag_configure("active_shift", foreground="#10B981")

    # ── Payroll controls ──────────────────────────────────────────────────────

    def _handle_overtime_change(self, *_args) -> None:
        self._update_payroll_controls()

    def _set_entry_state(self, entry: ttk.Entry, enabled: bool) -> None:
        if enabled:
            entry.state(["!disabled"])
        else:
            entry.state(["disabled"])

    def _update_payroll_controls(self, _event=None) -> None:
        pay_type = self.pay_type_var.get() or "hourly"
        try:
            overtime_rate = float(self.overtime_rate_var.get() or 0)
        except ValueError:
            overtime_rate = 0.0

        hourly_mode = pay_type == "hourly"
        self._set_entry_state(self.hourly_rate_entry, hourly_mode)
        self._set_entry_state(self.monthly_salary_entry, not hourly_mode)

        can_calculate = hourly_mode or overtime_rate > 0
        if can_calculate:
            self.calculate_salary_button.state(["!disabled"])
            self._set_entry_state(self.payroll_start_entry, True)
            self._set_entry_state(self.payroll_end_entry, True)
        else:
            self.calculate_salary_button.state(["disabled"])
            self._set_entry_state(self.payroll_start_entry, False)
            self._set_entry_state(self.payroll_end_entry, False)

        if hourly_mode:
            self.payroll_hint_var.set("Hourly staff can use salary calculation with attendance and overtime.")
        elif overtime_rate > 0:
            self.payroll_hint_var.set("Fixed salary is used as the base pay. Overtime rate enables calculation.")
        else:
            self.payroll_hint_var.set("Fixed salary staff do not need calculation unless an overtime rate is set.")

    # ── Layout ────────────────────────────────────────────────────────────────

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        self.directory_frame.grid_forget()
        self.side_panel.grid_forget()
        if width >= 1480:
            self.main_panel.columnconfigure(0, weight=3)
            self.main_panel.columnconfigure(1, weight=2)
            self.directory_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            self.side_panel.grid(row=0, column=1, sticky="nsew")
        else:
            self.main_panel.columnconfigure(0, weight=1)
            self.main_panel.columnconfigure(1, weight=0)
            self.directory_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
            self.side_panel.grid(row=1, column=0, sticky="nsew")
        self._sync_scrollregion()

    # ── Palette ───────────────────────────────────────────────────────────────

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        apply_treeview_stripes(self.employee_tree, palette)
        apply_treeview_stripes(self.attendance_tree, palette)
        self.attendance_tree.tag_configure("active_shift", foreground=palette["success"])

    # ── CRUD helpers ──────────────────────────────────────────────────────────

    def _validate_employee_payload(self) -> dict:
        if not self.code_var.get().strip() or not self.employee_name_var.get().strip() or not self.role_var.get().strip():
            raise ValueError("Employee code, full name, and role are required.")
        try:
            hourly_rate = float(self.hourly_rate_var.get() or 0)
            monthly_salary = float(self.monthly_salary_var.get() or 0)
            overtime_rate = float(self.overtime_rate_var.get() or 0)
        except ValueError as exc:
            raise ValueError("Pay values must be valid numbers.") from exc
        pay_type = self.pay_type_var.get()
        if pay_type == "hourly":
            monthly_salary = 0.0
        else:
            hourly_rate = 0.0
        return {
            "employee_code": self.code_var.get().strip(),
            "full_name": self.employee_name_var.get().strip(),
            "phone": self.phone_var.get().strip(),
            "role": self.role_var.get().strip(),
            "pay_type": pay_type,
            "hourly_rate": hourly_rate,
            "monthly_salary": monthly_salary,
            "overtime_rate": overtime_rate,
            "is_active": self.active_var.get(),
        }

    def _save_employee(self) -> None:
        try:
            payload = self._validate_employee_payload()
            if self.selected_employee_id is None:
                self.employee_service.create_employee(payload)
                messagebox.showinfo("Saved", "Employee created successfully.", parent=self)
            else:
                self.employee_service.update_employee(self.selected_employee_id, payload)
                messagebox.showinfo("Updated", "Employee updated successfully.", parent=self)
            self.refresh()
            self._reset_form()
        except Exception as exc:
            messagebox.showerror("Employee Error", str(exc), parent=self)

    def _delete_employee(self) -> None:
        if self.selected_employee_id is None:
            messagebox.showwarning("Select Employee", "Choose an employee to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected employee?", parent=self):
            return
        try:
            self.employee_service.delete_employee(self.selected_employee_id)
            self.refresh()
            self._reset_form()
        except Exception as exc:
            messagebox.showerror("Delete Error", str(exc), parent=self)

    def _clock_in(self) -> None:
        if self.selected_employee_id is None:
            messagebox.showwarning("Select Employee", "Choose an employee first.", parent=self)
            return
        try:
            self.attendance_service.clock_in(self.selected_employee_id)
            messagebox.showinfo("Attendance", "Clock-in recorded successfully.", parent=self)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Clock-in Error", str(exc), parent=self)

    def _clock_out(self) -> None:
        if self.selected_employee_id is None:
            messagebox.showwarning("Select Employee", "Choose an employee first.", parent=self)
            return
        try:
            self.attendance_service.clock_out(self.selected_employee_id)
            messagebox.showinfo("Attendance", "Clock-out recorded successfully.", parent=self)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Clock-out Error", str(exc), parent=self)

    def _calculate_salary(self) -> None:
        if self.selected_employee_id is None:
            messagebox.showwarning("Select Employee", "Choose an employee first.", parent=self)
            return
        try:
            employee = self.employee_service.get_employee(self.selected_employee_id)
            if employee["pay_type"] == "fixed" and float(employee.get("overtime_rate") or 0) <= 0:
                messagebox.showinfo("Fixed Salary", "Fixed salary staff do not need salary calculation unless an overtime rate is set.", parent=self)
                return
            summary = self.employee_service.calculate_salary(
                self.selected_employee_id,
                self.payroll_start_var.get().strip(),
                self.payroll_end_var.get().strip(),
            )
            currency_settings = self.settings_service.get_currency_settings()
            messagebox.showinfo(
                "Salary Summary",
                (
                    f"Employee: {summary['employee']['full_name']}\n"
                    f"Regular Hours: {summary['regular_hours']:.2f}\n"
                    f"Overtime Hours: {summary['overtime_hours']:.2f}\n"
                    f"Base Pay: {self.settings_service.format_money(summary['base_pay'], currency_settings)}\n"
                    f"Overtime Pay: {self.settings_service.format_money(summary['overtime_pay'], currency_settings)}\n"
                    f"Gross Pay: {self.settings_service.format_money(summary['gross_pay'], currency_settings)}"
                ),
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Payroll Error", str(exc), parent=self)

    def _load_selected_employee(self, _event=None) -> None:
        selection = self.employee_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        employee_id = int(self.employee_tree.item(item_id, "text"))
        employee = next((row for row in self.employee_service.list_employees() if row["id"] == employee_id), None)
        if employee is None:
            return
        self.selected_employee_id = employee_id
        self.code_var.set(employee["employee_code"])
        self.employee_name_var.set(employee["full_name"])
        self.phone_var.set(employee.get("phone") or "")
        self.role_var.set(employee["role"])
        self.pay_type_var.set(employee["pay_type"])
        self.hourly_rate_var.set(str(employee["hourly_rate"]))
        self.monthly_salary_var.set(str(employee["monthly_salary"]))
        self.overtime_rate_var.set(str(employee["overtime_rate"]))
        self.active_var.set(bool(employee["is_active"]))
        self._update_payroll_controls()

    def _reset_form(self) -> None:
        self.selected_employee_id = None
        self.code_var.set("")
        self.employee_name_var.set("")
        self.phone_var.set("")
        self.role_var.set("")
        self.pay_type_var.set("hourly")
        self.hourly_rate_var.set("0")
        self.monthly_salary_var.set("0")
        self.overtime_rate_var.set("0")
        self.active_var.set(True)
        self._update_payroll_controls()

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        for item in self.employee_tree.get_children():
            self.employee_tree.delete(item)
        for index, employee in enumerate(self.employee_service.list_employees()):
            tag = "even" if index % 2 == 0 else "odd"
            self.employee_tree.insert(
                "",
                "end",
                text=str(employee["id"]),
                values=(
                    employee["employee_code"],
                    employee["full_name"],
                    employee["role"],
                    employee["pay_type"],
                    self.settings_service.format_money(employee["hourly_rate"], currency_settings),
                    self.settings_service.format_money(employee["monthly_salary"], currency_settings),
                ),
                tags=(tag,),
            )

        for item in self.attendance_tree.get_children():
            self.attendance_tree.delete(item)
        for index, record in enumerate(self.attendance_service.list_attendance()):
            is_active = not record["clock_out"]
            tags = ("active_shift",) if is_active else ("even" if index % 2 == 0 else "odd",)
            self.attendance_tree.insert(
                "",
                "end",
                values=(
                    record["employee_code"],
                    record["full_name"],
                    record["attendance_date"],
                    record["clock_in"][:16],
                    "● Active" if is_active else record["clock_out"][:16],
                    f"{record['hours_worked']:.2f}",
                    f"{record['overtime_hours']:.2f}",
                ),
                tags=tags,
            )
