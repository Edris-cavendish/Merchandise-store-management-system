from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.ui.widgets import ScrollablePage, make_labeled_entry


class InventoryTab(ScrollablePage):
    def __init__(self, parent, inventory_service, settings_service) -> None:
        super().__init__(parent, padding=6)
        self.inventory_service = inventory_service
        self.settings_service = settings_service
        self.selected_product_id: int | None = None
        self.category_lookup: dict[str, int] = {}

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Inventory Control Center", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(4, 16)
        )

        ttk.Label(
            self.body,
            text="Track products, cost prices, selling prices, suppliers, stock levels, and the latest cash or credit purchase status from one responsive workspace.",
            style="Muted.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.main_panel = ttk.Frame(self.body, style="App.TFrame")
        self.main_panel.grid(row=2, column=0, sticky="nsew")
        self.main_panel.columnconfigure(0, weight=2)
        self.main_panel.columnconfigure(1, weight=1)
        self.main_panel.rowconfigure(0, weight=1)

        self._build_grid()
        self._build_form()
        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh()

    def _build_grid(self) -> None:
        self.catalog_panel = ttk.LabelFrame(self.main_panel, text="Product Catalog", padding=14)
        self.catalog_panel.columnconfigure(0, weight=1)
        self.catalog_panel.rowconfigure(0, weight=1)

        columns = ("sku", "name", "supplier", "category", "cost", "price", "stock", "purchase", "pending")
        self.tree = ttk.Treeview(self.catalog_panel, columns=columns, show="headings", height=16)
        headings = {
            "sku": ("SKU", 100),
            "name": ("Product", 200),
            "supplier": ("Supplier", 170),
            "category": ("Category", 130),
            "cost": ("Cost Price", 120),
            "price": ("Unit Price", 120),
            "stock": ("Stock", 80),
            "purchase": ("Last Purchase", 120),
            "pending": ("Pending", 120),
        }
        for key, (title, width) in headings.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)

        scrollbar_y = ttk.Scrollbar(self.catalog_panel, orient="vertical", command=self.tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x = ttk.Scrollbar(self.catalog_panel, orient="horizontal", command=self.tree.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    def _build_form(self) -> None:
        self.form_panel = ttk.LabelFrame(self.main_panel, text="Add or Update Product", padding=16)
        for index in range(2):
            self.form_panel.columnconfigure(index, weight=1)

        self.sku_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.cost_price_var = tk.StringVar(value="0")
        self.price_var = tk.StringVar(value="0")
        self.stock_var = tk.StringVar(value="0")
        self.threshold_var = tk.StringVar(value="5")
        self.description_var = tk.StringVar()
        self.new_category_var = tk.StringVar()

        make_labeled_entry(self.form_panel, "SKU", self.sku_var, 0, 0)
        make_labeled_entry(self.form_panel, "Product Name", self.name_var, 0, 1)

        ttk.Label(self.form_panel, text="Category", style="FormLabel.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.category_box = ttk.Combobox(self.form_panel, textvariable=self.category_var, state="readonly")
        self.category_box.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        make_labeled_entry(self.form_panel, "Supplier", self.supplier_var, 2, 1)
        make_labeled_entry(self.form_panel, "Cost Price", self.cost_price_var, 4, 0)
        make_labeled_entry(self.form_panel, "Unit Price", self.price_var, 4, 1)
        make_labeled_entry(self.form_panel, "Stock Quantity", self.stock_var, 6, 0)
        make_labeled_entry(self.form_panel, "Low Stock Threshold", self.threshold_var, 6, 1)
        make_labeled_entry(self.form_panel, "Description", self.description_var, 8, 0, width=38)

        ttk.Label(
            self.form_panel,
            text="Use the Expenses & Suppliers tab to record stock purchases, credit balances, and supplier payments. Inventory shows the latest purchase mode and pending amount.",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=10, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Separator(self.form_panel, orient="horizontal").grid(row=11, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Label(self.form_panel, text="Quick Category Add", style="Section.TLabel").grid(
            row=12, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        make_labeled_entry(self.form_panel, "New Category Name", self.new_category_var, 13, 0)
        ttk.Button(self.form_panel, text="Add Category", style="Secondary.TButton", command=self._create_category).grid(
            row=14, column=1, sticky="ew", pady=(18, 10)
        )

        actions = ttk.Frame(self.form_panel, style="Surface.TFrame")
        actions.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(actions, text="Clear", style="Secondary.TButton", command=self._reset_form).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(actions, text="Delete", style="Secondary.TButton", command=self._delete_product).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(actions, text="Save Product", style="Primary.TButton", command=self._save_product).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        self.catalog_panel.grid_forget()
        self.form_panel.grid_forget()

        if width >= 1260:
            self.main_panel.columnconfigure(0, weight=2)
            self.main_panel.columnconfigure(1, weight=1)
            self.catalog_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            self.form_panel.grid(row=0, column=1, sticky="nsew")
        else:
            self.main_panel.columnconfigure(0, weight=1)
            self.main_panel.columnconfigure(1, weight=0)
            self.catalog_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
            self.form_panel.grid(row=1, column=0, sticky="nsew")

        self._sync_scrollregion()

    def _category_id(self) -> int | None:
        return self.category_lookup.get(self.category_var.get())

    def _validate_product_payload(self) -> dict:
        if not self.sku_var.get().strip() or not self.name_var.get().strip():
            raise ValueError("SKU and product name are required.")
        try:
            cost_price = float(self.cost_price_var.get())
            unit_price = float(self.price_var.get())
            stock_qty = int(self.stock_var.get())
            threshold = int(self.threshold_var.get())
        except ValueError as exc:
            raise ValueError("Cost price, unit price, stock quantity, and threshold must be valid numbers.") from exc
        if cost_price < 0 or unit_price < 0 or stock_qty < 0 or threshold < 0:
            raise ValueError("Numeric values cannot be negative.")
        return {
            "sku": self.sku_var.get().strip(),
            "name": self.name_var.get().strip(),
            "category_id": self._category_id(),
            "supplier": self.supplier_var.get().strip(),
            "cost_price": cost_price,
            "unit_price": unit_price,
            "stock_qty": stock_qty,
            "low_stock_threshold": threshold,
            "description": self.description_var.get().strip(),
        }

    def _save_product(self) -> None:
        try:
            payload = self._validate_product_payload()
            if self.selected_product_id is None:
                self.inventory_service.create_product(payload)
                messagebox.showinfo("Saved", "Product created successfully.", parent=self)
            else:
                self.inventory_service.update_product(self.selected_product_id, payload)
                messagebox.showinfo("Updated", "Product updated successfully.", parent=self)
            self.refresh()
            self._reset_form()
        except Exception as exc:
            messagebox.showerror("Product Error", str(exc), parent=self)

    def _delete_product(self) -> None:
        if self.selected_product_id is None:
            messagebox.showwarning("Select Product", "Choose a product to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected product?", parent=self):
            return
        try:
            self.inventory_service.delete_product(self.selected_product_id)
            self.refresh()
            self._reset_form()
        except Exception as exc:
            messagebox.showerror("Delete Error", str(exc), parent=self)

    def _create_category(self) -> None:
        name = self.new_category_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Category", "Enter a category name first.", parent=self)
            return
        try:
            self.inventory_service.create_category(name)
            self.new_category_var.set("")
            self.refresh()
            self.category_var.set(name)
        except Exception as exc:
            messagebox.showerror("Category Error", str(exc), parent=self)

    def _load_selected(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        product_id = int(self.tree.item(item_id, "text"))
        product = next((row for row in self.inventory_service.list_products() if row["id"] == product_id), None)
        if product is None:
            return

        self.selected_product_id = product_id
        self.sku_var.set(product["sku"])
        self.name_var.set(product["name"])
        self.category_var.set(product.get("category_name") or "")
        self.supplier_var.set(product.get("supplier") or "")
        self.cost_price_var.set(str(product.get("cost_price") or 0))
        self.price_var.set(str(product["unit_price"]))
        self.stock_var.set(str(product["stock_qty"]))
        self.threshold_var.set(str(product["low_stock_threshold"]))
        self.description_var.set(product.get("description") or "")

    def _reset_form(self) -> None:
        self.selected_product_id = None
        for variable in (
            self.sku_var,
            self.name_var,
            self.category_var,
            self.supplier_var,
            self.cost_price_var,
            self.price_var,
            self.stock_var,
            self.description_var,
        ):
            variable.set("")
        self.cost_price_var.set("0")
        self.price_var.set("0")
        self.stock_var.set("0")
        self.threshold_var.set("5")
        for selected in self.tree.selection():
            self.tree.selection_remove(selected)

    def refresh(self) -> None:
        categories = self.inventory_service.list_categories()
        currency_settings = self.settings_service.get_currency_settings()
        self.category_lookup = {category["name"]: category["id"] for category in categories}
        self.category_box["values"] = list(self.category_lookup.keys())

        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self.inventory_service.list_products():
            self.tree.insert(
                "",
                "end",
                text=str(product["id"]),
                values=(
                    product["sku"],
                    product["name"],
                    product.get("supplier") or "-",
                    product.get("category_name") or "Uncategorized",
                    self.settings_service.format_money(product.get("cost_price") or 0, currency_settings),
                    self.settings_service.format_money(product["unit_price"], currency_settings),
                    product["stock_qty"],
                    (product.get("last_payment_type") or "-").title() if product.get("last_payment_type") else "-",
                    self.settings_service.format_money(product.get("last_pending_amount") or 0, currency_settings),
                ),
            )
