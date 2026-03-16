from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.services.access_control import has_permission
from app.ui.widgets import ScrollablePage, StatCard, apply_treeview_stripes, repopulate_with_stripes


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
        super().__init__(parent, padding=14)
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
            "Track the supermarket at a glance — staff, stock, sales, expenses, and performance at one view."
            if self.is_admin
            else "See your own sales work, receipt activity, product updates, and your payment snapshot in one place."
        )

        # ── Page headline ─────────────────────────────────────────────────────
        ttk.Label(self.body, text=title, style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            self.body,
            text=subtitle,
            style="MutedBg.TLabel",
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 14))

        # ── Stat cards ────────────────────────────────────────────────────────
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

        # ── Pay snapshot (payroll-enabled users) ──────────────────────────────
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
                wraplength=1100,
                justify="left",
            ).grid(row=1, column=0, sticky="ew", pady=(8, 0))

        # ── Lower activity section ────────────────────────────────────────────
        self.lower = ttk.Frame(self.body, style="App.TFrame")
        self.lower.grid(row=4, column=0, sticky="nsew", pady=(18, 0))

        if self.is_admin:
            self._build_admin_lower()
        else:
            self._build_personal_lower()

        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)

    # ── Admin lower panels ────────────────────────────────────────────────────

    def _build_admin_lower(self) -> None:
        # Low-stock Treeview
        self.low_stock_frame = ttk.LabelFrame(self.lower, text="⚠  Low Stock Alerts", padding=14)
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

        # Recent activity side panel
        self.activity_frame = ttk.LabelFrame(self.lower, text="Recent Activity", padding=14)
        self.activity_frame.columnconfigure(0, weight=1)
        self.activity_frame.rowconfigure(1, weight=1)
        self.activity_frame.rowconfigure(5, weight=1)

        ttk.Label(self.activity_frame, text="Recent Sales", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.sales_tree = ttk.Treeview(
            self.activity_frame,
            columns=("receipt", "method", "amount", "time"),
            show="headings",
            height=7,
        )
        for col, title, width in (
            ("receipt", "Receipt", 130),
            ("method", "Method", 100),
            ("amount", "Amount", 110),
            ("time", "Time", 130),
        ):
            self.sales_tree.heading(col, text=title)
            self.sales_tree.column(col, width=width, anchor="center")
        self.sales_tree.grid(row=1, column=0, sticky="nsew")
        s_y = ttk.Scrollbar(self.activity_frame, orient="vertical", command=self.sales_tree.yview)
        s_y.grid(row=1, column=1, sticky="ns")
        s_x = ttk.Scrollbar(self.activity_frame, orient="horizontal", command=self.sales_tree.xview)
        s_x.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.sales_tree.configure(yscrollcommand=s_y.set, xscrollcommand=s_x.set)

        ttk.Separator(self.activity_frame, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(12, 12)
        )

        ttk.Label(self.activity_frame, text="Recent Attendance", style="Section.TLabel").grid(
            row=4, column=0, sticky="w", pady=(0, 6)
        )
        self.attendance_tree = ttk.Treeview(
            self.activity_frame,
            columns=("code", "name", "clock_in"),
            show="headings",
            height=7,
        )
        for col, title, width in (
            ("code", "Code", 90),
            ("name", "Name", 170),
            ("clock_in", "Clock In", 140),
        ):
            self.attendance_tree.heading(col, text=title)
            self.attendance_tree.column(col, width=width, anchor="center")
        self.attendance_tree.grid(row=5, column=0, sticky="nsew")
        a_y = ttk.Scrollbar(self.activity_frame, orient="vertical", command=self.attendance_tree.yview)
        a_y.grid(row=5, column=1, sticky="ns")
        a_x = ttk.Scrollbar(self.activity_frame, orient="horizontal", command=self.attendance_tree.xview)
        a_x.grid(row=6, column=0, sticky="ew", pady=(4, 0))
        self.attendance_tree.configure(yscrollcommand=a_y.set, xscrollcommand=a_x.set)

    # ── Personal lower panels ─────────────────────────────────────────────────

    def _build_personal_lower(self) -> None:
        self.sales_frame = ttk.LabelFrame(self.lower, text="My Recent Sales", padding=14)
        self.sales_frame.columnconfigure(0, weight=1)
        self.sales_frame.rowconfigure(1, weight=1)
        ttk.Label(
            self.sales_frame, text="Only your own sales activity is shown here.",
            style="Muted.TLabel", wraplength=460,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.sales_tree = ttk.Treeview(
            self.sales_frame,
            columns=("receipt", "method", "amount", "time"),
            show="headings",
            height=12,
        )
        for col, title, width in (
            ("receipt", "Receipt", 160),
            ("method", "Method", 130),
            ("amount", "Amount", 140),
            ("time", "Time", 160),
        ):
            self.sales_tree.heading(col, text=title)
            self.sales_tree.column(col, width=width, anchor="center")
        self.sales_tree.grid(row=1, column=0, sticky="nsew")
        s_y = ttk.Scrollbar(self.sales_frame, orient="vertical", command=self.sales_tree.yview)
        s_y.grid(row=1, column=1, sticky="ns")
        s_x = ttk.Scrollbar(self.sales_frame, orient="horizontal", command=self.sales_tree.xview)
        s_x.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.sales_tree.configure(yscrollcommand=s_y.set, xscrollcommand=s_x.set)

        self.updates_frame = ttk.LabelFrame(self.lower, text="Product Updates", padding=14)
        self.updates_frame.columnconfigure(0, weight=1)
        self.updates_frame.rowconfigure(1, weight=1)
        ttk.Label(
            self.updates_frame,
            text="Newly added products are listed here so you can stay updated on what is available to sell.",
            style="Muted.TLabel", wraplength=460,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.products_tree = ttk.Treeview(
            self.updates_frame,
            columns=("sku", "name", "supplier", "added"),
            show="headings",
            height=12,
        )
        for col, title, width in (
            ("sku", "SKU", 100),
            ("name", "Product", 180),
            ("supplier", "Supplier", 140),
            ("added", "Added", 130),
        ):
            self.products_tree.heading(col, text=title)
            self.products_tree.column(col, width=width, anchor="center")
        self.products_tree.grid(row=1, column=0, sticky="nsew")
        p_y = ttk.Scrollbar(self.updates_frame, orient="vertical", command=self.products_tree.yview)
        p_y.grid(row=1, column=1, sticky="ns")
        p_x = ttk.Scrollbar(self.updates_frame, orient="horizontal", command=self.products_tree.xview)
        p_x.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.products_tree.configure(yscrollcommand=p_y.set, xscrollcommand=p_x.set)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        card_columns = 3 if width >= 1200 else 2 if width >= 760 else 1

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
            self.personal_pay_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))

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

    # ── Palette ───────────────────────────────────────────────────────────────

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        for card in self.cards:
            card.apply_palette(palette)
        trees = [self.sales_tree]
        if self.is_admin:
            trees += [self.low_stock_tree, self.attendance_tree]
        else:
            trees += [self.products_tree]
        for tree in trees:
            apply_treeview_stripes(tree, palette)

    # ── Refresh ───────────────────────────────────────────────────────────────

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
                    f"{summary['employee']['full_name']}  ·  {summary['period_start']} to {summary['period_end']}"
                )
                self.personal_pay_value_var.set(
                    "  |  ".join(
                        [
                            f"Base Pay: {self.settings_service.format_money(summary['base_pay'], currency_settings)}",
                            f"Overtime: {self.settings_service.format_money(summary['overtime_pay'], currency_settings)}",
                            f"Estimated Gross: {self.settings_service.format_money(summary['gross_pay'], currency_settings)}",
                            f"Hours: {summary['regular_hours']:.2f} regular / {summary['overtime_hours']:.2f} overtime",
                        ]
                    )
                )

        # Recent sales Treeview
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
        for index, sale in enumerate(stats["recent_sales"]):
            amount = self.settings_service.format_money(sale["total_amount"], currency_settings)
            tag = "even" if index % 2 == 0 else "odd"
            self.sales_tree.insert(
                "",
                "end",
                values=(
                    sale["receipt_no"],
                    sale["payment_method"],
                    amount,
                    sale["created_at"][:16],
                ),
                tags=(tag,),
            )

        if self.is_admin:
            # Low-stock Treeview
            for item in self.low_stock_tree.get_children():
                self.low_stock_tree.delete(item)
            for index, product in enumerate(self.inventory_service.low_stock_products()):
                tag = "even" if index % 2 == 0 else "odd"
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
                    tags=(tag,),
                )

            # Attendance Treeview
            for item in self.attendance_tree.get_children():
                self.attendance_tree.delete(item)
            for index, entry in enumerate(stats["recent_attendance"]):
                tag = "even" if index % 2 == 0 else "odd"
                self.attendance_tree.insert(
                    "",
                    "end",
                    values=(
                        entry["employee_code"],
                        entry["full_name"],
                        entry["clock_in"][:16],
                    ),
                    tags=(tag,),
                )
        else:
            for item in self.products_tree.get_children():
                self.products_tree.delete(item)
            for index, product in enumerate(stats["product_updates"]):
                tag = "even" if index % 2 == 0 else "odd"
                self.products_tree.insert(
                    "",
                    "end",
                    values=(
                        product["sku"],
                        product["name"],
                        product.get("supplier") or "No supplier",
                        product["created_at"][:16],
                    ),
                    tags=(tag,),
                )
