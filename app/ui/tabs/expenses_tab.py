from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from app.config import COPYRIGHT_TEXT, STORE_NAME
from app.ui.widgets import ScrollablePage, make_labeled_entry, apply_treeview_stripes
from app.utils.pdf_export import export_text_as_pdf


class ExpensesTab(ScrollablePage):
    def __init__(self, parent, current_user: dict, expenses_service, inventory_service, settings_service, refresh_callbacks=None) -> None:
        super().__init__(parent, padding=14)
        self.current_user = current_user
        self.expenses_service = expenses_service
        self.inventory_service = inventory_service
        self.settings_service = settings_service
        self.refresh_callbacks = refresh_callbacks or []
        self.selected_expense_id: int | None = None
        self.selected_purchase_id: int | None = None
        self.loaded_purchase_amount_paid: float = 0.0
        self.product_lookup: dict[str, dict] = {}

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Expenses & Supplier Credit", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            self.body,
            text="Manage supermarket operating expenses, record new stock purchases, track supplier credit, and settle unpaid balances from one admin workspace.",
            style="MutedBg.TLabel",
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.inner_notebook = ttk.Notebook(self.body)
        self.inner_notebook.grid(row=2, column=0, sticky="nsew")

        self.expenses_page = ttk.Frame(self.inner_notebook, style="App.TFrame", padding=6)
        self.suppliers_page = ttk.Frame(self.inner_notebook, style="App.TFrame", padding=6)
        self.inner_notebook.add(self.expenses_page, text="Expenses")
        self.inner_notebook.add(self.suppliers_page, text="Supplier Credit")

        self._build_expenses_page()
        self._build_suppliers_page()
        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh()

    def _build_expenses_page(self) -> None:
        self.expenses_page.columnconfigure(0, weight=1)
        self.expenses_page.rowconfigure(0, weight=1)
        self.expenses_page.rowconfigure(1, weight=0)

        self.expense_grid = ttk.LabelFrame(self.expenses_page, text="Expense Records", padding=14)
        self.expense_grid.columnconfigure(0, weight=1)
        self.expense_grid.rowconfigure(0, weight=1)

        columns = ("date", "category", "title", "amount", "notes")
        self.expense_tree = ttk.Treeview(self.expense_grid, columns=columns, show="headings", height=16)
        for key, title, width in (
            ("date", "Date", 100),
            ("category", "Category", 140),
            ("title", "Title", 220),
            ("amount", "Amount", 120),
            ("notes", "Notes", 240),
        ):
            self.expense_tree.heading(key, text=title)
            self.expense_tree.column(key, width=width, anchor="center")
        self.expense_tree.grid(row=0, column=0, sticky="nsew")
        self.expense_tree.bind("<<TreeviewSelect>>", self._load_selected_expense)
        expense_y = ttk.Scrollbar(self.expense_grid, orient="vertical", command=self.expense_tree.yview)
        expense_y.grid(row=0, column=1, sticky="ns")
        expense_x = ttk.Scrollbar(self.expense_grid, orient="horizontal", command=self.expense_tree.xview)
        expense_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.expense_tree.configure(yscrollcommand=expense_y.set, xscrollcommand=expense_x.set)

        expense_summary = ttk.Frame(self.expense_grid, style="Surface.TFrame")
        expense_summary.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        expense_summary.columnconfigure(1, weight=1)
        expense_summary.columnconfigure(3, weight=1)
        self.expenses_month_total_var = tk.StringVar(value="0")
        self.expenses_all_time_total_var = tk.StringVar(value="0")
        ttk.Label(expense_summary, text="This Month Total:", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(expense_summary, textvariable=self.expenses_month_total_var, style="CardTitle.TLabel").grid(
            row=0, column=1, sticky="w", padx=(6, 16)
        )
        ttk.Label(expense_summary, text="All-Time Total:", style="FormLabel.TLabel").grid(
            row=0, column=2, sticky="w"
        )
        ttk.Label(expense_summary, textvariable=self.expenses_all_time_total_var, style="CardTitle.TLabel").grid(
            row=0, column=3, sticky="w", padx=(6, 0)
        )

        self.expense_form = ttk.LabelFrame(self.expenses_page, text="Add Expense", padding=16)
        self.expense_form.columnconfigure(0, weight=1)
        self.expense_date_var = tk.StringVar(value=date.today().isoformat())
        self.expense_category_var = tk.StringVar()
        self.expense_title_var = tk.StringVar()
        self.expense_amount_var = tk.StringVar(value="0")
        self.expense_notes_var = tk.StringVar()

        make_labeled_entry(self.expense_form, "Expense Date", self.expense_date_var, 0, 0)
        make_labeled_entry(self.expense_form, "Category", self.expense_category_var, 2, 0)
        make_labeled_entry(self.expense_form, "Title", self.expense_title_var, 4, 0)
        make_labeled_entry(self.expense_form, "Amount", self.expense_amount_var, 6, 0)
        make_labeled_entry(self.expense_form, "Notes", self.expense_notes_var, 8, 0, width=36)

        expense_actions = ttk.Frame(self.expense_form, style="Surface.TFrame")
        expense_actions.grid(row=10, column=0, sticky="ew", pady=(8, 0))
        expense_actions.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(expense_actions, text="Clear", style="Secondary.TButton", command=self._reset_expense_form).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(expense_actions, text="Delete", style="Secondary.TButton", command=self._delete_expense).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        self.save_expense_btn = ttk.Button(expense_actions, text="Save Expense", style="Primary.TButton", command=self._save_expense)
        self.save_expense_btn.grid(row=0, column=2, sticky="ew", padx=(8, 0))

    def _build_suppliers_page(self) -> None:
        self.suppliers_page.columnconfigure(0, weight=1)
        self.suppliers_page.rowconfigure(1, weight=1)  # Allow payables frame to expand
        self.suppliers_page.rowconfigure(3, weight=1)  # Allow payment log frame to expand

        self.purchase_form = ttk.LabelFrame(self.suppliers_page, text="Record Stock Purchase", padding=16)
        self.purchase_form.grid(row=0, column=0, sticky="ew")
        self.purchase_form.columnconfigure(0, weight=1)
        self.purchase_form.columnconfigure(1, weight=1)

        self.purchase_product_var = tk.StringVar()
        self.purchase_supplier_var = tk.StringVar()
        self.purchase_date_var = tk.StringVar(value=date.today().isoformat())
        self.purchase_quantity_var = tk.StringVar(value="1")
        self.purchase_unit_cost_var = tk.StringVar(value="0")
        self.purchase_total_amount_var = tk.StringVar(value="0")
        self.purchase_payment_type_var = tk.StringVar(value="cash")
        self.purchase_amount_paid_var = tk.StringVar(value="0")
        self.purchase_notes_var = tk.StringVar()
        self.payment_amount_var = tk.StringVar(value="0")
        self.payment_date_var = tk.StringVar(value=date.today().isoformat())
        self.payment_notes_var = tk.StringVar()

        ttk.Label(self.purchase_form, text="Product", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.purchase_product_box = ttk.Combobox(self.purchase_form, textvariable=self.purchase_product_var, state="readonly")
        self.purchase_product_box.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        self.purchase_product_box.bind("<<ComboboxSelected>>", self._on_product_selected)
        
        # Supplier Name - dropdown from inventory records
        ttk.Label(self.purchase_form, text="Supplier Name", style="FormLabel.TLabel").grid(row=0, column=1, sticky="w", pady=(0, 4))
        self.purchase_supplier_box = ttk.Combobox(self.purchase_form, textvariable=self.purchase_supplier_var, state="readonly")
        self.purchase_supplier_box.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))
        make_labeled_entry(self.purchase_form, "Purchase Date", self.purchase_date_var, 2, 0)
        ttk.Label(self.purchase_form, text="Supplied Quantity", style="FormLabel.TLabel").grid(row=2, column=1, sticky="w", pady=(0, 4))
        self.purchase_quantity_entry = ttk.Entry(self.purchase_form, textvariable=self.purchase_quantity_var)
        self.purchase_quantity_entry.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))
        ttk.Label(self.purchase_form, text="Unit Cost", style="FormLabel.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.purchase_unit_cost_entry = ttk.Entry(self.purchase_form, textvariable=self.purchase_unit_cost_var)
        self.purchase_unit_cost_entry.grid(row=5, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        ttk.Label(self.purchase_form, text="Total Amount (Qty × Unit Cost)", style="FormLabel.TLabel").grid(
            row=6, column=0, sticky="w", pady=(0, 4)
        )
        self.purchase_total_amount_entry = ttk.Entry(self.purchase_form, textvariable=self.purchase_total_amount_var, state="readonly")
        self.purchase_total_amount_entry.grid(row=7, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        ttk.Label(self.purchase_form, text="Payment Type", style="FormLabel.TLabel").grid(row=4, column=1, sticky="w", pady=(0, 4))
        self.purchase_payment_box = ttk.Combobox(
            self.purchase_form,
            textvariable=self.purchase_payment_type_var,
            values=("cash", "mobile money", "bank"),
            state="readonly",
        )
        self.purchase_payment_box.grid(row=5, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))
        self.purchase_payment_box.bind("<<ComboboxSelected>>", self._sync_purchase_payment_state)
        make_labeled_entry(self.purchase_form, "Amount Paid Now", self.purchase_amount_paid_var, 8, 0)
        make_labeled_entry(self.purchase_form, "Notes", self.purchase_notes_var, 8, 1, width=36)

        # Purchase action buttons (Clear, Delete, Save)
        purchase_actions = ttk.Frame(self.purchase_form, style="Surface.TFrame")
        purchase_actions.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        purchase_actions.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(purchase_actions, text="Clear", style="Secondary.TButton", command=self._reset_purchase_form).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(purchase_actions, text="Delete", style="Secondary.TButton", command=self._delete_purchase).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        self.save_purchase_btn = ttk.Button(purchase_actions, text="Save Stock Purchase", style="Primary.TButton", command=self._save_purchase)
        self.save_purchase_btn.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        self.payables_frame = ttk.LabelFrame(self.suppliers_page, text="Supplier Payables", padding=14)
        self.payables_frame.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        self.payables_frame.columnconfigure(0, weight=1)
        self.payables_frame.rowconfigure(1, weight=1)

        payables_controls = ttk.Frame(self.payables_frame, style="Surface.TFrame")
        payables_controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        payables_controls.columnconfigure(1, weight=1)
        self.payables_filter_var = tk.StringVar(value="All")
        ttk.Label(payables_controls, text="Filter", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.payables_filter_box = ttk.Combobox(
            payables_controls,
            textvariable=self.payables_filter_var,
            values=("All", "With Balance", "Zero Balance"),
            state="readonly",
        )
        self.payables_filter_box.grid(row=0, column=1, sticky="w")
        self.payables_filter_box.bind("<<ComboboxSelected>>", self._on_payables_filter_changed)

        columns = ("supplier", "product", "qty", "date", "mode", "total", "paid", "pending")
        self.payables_tree = ttk.Treeview(self.payables_frame, columns=columns, show="headings", height=10)
        for key, title, width in (
            ("supplier", "Supplier", 170),
            ("product", "Product", 180),
            ("qty", "Qty", 70),
            ("date", "Purchase Date", 110),
            ("mode", "Mode", 100),
            ("total", "Total", 120),
            ("paid", "Paid", 120),
            ("pending", "Pending", 120),
        ):
            self.payables_tree.heading(key, text=title)
            self.payables_tree.column(key, width=width, anchor="center")
        self.payables_tree.grid(row=1, column=0, sticky="nsew")
        self.payables_tree.bind("<<TreeviewSelect>>", self._load_selected_purchase)
        payables_y = ttk.Scrollbar(self.payables_frame, orient="vertical", command=self.payables_tree.yview)
        payables_y.grid(row=1, column=1, sticky="ns")
        payables_x = ttk.Scrollbar(self.payables_frame, orient="horizontal", command=self.payables_tree.xview)
        payables_x.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.payables_tree.configure(yscrollcommand=payables_y.set, xscrollcommand=payables_x.set)

        self.payment_panel = ttk.LabelFrame(self.suppliers_page, text="Record Supplier Payment", padding=16)
        self.payment_panel.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self.payment_panel.columnconfigure((0, 1), weight=1)
        self.purchase_status_var = tk.StringVar(value="Select a stock purchase to manage payments.")
        ttk.Label(
            self.payment_panel,
            textvariable=self.purchase_status_var,
            style="Muted.TLabel",
            wraplength=900,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        make_labeled_entry(self.payment_panel, "Payment Amount", self.payment_amount_var, 1, 0)
        make_labeled_entry(self.payment_panel, "Payment Date", self.payment_date_var, 1, 1)
        # Payment Notes - manually placed with colspan to span both columns
        ttk.Label(self.payment_panel, text="Payment Notes", style="FormLabel.TLabel").grid(
            row=3, column=0, sticky="w", pady=(0, 4), columnspan=2
        )
        payment_notes_entry = ttk.Entry(self.payment_panel, textvariable=self.payment_notes_var, width=40)
        payment_notes_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Button(self.payment_panel, text="Record Payment", style="Primary.TButton", command=self._record_payment).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

        self.payment_history_list = tk.Listbox(self.payment_panel, height=4, relief="flat", font=("Segoe UI", 10))
        self.payment_history_list.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        self.payment_log_frame = ttk.LabelFrame(self.suppliers_page, text="Supplier Payment Audit Log", padding=14)
        self.payment_log_frame.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        self.payment_log_frame.columnconfigure(0, weight=1)
        self.payment_log_frame.rowconfigure(1, weight=1)

        payment_log_filters = ttk.Frame(self.payment_log_frame, style="Surface.TFrame")
        payment_log_filters.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        payment_log_filters.columnconfigure(1, weight=1)

        self.payment_log_supplier_var = tk.StringVar(value="All Suppliers")
        ttk.Label(payment_log_filters, text="Supplier", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.payment_log_supplier_box = ttk.Combobox(
            payment_log_filters,
            textvariable=self.payment_log_supplier_var,
            state="readonly",
        )
        self.payment_log_supplier_box.grid(row=0, column=1, sticky="ew")
        self.payment_log_supplier_box.bind("<<ComboboxSelected>>", self._on_supplier_log_filter_changed)
        ttk.Button(
            payment_log_filters,
            text="Export Log (PDF)",
            style="Primary.TButton",
            command=self._export_supplier_payment_log,
        ).grid(row=0, column=2, sticky="e", padx=(10, 0))

        log_columns = ("ref", "date", "supplier", "product", "method", "amount", "remaining", "status", "by", "notes")
        self.payment_log_tree = ttk.Treeview(self.payment_log_frame, columns=log_columns, show="headings", height=9)
        for key, title, width in (
            ("ref", "Ref", 130),
            ("date", "Payment Date", 110),
            ("supplier", "Supplier", 150),
            ("product", "Product", 170),
            ("method", "Method", 120),
            ("amount", "Amount Paid", 120),
            ("remaining", "Balance After", 130),
            ("status", "Status", 90),
            ("by", "Recorded By", 140),
            ("notes", "Notes", 200),
        ):
            self.payment_log_tree.heading(key, text=title)
            self.payment_log_tree.column(key, width=width, anchor="center")
        self.payment_log_tree.grid(row=1, column=0, sticky="nsew")

        payment_log_y = ttk.Scrollbar(self.payment_log_frame, orient="vertical", command=self.payment_log_tree.yview)
        payment_log_y.grid(row=1, column=1, sticky="ns")
        payment_log_x = ttk.Scrollbar(self.payment_log_frame, orient="horizontal", command=self.payment_log_tree.xview)
        payment_log_x.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.payment_log_tree.configure(yscrollcommand=payment_log_y.set, xscrollcommand=payment_log_x.set)

        self.purchase_quantity_var.trace_add("write", lambda *_: self._recalculate_purchase_total())
        self.purchase_unit_cost_var.trace_add("write", lambda *_: self._recalculate_purchase_total())
        self._recalculate_purchase_total()
        self._sync_purchase_payment_state()

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        self.expense_grid.grid_forget()
        self.expense_form.grid_forget()

        self.expense_grid.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        self.expense_form.grid(row=1, column=0, sticky="nsew")

        self._sync_scrollregion()

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        self.payment_history_list.configure(
            bg=palette["entry"],
            fg=palette["text"],
            selectbackground=palette["accent"],
            selectforeground="#FFFFFF",
            highlightthickness=0,
            borderwidth=0,
        )
        apply_treeview_stripes(self.expense_tree, palette)
        apply_treeview_stripes(self.payment_log_tree, palette)
        # Pending balances are highlighted red, settled balances are highlighted green.
        self.payables_tree.tag_configure("pending", background="#FAD4D8", foreground="#7F1D1D")
        self.payables_tree.tag_configure("settled", background="#D4EDDA", foreground="#1A6B3C")
        self.payment_log_tree.tag_configure("partial", background="#FFF6CC", foreground="#7A4B00")
        self.payment_log_tree.tag_configure("full", background="#D4EDDA", foreground="#1A6B3C")

    def _recalculate_purchase_total(self) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        try:
            quantity = int((self.purchase_quantity_var.get() or "0").strip())
            unit_cost = self.settings_service.parse_money(self.purchase_unit_cost_var.get(), currency_settings)
            total = max(quantity, 0) * max(unit_cost, 0.0)
        except ValueError:
            total = 0.0
        self.purchase_total_amount_var.set(self.settings_service.format_money(total, currency_settings))

    def _sync_purchase_payment_state(self, _event=None) -> None:
        if not self.purchase_amount_paid_var.get().strip():
            self.purchase_amount_paid_var.set("0")

    def _on_payables_filter_changed(self, _event=None) -> None:
        self.refresh()

    def _matches_payables_filter(self, pending_amount: float) -> bool:
        selected_filter = self.payables_filter_var.get().strip()
        if selected_filter == "With Balance":
            return pending_amount > 0.009
        if selected_filter == "Zero Balance":
            return pending_amount <= 0.009
        return True

    def _reset_purchase_form(self) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        self.selected_purchase_id = None
        self.loaded_purchase_amount_paid = 0.0
        self.purchase_product_var.set(next(iter(self.product_lookup.keys())) if self.product_lookup else "")
        self.purchase_supplier_var.set("")
        self.purchase_supplier_box["values"] = []
        self.purchase_date_var.set(date.today().isoformat())
        # Trigger product selection to populate stock and total amount
        self._on_product_selected()
        self.purchase_payment_type_var.set("cash")
        self.purchase_amount_paid_var.set("0")
        self.purchase_notes_var.set("")
        self.save_purchase_btn.configure(text="Save Stock Purchase", command=self._save_purchase)
        self.purchase_status_var.set("Select a stock purchase to manage payments.")
        self.payment_amount_var.set(self.settings_service.format_money(0, currency_settings))
        self.payment_date_var.set(date.today().isoformat())
        self.payment_notes_var.set("")
        self.payment_history_list.delete(0, tk.END)
        for item in self.payables_tree.selection():
            self.payables_tree.selection_remove(item)
        self._recalculate_purchase_total()
        self._sync_purchase_payment_state()

    def _selected_product_id(self) -> int | None:
        product = self.product_lookup.get(self.purchase_product_var.get())
        return int(product["id"]) if product else None

    def _on_supplier_log_filter_changed(self, _event=None) -> None:
        self._refresh_supplier_payment_log()

    def _refresh_supplier_payment_log(self) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        supplier_filter = self.payment_log_supplier_var.get().strip()
        selected_supplier = None if supplier_filter in {"", "All Suppliers"} else supplier_filter

        for item in self.payment_log_tree.get_children():
            self.payment_log_tree.delete(item)

        logs = self.inventory_service.supplier_payment_log(selected_supplier)
        for entry in logs:
            status = entry.get("settlement_status", "Partial")
            tag = "full" if status == "Full" else "partial"
            self.payment_log_tree.insert(
                "",
                "end",
                values=(
                    entry.get("payment_reference", "-"),
                    entry.get("payment_date", "-"),
                    entry.get("supplier_name", "-"),
                    entry.get("product_name", "-"),
                    str(entry.get("payment_type", "-")).title(),
                    self.settings_service.format_money(entry.get("amount", 0), currency_settings),
                    self.settings_service.format_money(entry.get("remaining_after_payment", 0), currency_settings),
                    status,
                    entry.get("recorded_by", "System User"),
                    entry.get("notes") or "Payment recorded",
                ),
                tags=(tag,),
            )

    def _export_supplier_payment_log(self) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        supplier_filter = self.payment_log_supplier_var.get().strip()
        selected_supplier = None if supplier_filter in {"", "All Suppliers"} else supplier_filter
        logs = self.inventory_service.supplier_payment_log(selected_supplier)
        if not logs:
            messagebox.showwarning("No Log Data", "There are no supplier payment log records to export.", parent=self)
            return

        report_date = date.today().isoformat()
        supplier_label = selected_supplier or "all-suppliers"
        default_name = f"supplier-payment-log-{supplier_label}-{report_date}.pdf".replace(" ", "-")
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Supplier Payment Log",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF File", "*.pdf")],
        )
        if not file_path:
            return

        store_name = self.settings_service.get_store_name() or STORE_NAME
        designer_line = COPYRIGHT_TEXT
        line_width = 142

        def fit(value: object, width: int) -> str:
            text = str(value or "-").replace("\n", " ").strip()
            if len(text) > width:
                return text[: max(width - 3, 1)] + "..."
            return text.ljust(width)

        lines = [
            store_name.upper(),
            "SUPPLIER PAYMENT AUDIT LOG",
            designer_line,
            f"Generated: {report_date}",
            f"Filter: {selected_supplier or 'All Suppliers'}",
            "=" * line_width,
            (
                f"{fit('Ref', 14)} {fit('Date', 10)} {fit('Supplier', 16)} {fit('Product', 18)} "
                f"{fit('Method', 10)} {fit('Amount', 12)} {fit('Balance', 12)} {fit('Status', 8)} "
                f"{fit('Recorded By', 14)} {fit('Notes', 16)}"
            ),
            "-" * line_width,
        ]

        for entry in logs:
            row = (
                f"{fit(entry.get('payment_reference', '-'), 14)} "
                f"{fit(entry.get('payment_date', '-'), 10)} "
                f"{fit(entry.get('supplier_name', '-'), 16)} "
                f"{fit(entry.get('product_name', '-'), 18)} "
                f"{fit(str(entry.get('payment_type', '-')).title(), 10)} "
                f"{fit(self.settings_service.format_money(entry.get('amount', 0), currency_settings), 12)} "
                f"{fit(self.settings_service.format_money(entry.get('remaining_after_payment', 0), currency_settings), 12)} "
                f"{fit(entry.get('settlement_status', 'Partial'), 8)} "
                f"{fit(entry.get('recorded_by', 'System User'), 14)} "
                f"{fit(entry.get('notes') or 'Payment recorded', 16)}"
            )
            lines.append(row)

        try:
            export_text_as_pdf("\n".join(lines), file_path, landscape=True, font_size=9)
            messagebox.showinfo("Log Exported", f"Supplier payment log exported to:\n{file_path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc), parent=self)

    def _on_product_selected(self, _event=None) -> None:
        """When product is selected, prefill supplier and unit cost for a supply batch."""
        product = self.product_lookup.get(self.purchase_product_var.get())
        if product:
            cost_price = float(product.get("cost_price", 0))
            product_supplier = (product.get("supplier") or "").strip()

            currency_settings = self.settings_service.get_currency_settings()
            self.purchase_quantity_var.set(self.purchase_quantity_var.get().strip() or "1")
            self.purchase_unit_cost_var.set(self.settings_service.format_money(cost_price, currency_settings))

            # Supplier is tied to product inventory record.
            if product_supplier:
                self.purchase_supplier_box["values"] = [product_supplier]
                self.purchase_supplier_var.set(product_supplier)
            else:
                self.purchase_supplier_box["values"] = []
                self.purchase_supplier_var.set("")
        else:
            self.purchase_quantity_var.set("1")
            currency_settings = self.settings_service.get_currency_settings()
            self.purchase_unit_cost_var.set(self.settings_service.format_money(0, currency_settings))
            self.purchase_supplier_box["values"] = []
            self.purchase_supplier_var.set("")

        self._recalculate_purchase_total()
        self._sync_purchase_payment_state()

    def _load_selected_expense(self, _event=None) -> None:
        selection = self.expense_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        self.selected_expense_id = int(self.expense_tree.item(item_id, "text"))
        # Load expense data for editing
        try:
            expense = self.expenses_service.get_expense(self.selected_expense_id)
            self.expense_date_var.set(expense["expense_date"])
            self.expense_category_var.set(expense["category"])
            self.expense_title_var.set(expense["title"])
            self.expense_amount_var.set(str(expense["amount"]))
            self.expense_notes_var.set(expense.get("notes", ""))
            self.save_expense_btn.configure(text="Update Expense", command=self._update_expense)
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc), parent=self)

    def _reset_expense_form(self) -> None:
        self.selected_expense_id = None
        self.expense_date_var.set(date.today().isoformat())
        self.expense_category_var.set("")
        self.expense_title_var.set("")
        self.expense_amount_var.set("0")
        self.expense_notes_var.set("")
        self.save_expense_btn.configure(text="Save Expense", command=self._save_expense)
        for item in self.expense_tree.selection():
            self.expense_tree.selection_remove(item)

    def _save_expense(self) -> None:
        try:
            self.expenses_service.create_expense(
                {
                    "expense_date": self.expense_date_var.get(),
                    "category": self.expense_category_var.get(),
                    "title": self.expense_title_var.get(),
                    "amount": self.expense_amount_var.get(),
                    "notes": self.expense_notes_var.get(),
                },
                actor_user_id=int(self.current_user["id"]),
            )
            messagebox.showinfo("Expense Saved", "Expense recorded successfully.", parent=self)
            self._reset_expense_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Expense Error", str(exc), parent=self)

    def _update_expense(self) -> None:
        if self.selected_expense_id is None:
            messagebox.showwarning("Select Expense", "Choose an expense record to update first.", parent=self)
            return
        try:
            self.expenses_service.update_expense(
                self.selected_expense_id,
                {
                    "expense_date": self.expense_date_var.get(),
                    "category": self.expense_category_var.get(),
                    "title": self.expense_title_var.get(),
                    "amount": self.expense_amount_var.get(),
                    "notes": self.expense_notes_var.get(),
                },
                actor_user_id=int(self.current_user["id"]),
            )
            messagebox.showinfo("Expense Updated", "Expense updated successfully.", parent=self)
            self._reset_expense_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Update Error", str(exc), parent=self)

    def _delete_expense(self) -> None:
        if self.selected_expense_id is None:
            messagebox.showwarning("Select Expense", "Choose an expense record first.", parent=self)
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected expense?", parent=self):
            return
        try:
            self.expenses_service.delete_expense(self.selected_expense_id)
            self._reset_expense_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Delete Error", str(exc), parent=self)

    def _save_purchase(self) -> None:
        try:
            product_id = self._selected_product_id()
            if product_id is None:
                raise ValueError("Select a valid product for the stock purchase.")
            if not self.purchase_supplier_var.get().strip():
                raise ValueError("Selected product has no supplier in inventory. Set the supplier on the product first.")
            currency_settings = self.settings_service.get_currency_settings()

            quantity = int(self.purchase_quantity_var.get())
            if quantity <= 0:
                raise ValueError("Supplied quantity must be greater than zero.")
            actual_unit_cost = self.settings_service.parse_money(self.purchase_unit_cost_var.get(), currency_settings)
            if actual_unit_cost < 0:
                raise ValueError("Unit cost cannot be negative.")
            amount_paid_value = self.settings_service.parse_money(self.purchase_amount_paid_var.get(), currency_settings)
            
            self.inventory_service.create_stock_purchase(
                {
                    "product_id": product_id,
                    "supplier_name": self.purchase_supplier_var.get(),
                    "purchase_date": self.purchase_date_var.get(),
                    "quantity": self.purchase_quantity_var.get(),
                    "unit_cost": actual_unit_cost,
                    "payment_type": self.purchase_payment_type_var.get(),
                    "amount_paid": amount_paid_value,
                    "notes": self.purchase_notes_var.get(),
                },
                actor_user_id=int(self.current_user["id"]),
            )
            messagebox.showinfo("Stock Purchase Saved", "Stock purchase recorded and inventory updated successfully.", parent=self)
            self._reset_purchase_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Purchase Error", str(exc), parent=self)

    def _update_purchase(self) -> None:
        if self.selected_purchase_id is None:
            messagebox.showwarning("Select Purchase", "Choose a purchase record to update first.", parent=self)
            return
        try:
            product_id = self._selected_product_id()
            if product_id is None:
                raise ValueError("Select a valid product for the stock purchase.")
            if not self.purchase_supplier_var.get().strip():
                raise ValueError("Selected product has no supplier in inventory. Set the supplier on the product first.")

            currency_settings = self.settings_service.get_currency_settings()
            quantity = int(self.purchase_quantity_var.get())
            if quantity <= 0:
                raise ValueError("Supplied quantity must be greater than zero.")
            actual_unit_cost = self.settings_service.parse_money(self.purchase_unit_cost_var.get(), currency_settings)
            if actual_unit_cost < 0:
                raise ValueError("Unit cost cannot be negative.")
            entered_paid_total = self.settings_service.parse_money(self.purchase_amount_paid_var.get(), currency_settings)
            if entered_paid_total < 0:
                raise ValueError("Amount paid now cannot be negative.")

            additional_payment = round(entered_paid_total - self.loaded_purchase_amount_paid, 2)
            if additional_payment < 0:
                raise ValueError("Amount Paid Now cannot be reduced below already recorded paid amount.")

            self.inventory_service.update_stock_purchase(
                self.selected_purchase_id,
                {
                    "product_id": product_id,
                    "supplier_name": self.purchase_supplier_var.get(),
                    "purchase_date": self.purchase_date_var.get(),
                    "quantity": self.purchase_quantity_var.get(),
                    "unit_cost": actual_unit_cost,
                    "payment_type": self.purchase_payment_type_var.get(),
                    "notes": self.purchase_notes_var.get(),
                },
                actor_user_id=int(self.current_user["id"]),
            )

            # In edit mode, Amount Paid Now shows paid-to-date; only positive delta is new payment.
            if additional_payment > 0:
                self.inventory_service.record_stock_payment(
                    self.selected_purchase_id,
                    additional_payment,
                    self.purchase_date_var.get(),
                    "Payment added while updating stock purchase",
                    actor_user_id=int(self.current_user["id"]),
                )

            messagebox.showinfo("Purchase Updated", "Stock purchase updated successfully.", parent=self)
            self._reset_purchase_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Update Error", str(exc), parent=self)

    def _delete_purchase(self) -> None:
        if self.selected_purchase_id is None:
            messagebox.showwarning("Select Purchase", "Choose a purchase record to delete first.", parent=self)
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected purchase? This will reverse the stock addition.", parent=self):
            return
        try:
            self.inventory_service.delete_stock_purchase(self.selected_purchase_id)
            self._reset_purchase_form()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Delete Error", str(exc), parent=self)

    def _load_selected_purchase(self, _event=None) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        selection = self.payables_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        self.selected_purchase_id = int(self.payables_tree.item(item_id, "text"))
        purchase = self.inventory_service.get_stock_purchase(self.selected_purchase_id)
        outstanding = purchase["outstanding_amount"]

        # Populate form for editing
        product_key = f"{purchase['product_name']} | {purchase['sku']}"
        if product_key in self.product_lookup:
            self.purchase_product_var.set(product_key)
            # Trigger product selection to populate read-only stock and total amount fields
            self._on_product_selected()
        self.purchase_supplier_var.set(purchase["supplier_name"])
        self.payment_log_supplier_var.set(purchase["supplier_name"])
        self.purchase_date_var.set(purchase["purchase_date"])
        self.purchase_quantity_var.set(str(int(purchase.get("quantity", 0))))
        self.purchase_unit_cost_var.set(self.settings_service.format_money(float(purchase.get("unit_cost", 0)), currency_settings))
        self._recalculate_purchase_total()
        self.purchase_payment_type_var.set(purchase["payment_type"])
        self.loaded_purchase_amount_paid = float(purchase.get("amount_paid", 0))
        self.purchase_amount_paid_var.set(self.settings_service.format_money(self.loaded_purchase_amount_paid, currency_settings))
        self.purchase_notes_var.set(purchase.get("notes", ""))

        # Update button to Edit mode
        self.save_purchase_btn.configure(text="Update Purchase", command=self._update_purchase)

        # Update payment panel
        formatted_outstanding = self.settings_service.format_money(outstanding, currency_settings)
        self.purchase_status_var.set(
            f"Supplier: {purchase['supplier_name']} | Product: {purchase['product_name']} | Purchase Date: {purchase['purchase_date']} | Outstanding: {formatted_outstanding}"
        )
        self.payment_amount_var.set(self.settings_service.format_money(outstanding if outstanding > 0 else 0, currency_settings))
        self.payment_history_list.delete(0, tk.END)
        for payment in self.inventory_service.supplier_payment_history(self.selected_purchase_id):
            formatted_payment = self.settings_service.format_money(payment['amount'], currency_settings)
            self.payment_history_list.insert(
                tk.END,
                f"{payment['payment_date']} | {formatted_payment} | {payment.get('notes') or 'Payment recorded'}",
            )
        self._refresh_supplier_payment_log()

    def _record_payment(self) -> None:
        if self.selected_purchase_id is None:
            messagebox.showwarning("Select Purchase", "Choose a supplier purchase record first.", parent=self)
            return
        try:
            currency_settings = self.settings_service.get_currency_settings()
            self.inventory_service.record_stock_payment(
                self.selected_purchase_id,
                self.settings_service.parse_money(self.payment_amount_var.get(), currency_settings),
                self.payment_date_var.get(),
                self.payment_notes_var.get(),
                actor_user_id=int(self.current_user["id"]),
            )
            messagebox.showinfo("Payment Saved", "Supplier payment recorded successfully.", parent=self)
            self.payment_notes_var.set("")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Payment Error", str(exc), parent=self)

    def refresh(self) -> None:
        try:
            self.inventory_service.ensure_supplier_payables_seeded()
        except Exception:
            pass

        currency_settings = self.settings_service.get_currency_settings()
        products = self.inventory_service.list_products()
        self.product_lookup = {
            f"{product['name']} | {product['sku']}": product
            for product in products
        }
        self.purchase_product_box["values"] = list(self.product_lookup.keys())
        if self.product_lookup and self.purchase_product_var.get() not in self.product_lookup:
            self.purchase_product_var.set(next(iter(self.product_lookup.keys())))
            # Trigger product selection to populate stock and total amount
            self._on_product_selected()

        # Ensure supplier options stay tied to selected product.
        self._on_product_selected()

        suppliers = self.inventory_service.list_suppliers()
        supplier_filter_values = ["All Suppliers", *suppliers]
        self.payment_log_supplier_box["values"] = supplier_filter_values
        if self.payment_log_supplier_var.get() not in supplier_filter_values:
            self.payment_log_supplier_var.set("All Suppliers")

        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)
        for index, expense in enumerate(self.expenses_service.list_expenses()):
            tag = "even" if index % 2 == 0 else "odd"
            self.expense_tree.insert(
                "",
                "end",
                text=str(expense["id"]),
                values=(
                    expense["expense_date"],
                    expense["category"],
                    expense["title"],
                    self.settings_service.format_money(expense["amount"], currency_settings),
                    expense.get("notes") or "-",
                ),
                tags=(tag,),
            )

        month_start = date.today().replace(day=1).isoformat()
        month_end = date.today().isoformat()
        month_total = self.expenses_service.expenses_total(month_start, month_end)
        all_time_total = self.expenses_service.expenses_total()
        self.expenses_month_total_var.set(self.settings_service.format_money(month_total, currency_settings))
        self.expenses_all_time_total_var.set(self.settings_service.format_money(all_time_total, currency_settings))

        for item in self.payables_tree.get_children():
            self.payables_tree.delete(item)
        for purchase in self.inventory_service.list_stock_purchases():
            pending = float(purchase["outstanding_amount"])
            if not self._matches_payables_filter(pending):
                continue
            tag = "pending" if pending > 0 else "settled"
            self.payables_tree.insert(
                "",
                "end",
                text=str(purchase["id"]),
                values=(
                    purchase["supplier_name"],
                    purchase["product_name"],
                    purchase.get("quantity", 0),
                    purchase["purchase_date"],
                    purchase["payment_type"].title(),
                    self.settings_service.format_money(purchase["total_cost"], currency_settings),
                    self.settings_service.format_money(purchase["amount_paid"], currency_settings),
                    self.settings_service.format_money(pending, currency_settings),
                ),
                tags=(tag,),
            )
        self.payables_tree.tag_configure("pending", background="#FAD4D8", foreground="#7F1D1D")
        self.payables_tree.tag_configure("settled", background="#D4EDDA", foreground="#1A6B3C")
        self._refresh_supplier_payment_log()

        if self.selected_purchase_id is not None:
            try:
                currency_settings = self.settings_service.get_currency_settings()
                purchase = self.inventory_service.get_stock_purchase(self.selected_purchase_id)
                outstanding = purchase["outstanding_amount"]
                formatted_outstanding = self.settings_service.format_money(outstanding, currency_settings)
                self.purchase_status_var.set(
                    f"Supplier: {purchase['supplier_name']} | Product: {purchase['product_name']} | Purchase Date: {purchase['purchase_date']} | Outstanding: {formatted_outstanding}"
                )
                self.payment_history_list.delete(0, tk.END)
                for payment in self.inventory_service.supplier_payment_history(self.selected_purchase_id):
                    formatted_payment = self.settings_service.format_money(payment['amount'], currency_settings)
                    self.payment_history_list.insert(
                        tk.END,
                        f"{payment['payment_date']} | {formatted_payment} | {payment.get('notes') or 'Payment recorded'}",
                    )
            except Exception:
                self.selected_purchase_id = None
                self.payment_history_list.delete(0, tk.END)
                self.purchase_status_var.set("Select a stock purchase to manage payments.")

        for callback in self.refresh_callbacks:
            callback()

        self._sync_scrollregion()





