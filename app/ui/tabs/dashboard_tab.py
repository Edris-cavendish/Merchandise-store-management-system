from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.services.access_control import has_permission
from app.ui.widgets import ScrollablePage, StatCard


class DashboardTab(ScrollablePage):
    def __init__(
        self,
        parent,
        dashboard_service,
        inventory_service,
        attendance_service,
        payroll_service,
        settings_service,
        current_user: dict,
    ) -> None:
        super().__init__(parent, padding=6)
        self.dashboard_service = dashboard_service
        self.inventory_service = inventory_service
        self.attendance_service = attendance_service
        self.payroll_service = payroll_service
        self.settings_service = settings_service
        self.current_user = current_user
        self.is_admin = current_user.get("role") == "Administrator"

        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(3, weight=1)

        title = "Operations Dashboard" if self.is_admin else "My Work Dashboard"
        subtitle = (
            "Track the supermarket at a glance with staff, stock, sales, expenses, and performance updates."
            if self.is_admin
            else "See your own sales work, receipt activity, product updates, and your payment snapshot in one place."
        )

        ttk.Label(self.body, text=title, style="Headline.TLabel").grid(row=0, column=0, sticky="w", pady=(4, 8))
        ttk.Label(
            self.body,
            text=subtitle,
            style="Muted.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

        self.cards_frame = ttk.Frame(self.body, style="App.TFrame")
        self.cards_frame.grid(row=2, column=0, sticky="ew")

        if self.is_admin:
            self.cards = [
                StatCard(self.cards_frame, "Active Staff", "0", "Ready for today's shifts"),
                StatCard(self.cards_frame, "Sales Today", "0", "Live revenue snapshot"),
                StatCard(self.cards_frame, "Expenses Today", "0", "Operating spending so far"),
                StatCard(self.cards_frame, "Profit Today", "0", "Revenue minus stock cost and expenses"),
                StatCard(self.cards_frame, "Inventory Value", "0", "Current asset value"),
                StatCard(self.cards_frame, "Low Stock", "0", "Products that need restocking"),
            ]
        else:
            self.cards = [
                StatCard(self.cards_frame, "My Receipts Today", "0", "Receipts created by your account today"),
                StatCard(self.cards_frame, "My Sales Today", "0", "Your sales total for today"),
                StatCard(self.cards_frame, "New Products", "0", "Products added in the last 7 days"),
                StatCard(self.cards_frame, "Recent Sales", "0", "Your latest saved sales activity"),
            ]

        self.personal_pay_frame = None
        if has_permission(self.current_user, "view_payroll"):
            self.personal_pay_frame = ttk.LabelFrame(self.body, text="My Payment Snapshot", padding=16)
            self.personal_pay_frame.columnconfigure(0, weight=1)
            self.personal_pay_title_var = tk.StringVar(value="Current payroll snapshot")
            self.personal_pay_value_var = tk.StringVar(value="Payroll information will appear here.")
            ttk.Label(self.personal_pay_frame, textvariable=self.personal_pay_title_var, style="Section.TLabel").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(
                self.personal_pay_frame,
                textvariable=self.personal_pay_value_var,
                style="Muted.TLabel",
                wraplength=980,
                justify="left",
            ).grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.lower = ttk.Frame(self.body, style="App.TFrame")
        self.lower.grid(row=4, column=0, sticky="nsew", pady=(18, 0))

        if self.is_admin:
            self._build_admin_lower()
        else:
            self._build_personal_lower()

        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)

    def _build_admin_lower(self) -> None:
        self.low_stock_frame = ttk.LabelFrame(self.lower, text="Low Stock Alerts", padding=16)
        self.low_stock_frame.columnconfigure(0, weight=1)
        self.low_stock_frame.rowconfigure(0, weight=1)
        self.low_stock_tree = ttk.Treeview(
            self.low_stock_frame,
            columns=("sku", "name", "supplier", "stock", "threshold"),
            show="headings",
            height=10,
        )
        for column, title, width in (
            ("sku", "SKU", 110),
            ("name", "Product", 210),
            ("supplier", "Supplier", 170),
            ("stock", "Stock", 90),
            ("threshold", "Threshold", 90),
        ):
            self.low_stock_tree.heading(column, text=title)
            self.low_stock_tree.column(column, width=width, anchor="center")
        self.low_stock_tree.grid(row=0, column=0, sticky="nsew")
        low_stock_y = ttk.Scrollbar(self.low_stock_frame, orient="vertical", command=self.low_stock_tree.yview)
        low_stock_y.grid(row=0, column=1, sticky="ns")
        low_stock_x = ttk.Scrollbar(self.low_stock_frame, orient="horizontal", command=self.low_stock_tree.xview)
        low_stock_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.low_stock_tree.configure(yscrollcommand=low_stock_y.set, xscrollcommand=low_stock_x.set)

        self.activity_frame = ttk.LabelFrame(self.lower, text="Recent Activity", padding=16)
        self.activity_frame.columnconfigure(0, weight=1)
        self.activity_frame.rowconfigure(1, weight=1)
        self.activity_frame.rowconfigure(4, weight=1)

        ttk.Label(self.activity_frame, text="Recent Sales", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.sales_x = ttk.Scrollbar(self.activity_frame, orient="horizontal")
        self.sales_list = tk.Listbox(
            self.activity_frame,
            height=7,
            relief="flat",
            font=("Segoe UI", 10),
            xscrollcommand=self.sales_x.set,
        )
        self.sales_x.configure(command=self.sales_list.xview)
        self.sales_list.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.sales_x.grid(row=2, column=0, sticky="ew", pady=(6, 16))

        ttk.Label(self.activity_frame, text="Recent Attendance", style="Section.TLabel").grid(row=3, column=0, sticky="w")
        self.attendance_x = ttk.Scrollbar(self.activity_frame, orient="horizontal")
        self.attendance_list = tk.Listbox(
            self.activity_frame,
            height=7,
            relief="flat",
            font=("Segoe UI", 10),
            xscrollcommand=self.attendance_x.set,
        )
        self.attendance_x.configure(command=self.attendance_list.xview)
        self.attendance_list.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        self.attendance_x.grid(row=5, column=0, sticky="ew", pady=(6, 0))

    def _build_personal_lower(self) -> None:
        self.sales_frame = ttk.LabelFrame(self.lower, text="My Recent Sales", padding=16)
        self.sales_frame.columnconfigure(0, weight=1)
        self.sales_frame.rowconfigure(1, weight=1)
        ttk.Label(
            self.sales_frame,
            text="Only your own sales activity is shown here.",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.sales_x = ttk.Scrollbar(self.sales_frame, orient="horizontal")
        self.sales_list = tk.Listbox(
            self.sales_frame,
            height=12,
            relief="flat",
            font=("Segoe UI", 10),
            xscrollcommand=self.sales_x.set,
        )
        self.sales_x.configure(command=self.sales_list.xview)
        self.sales_list.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.sales_x.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        self.updates_frame = ttk.LabelFrame(self.lower, text="Product Updates", padding=16)
        self.updates_frame.columnconfigure(0, weight=1)
        self.updates_frame.rowconfigure(1, weight=1)
        ttk.Label(
            self.updates_frame,
            text="Newly added products are listed here so you can stay updated on what is available to sell.",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.products_x = ttk.Scrollbar(self.updates_frame, orient="horizontal")
        self.products_list = tk.Listbox(
            self.updates_frame,
            height=12,
            relief="flat",
            font=("Segoe UI", 10),
            xscrollcommand=self.products_x.set,
        )
        self.products_x.configure(command=self.products_list.xview)
        self.products_list.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.products_x.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        card_columns = 3 if width >= 1380 else 2 if width >= 820 else 1

        for child in self.cards_frame.winfo_children():
            child.grid_forget()
        for column in range(6):
            self.cards_frame.columnconfigure(column, weight=0)
        for column in range(card_columns):
            self.cards_frame.columnconfigure(column, weight=1)

        for index, card in enumerate(self.cards):
            row = index // card_columns
            column = index % card_columns
            padx = (0, 8) if column < card_columns - 1 else (0, 0)
            pady = (0, 8) if index < len(self.cards) - card_columns else (0, 0)
            card.grid(row=row, column=column, sticky="nsew", padx=padx, pady=pady)

        if self.personal_pay_frame is not None:
            self.personal_pay_frame.grid(row=3, column=0, sticky="ew", pady=(16, 0))

        for child in self.lower.winfo_children():
            child.grid_forget()
        self.lower.columnconfigure(0, weight=0)
        self.lower.columnconfigure(1, weight=0)

        if width >= 1080:
            self.lower.columnconfigure(0, weight=1)
            self.lower.columnconfigure(1, weight=1)
            if self.is_admin:
                self.low_stock_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
                self.activity_frame.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
            else:
                self.sales_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
                self.updates_frame.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        else:
            self.lower.columnconfigure(0, weight=1)
            if self.is_admin:
                self.low_stock_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
                self.activity_frame.grid(row=1, column=0, sticky="nsew")
            else:
                self.sales_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
                self.updates_frame.grid(row=1, column=0, sticky="nsew")

        self._sync_scrollregion()

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        widgets = [self.sales_list]
        if self.is_admin:
            widgets.append(self.attendance_list)
        else:
            widgets.append(self.products_list)
        for widget in widgets:
            widget.configure(
                bg=palette["entry"],
                fg=palette["text"],
                selectbackground=palette["accent"],
                selectforeground="#FFFFFF",
                highlightthickness=0,
                borderwidth=0,
            )

    def refresh(self) -> None:
        stats = self.dashboard_service.stats(self.current_user)
        currency_settings = self.settings_service.get_currency_settings()

        if stats["mode"] == "admin":
            values = [
                str(stats["employees"]),
                self.settings_service.format_money(stats["sales_today"], currency_settings),
                self.settings_service.format_money(stats["expenses_today"], currency_settings),
                self.settings_service.format_money(stats["profit_today"], currency_settings),
                self.settings_service.format_money(stats["inventory_value"], currency_settings),
                str(stats["low_stock"]),
            ]
            details = [
                "Ready for assigned operations",
                "All receipts processed today",
                "Utilities, rent, and other recorded spending",
                "Revenue minus stock cost and expenses",
                "Live retail asset valuation",
                "Products that need restocking attention",
            ]
        else:
            values = [
                str(stats["my_receipts_today"]),
                self.settings_service.format_money(stats["my_sales_today"], currency_settings),
                str(stats["new_products"]),
                str(len(stats["recent_sales"])),
            ]
            details = [
                "Receipts created by your account today",
                "Your personal sales total for the day",
                "Products added during the last 7 days",
                "Your most recent saved sale activity",
            ]

        for card, value, detail in zip(self.cards, values, details):
            card.update_content(value, detail)

        if self.personal_pay_frame is not None:
            summary = self.payroll_service.summary_for_user(self.current_user)
            if summary is None:
                self.personal_pay_title_var.set("My Payment Snapshot")
                self.personal_pay_value_var.set(
                    "No employee profile is linked to this login yet. Ask an administrator to connect your account to a staff record."
                )
            else:
                self.personal_pay_title_var.set(
                    f"{summary['employee']['full_name']} | {summary['period_start']} to {summary['period_end']}"
                )
                self.personal_pay_value_var.set(
                    " | ".join(
                        [
                            f"Base Pay: {self.settings_service.format_money(summary['base_pay'], currency_settings)}",
                            f"Overtime: {self.settings_service.format_money(summary['overtime_pay'], currency_settings)}",
                            f"Estimated Gross: {self.settings_service.format_money(summary['gross_pay'], currency_settings)}",
                            f"Hours: {summary['regular_hours']:.2f} regular / {summary['overtime_hours']:.2f} overtime",
                        ]
                    )
                )

        self.sales_list.delete(0, tk.END)
        for sale in stats["recent_sales"]:
            amount = self.settings_service.format_money(sale["total_amount"], currency_settings)
            self.sales_list.insert(
                tk.END,
                f"{sale['receipt_no']} | {sale['payment_method']} | {amount} | {sale['created_at'][:16]}",
            )

        if self.is_admin:
            for item in self.low_stock_tree.get_children():
                self.low_stock_tree.delete(item)
            for product in self.inventory_service.low_stock_products():
                self.low_stock_tree.insert(
                    "",
                    "end",
                    values=(
                        product["sku"],
                        product["name"],
                        product.get("supplier") or "-",
                        product["stock_qty"],
                        product["low_stock_threshold"],
                    ),
                )

            self.attendance_list.delete(0, tk.END)
            for entry in stats["recent_attendance"]:
                self.attendance_list.insert(
                    tk.END,
                    f"{entry['employee_code']} | {entry['full_name']} | {entry['clock_in'][:16]}",
                )
        else:
            self.products_list.delete(0, tk.END)
            for product in stats["product_updates"]:
                supplier = product.get("supplier") or "No supplier"
                self.products_list.insert(
                    tk.END,
                    f"{product['sku']} | {product['name']} | {supplier} | added {product['created_at'][:16]}",
                )
