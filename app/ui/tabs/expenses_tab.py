from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from app.ui.widgets import ScrollablePage, make_labeled_entry


class ExpensesTab(ScrollablePage):
    def __init__(self, parent, current_user: dict, expenses_service, inventory_service, settings_service, refresh_callbacks=None) -> None:
        super().__init__(parent, padding=6)
        self.current_user = current_user
        self.expenses_service = expenses_service
        self.inventory_service = inventory_service
        self.settings_service = settings_service
        self.refresh_callbacks = refresh_callbacks or []
        self.selected_expense_id: int | None = None
        self.selected_purchase_id: int | None = None
        self.product_lookup: dict[str, dict] = {}

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Expenses & Suppliers", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(4, 16)
        )
        ttk.Label(
            self.body,
            text="Manage supermarket operating expenses, record new stock purchases, track supplier credit, and settle unpaid balances from one admin workspace.",
            style="Muted.TLabel",
            wraplength=980,
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
        self.expenses_page.columnconfigure(0, weight=2)
        self.expenses_page.columnconfigure(1, weight=1)
        self.expenses_page.rowconfigure(0, weight=1)

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
        ttk.Button(expense_actions, text="Save Expense", style="Primary.TButton", command=self._save_expense).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

    def _build_suppliers_page(self) -> None:
        self.suppliers_page.columnconfigure(0, weight=1)

        self.purchase_form = ttk.LabelFrame(self.suppliers_page, text="Record Stock Purchase", padding=16)
        self.purchase_form.grid(row=0, column=0, sticky="ew")
        self.purchase_form.columnconfigure(0, weight=1)
        self.purchase_form.columnconfigure(1, weight=1)

        self.purchase_product_var = tk.StringVar()
        self.purchase_supplier_var = tk.StringVar()
        self.purchase_date_var = tk.StringVar(value=date.today().isoformat())
        self.purchase_quantity_var = tk.StringVar(value="1")
        self.purchase_unit_cost_var = tk.StringVar(value="0")
        self.purchase_payment_type_var = tk.StringVar(value="cash")
        self.purchase_amount_paid_var = tk.StringVar(value="0")
        self.purchase_notes_var = tk.StringVar()
        self.payment_amount_var = tk.StringVar(value="0")
        self.payment_date_var = tk.StringVar(value=date.today().isoformat())
        self.payment_notes_var = tk.StringVar()

        ttk.Label(self.purchase_form, text="Product", style="FormLabel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.purchase_product_box = ttk.Combobox(self.purchase_form, textvariable=self.purchase_product_var, state="readonly")
        self.purchase_product_box.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        make_labeled_entry(self.purchase_form, "Supplier Name", self.purchase_supplier_var, 0, 1)
        make_labeled_entry(self.purchase_form, "Purchase Date", self.purchase_date_var, 2, 0)
        make_labeled_entry(self.purchase_form, "Quantity", self.purchase_quantity_var, 2, 1)
        make_labeled_entry(self.purchase_form, "Unit Cost", self.purchase_unit_cost_var, 4, 0)

        ttk.Label(self.purchase_form, text="Payment Type", style="FormLabel.TLabel").grid(row=4, column=1, sticky="w", pady=(0, 4))
        self.purchase_payment_box = ttk.Combobox(
            self.purchase_form,
            textvariable=self.purchase_payment_type_var,
            values=("cash", "credit"),
            state="readonly",
        )
        self.purchase_payment_box.grid(row=5, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))
        self.purchase_payment_box.bind("<<ComboboxSelected>>", self._sync_purchase_payment_state)
        make_labeled_entry(self.purchase_form, "Amount Paid Now", self.purchase_amount_paid_var, 6, 0)
        make_labeled_entry(self.purchase_form, "Notes", self.purchase_notes_var, 6, 1, width=36)
        ttk.Button(self.purchase_form, text="Save Stock Purchase", style="Primary.TButton", command=self._save_purchase).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

        self.payables_frame = ttk.LabelFrame(self.suppliers_page, text="Supplier Payables", padding=14)
        self.payables_frame.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        self.payables_frame.columnconfigure(0, weight=1)
        self.payables_frame.rowconfigure(0, weight=1)

        columns = ("supplier", "product", "date", "mode", "total", "paid", "pending")
        self.payables_tree = ttk.Treeview(self.payables_frame, columns=columns, show="headings", height=14)
        for key, title, width in (
            ("supplier", "Supplier", 170),
            ("product", "Product", 180),
            ("date", "Purchase Date", 110),
            ("mode", "Mode", 100),
            ("total", "Total", 120),
            ("paid", "Paid", 120),
            ("pending", "Pending", 120),
        ):
            self.payables_tree.heading(key, text=title)
            self.payables_tree.column(key, width=width, anchor="center")
        self.payables_tree.grid(row=0, column=0, sticky="nsew")
        self.payables_tree.bind("<<TreeviewSelect>>", self._load_selected_purchase)
        payables_y = ttk.Scrollbar(self.payables_frame, orient="vertical", command=self.payables_tree.yview)
        payables_y.grid(row=0, column=1, sticky="ns")
        payables_x = ttk.Scrollbar(self.payables_frame, orient="horizontal", command=self.payables_tree.xview)
        payables_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
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
        make_labeled_entry(self.payment_panel, "Payment Notes", self.payment_notes_var, 3, 0, width=40)
        ttk.Button(self.payment_panel, text="Record Payment", style="Primary.TButton", command=self._record_payment).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

        self.payment_history_list = tk.Listbox(self.payment_panel, height=5, relief="flat", font=("Segoe UI", 10))
        self.payment_history_list.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        self._sync_purchase_payment_state()

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        self.expense_grid.grid_forget()
        self.expense_form.grid_forget()

        if width >= 1260:
            self.expense_grid.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            self.expense_form.grid(row=0, column=1, sticky="nsew")
        else:
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

    def _sync_purchase_payment_state(self, _event=None) -> None:
        payment_type = self.purchase_payment_type_var.get() or "cash"
        if payment_type == "cash":
            try:
                total_cost = float(self.purchase_quantity_var.get() or 0) * float(self.purchase_unit_cost_var.get() or 0)
            except ValueError:
                total_cost = 0
            self.purchase_amount_paid_var.set(f"{total_cost:.2f}")
        elif not self.purchase_amount_paid_var.get():
            self.purchase_amount_paid_var.set("0")

    def _selected_product_id(self) -> int | None:
        product = self.product_lookup.get(self.purchase_product_var.get())
        return int(product["id"]) if product else None

    def _load_selected_expense(self, _event=None) -> None:
        selection = self.expense_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        self.selected_expense_id = int(self.expense_tree.item(item_id, "text"))

    def _reset_expense_form(self) -> None:
        self.selected_expense_id = None
        self.expense_date_var.set(date.today().isoformat())
        self.expense_category_var.set("")
        self.expense_title_var.set("")
        self.expense_amount_var.set("0")
        self.expense_notes_var.set("")
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
            self.inventory_service.create_stock_purchase(
                {
                    "product_id": product_id,
                    "supplier_name": self.purchase_supplier_var.get(),
                    "purchase_date": self.purchase_date_var.get(),
                    "quantity": self.purchase_quantity_var.get(),
                    "unit_cost": self.purchase_unit_cost_var.get(),
                    "payment_type": self.purchase_payment_type_var.get(),
                    "amount_paid": self.purchase_amount_paid_var.get(),
                    "notes": self.purchase_notes_var.get(),
                },
                actor_user_id=int(self.current_user["id"]),
            )
            messagebox.showinfo("Stock Purchase Saved", "Stock purchase recorded and inventory updated successfully.", parent=self)
            self.purchase_supplier_var.set("")
            self.purchase_quantity_var.set("1")
            self.purchase_unit_cost_var.set("0")
            self.purchase_amount_paid_var.set("0")
            self.purchase_notes_var.set("")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Purchase Error", str(exc), parent=self)

    def _load_selected_purchase(self, _event=None) -> None:
        selection = self.payables_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        self.selected_purchase_id = int(self.payables_tree.item(item_id, "text"))
        purchase = self.inventory_service.get_stock_purchase(self.selected_purchase_id)
        outstanding = purchase["outstanding_amount"]
        self.purchase_status_var.set(
            f"Supplier: {purchase['supplier_name']} | Product: {purchase['product_name']} | Purchase Date: {purchase['purchase_date']} | Outstanding: {outstanding:.2f}"
        )
        self.payment_amount_var.set(str(outstanding if outstanding > 0 else 0))
        self.payment_history_list.delete(0, tk.END)
        for payment in self.inventory_service.supplier_payment_history(self.selected_purchase_id):
            self.payment_history_list.insert(
                tk.END,
                f"{payment['payment_date']} | {payment['amount']:.2f} | {payment.get('notes') or 'Payment recorded'}",
            )

    def _record_payment(self) -> None:
        if self.selected_purchase_id is None:
            messagebox.showwarning("Select Purchase", "Choose a supplier purchase record first.", parent=self)
            return
        try:
            self.inventory_service.record_stock_payment(
                self.selected_purchase_id,
                float(self.payment_amount_var.get()),
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
        currency_settings = self.settings_service.get_currency_settings()
        products = self.inventory_service.list_products()
        self.product_lookup = {
            f"{product['name']} | {product['sku']}": product
            for product in products
        }
        self.purchase_product_box["values"] = list(self.product_lookup.keys())
        if self.product_lookup and self.purchase_product_var.get() not in self.product_lookup:
            self.purchase_product_var.set(next(iter(self.product_lookup.keys())))

        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)
        for expense in self.expenses_service.list_expenses():
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
            )

        for item in self.payables_tree.get_children():
            self.payables_tree.delete(item)
        for purchase in self.inventory_service.list_stock_purchases():
            pending = float(purchase["outstanding_amount"])
            tag = "pending" if pending > 0 else "settled"
            self.payables_tree.insert(
                "",
                "end",
                text=str(purchase["id"]),
                values=(
                    purchase["supplier_name"],
                    purchase["product_name"],
                    purchase["purchase_date"],
                    purchase["payment_type"].title(),
                    self.settings_service.format_money(purchase["total_cost"], currency_settings),
                    self.settings_service.format_money(purchase["amount_paid"], currency_settings),
                    self.settings_service.format_money(pending, currency_settings),
                ),
                tags=(tag,),
            )
        self.payables_tree.tag_configure("pending", background="#FFF1CD")
        self.payables_tree.tag_configure("settled", background="#E7F4EA")

        if self.selected_purchase_id is not None:
            try:
                purchase = self.inventory_service.get_stock_purchase(self.selected_purchase_id)
                outstanding = purchase["outstanding_amount"]
                self.purchase_status_var.set(
                    f"Supplier: {purchase['supplier_name']} | Product: {purchase['product_name']} | Purchase Date: {purchase['purchase_date']} | Outstanding: {outstanding:.2f}"
                )
                self.payment_history_list.delete(0, tk.END)
                for payment in self.inventory_service.supplier_payment_history(self.selected_purchase_id):
                    self.payment_history_list.insert(
                        tk.END,
                        f"{payment['payment_date']} | {payment['amount']:.2f} | {payment.get('notes') or 'Payment recorded'}",
                    )
            except Exception:
                self.selected_purchase_id = None
                self.payment_history_list.delete(0, tk.END)
                self.purchase_status_var.set("Select a stock purchase to manage payments.")

        for callback in self.refresh_callbacks:
            callback()

        self._sync_scrollregion()




