from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.ui.widgets import ScrollablePage, make_labeled_entry, apply_treeview_stripes, repopulate_with_stripes


class InventoryTab(ScrollablePage):
    def __init__(self, parent, inventory_service, settings_service) -> None:
        super().__init__(parent, padding=14)
        self.inventory_service = inventory_service
        self.settings_service = settings_service
        self.selected_product_id: int | None = None
        self.category_lookup: dict[str, int] = {}
        self._all_products: list[dict] = []

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Inventory Control Center", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            self.body,
            text="Track products, cost prices, selling prices, suppliers, stock levels, and the latest purchase status.",
            style="MutedBg.TLabel",
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Search bar
        search_bar = ttk.Frame(self.body, style="App.TFrame")
        search_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        search_bar.columnconfigure(1, weight=1)
        ttk.Label(search_bar, text="🔍  Search", style="FormLabelBg.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        ttk.Entry(search_bar, textvariable=self.search_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(search_bar, text="Clear", style="Secondary.TButton", command=self._clear_search).grid(
            row=0, column=2, padx=(8, 0)
        )

        self.main_panel = ttk.Frame(self.body, style="App.TFrame")
        self.main_panel.grid(row=3, column=0, sticky="nsew")
        self.main_panel.columnconfigure(0, weight=2)
        self.main_panel.columnconfigure(1, weight=1)
        self.main_panel.rowconfigure(0, weight=1)

        self._build_grid()
        self._build_form()
        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh()

    # ── Product catalogue ─────────────────────────────────────────────────────

    def _build_grid(self) -> None:
        self.catalog_panel = ttk.LabelFrame(self.main_panel, text="Product Catalogue", padding=14)
        self.catalog_panel.columnconfigure(0, weight=1)
        self.catalog_panel.rowconfigure(0, weight=1)

        columns = ("sku", "name", "supplier", "category", "cost", "price", "stock", "unit", "purchase", "pending")
        self.tree = ttk.Treeview(self.catalog_panel, columns=columns, show="headings", height=16)
        headings = {
            "sku":      ("SKU",          100),
            "name":     ("Product",      200),
            "supplier": ("Supplier",     170),
            "category": ("Category",     130),
            "cost":     ("Cost Price",   120),
            "price":    ("Unit Price",   120),
            "stock":    ("Stock",         80),
            "unit":     ("Unit",          80),
            "purchase": ("Last Purchase",120),
            "pending":  ("Pending",      120),
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

    # ── Form ──────────────────────────────────────────────────────────────────

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
        self.unit_var = tk.StringVar(value="pcs")
        self.new_category_var = tk.StringVar()
        self._original_category_name: str = ""

        # ── Group 1: Identification ────────────────────────────────────────────
        ttk.Label(self.form_panel, text="IDENTIFICATION", style="Kicker.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        # SKU - read-only, auto-generated based on category
        ttk.Label(self.form_panel, text="SKU", style="FormLabel.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 3))
        self.sku_entry = ttk.Entry(self.form_panel, textvariable=self.sku_var, state="readonly", width=18)
        self.sku_entry.grid(row=2, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        make_labeled_entry(self.form_panel, "Product Name", self.name_var, 1, 1)

        ttk.Label(self.form_panel, text="Category", style="FormLabel.TLabel").grid(row=3, column=0, sticky="w", pady=(0, 3))
        self.category_box = ttk.Combobox(self.form_panel, textvariable=self.category_var, state="readonly")
        self.category_box.grid(row=4, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        self.category_box.bind("<<ComboboxSelected>>", self._on_category_selected)
        make_labeled_entry(self.form_panel, "Supplier", self.supplier_var, 3, 1)

        # ── Group 2: Pricing ───────────────────────────────────────────────────
        ttk.Separator(self.form_panel, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        ttk.Label(self.form_panel, text="PRICING", style="Kicker.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        make_labeled_entry(self.form_panel, "Cost Price", self.cost_price_var, 7, 0)
        make_labeled_entry(self.form_panel, "Unit Price", self.price_var, 7, 1)

        # ── Group 3: Stock ─────────────────────────────────────────────────────
        ttk.Separator(self.form_panel, orient="horizontal").grid(row=9, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        ttk.Label(self.form_panel, text="STOCK MANAGEMENT", style="Kicker.TLabel").grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        make_labeled_entry(self.form_panel, "Stock Quantity", self.stock_var, 11, 0)
        make_labeled_entry(self.form_panel, "Low Stock Threshold", self.threshold_var, 11, 1)
        make_labeled_entry(self.form_panel, "Description", self.description_var, 13, 0, width=38)

        ttk.Label(self.form_panel, text="Measurement Unit", style="FormLabel.TLabel").grid(
            row=13, column=1, sticky="w", pady=(0, 3)
        )
        self.unit_box = ttk.Combobox(self.form_panel, textvariable=self.unit_var, state="readonly")
        self.unit_box.grid(row=14, column=1, sticky="ew", pady=(0, 10))

        ttk.Label(
            self.form_panel,
            text="Use Expenses & Suppliers to record stock purchases. Inventory shows the latest purchase mode and pending amount.",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=15, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # ── Quick category add ─────────────────────────────────────────────────
        ttk.Separator(self.form_panel, orient="horizontal").grid(row=16, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        ttk.Label(self.form_panel, text="QUICK CATEGORY", style="Kicker.TLabel").grid(
            row=17, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        make_labeled_entry(self.form_panel, "New Category Name", self.new_category_var, 18, 0)
        ttk.Button(self.form_panel, text="Add Category", style="Secondary.TButton", command=self._create_category).grid(
            row=19, column=1, sticky="ew", pady=(0, 10)
        )

        # ── Action buttons ─────────────────────────────────────────────────────
        ttk.Separator(self.form_panel, orient="horizontal").grid(row=20, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        actions = ttk.Frame(self.form_panel, style="Surface.TFrame")
        actions.grid(row=21, column=0, columnspan=2, sticky="ew")
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

    # ── Search ────────────────────────────────────────────────────────────────

    def _on_search(self, *_args) -> None:
        self._render_tree(self._all_products)

    def _clear_search(self) -> None:
        self.search_var.set("")

    def _render_tree(self, products: list[dict]) -> None:
        query = self.search_var.get().strip().lower()
        currency_settings = self.settings_service.get_currency_settings()
        for item in self.tree.get_children():
            self.tree.delete(item)
        index = 0
        for product in products:
            if query and query not in (product["name"] + product["sku"] + (product.get("supplier") or "")).lower():
                continue
            tag = "even" if index % 2 == 0 else "odd"
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
                    product.get("measurement_unit") or "-",
                    (product.get("last_payment_type") or "-").title() if product.get("last_payment_type") else "-",
                    self.settings_service.format_money(product.get("last_pending_amount") or 0, currency_settings),
                ),
                tags=(tag,),
            )
            index += 1

    # ── Layout ────────────────────────────────────────────────────────────────

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

    # ── Palette ───────────────────────────────────────────────────────────────

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        apply_treeview_stripes(self.tree, palette)

    # ── Form helpers ──────────────────────────────────────────────────────────

    def _category_id(self) -> int | None:
        return self.category_lookup.get(self.category_var.get())

    def _on_category_selected(self, _event=None) -> None:
        """Auto-generate SKU when category is selected.

        For new products: always generate a SKU for the chosen category.
        For existing products: regenerate the SKU only when the category
        actually changed, so the prefix stays consistent with the category.
        """
        category_name = self.category_var.get()
        if not category_name:
            return
        category_id = self.category_lookup.get(category_name)
        if category_id is None:
            return

        if self.selected_product_id is not None:
            # Editing — only regenerate when the category truly changed.
            if category_name == self._original_category_name:
                return
            # Pass the current SKU so its slot is treated as free in the
            # new category's prefix range (handles same-prefix edge case).
            current_sku = self.sku_var.get().strip() or None
        else:
            current_sku = None

        try:
            sku = self.inventory_service.generate_sku_for_category(
                category_id, category_name, exclude_sku=current_sku
            )
            self.sku_var.set(sku)
        except Exception:
            pass

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
            "measurement_unit": self.unit_var.get().strip() or "pcs",
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

    def _migrate_skus(self) -> None:
        """Run SKU migration to convert all existing SKUs to new format."""
        if not messagebox.askyesno(
            "Confirm Migration",
            "This will convert ALL existing product SKUs to the new category-based format (e.g., BEV-001).\n\n"
            "The changes cannot be undone. Make sure you have a backup if needed.\n\n"
            "Continue?",
            parent=self
        ):
            return
        try:
            changes = self.inventory_service.migrate_skus_to_new_format()
            self.refresh()
            if changes:
                summary = "\n".join([f"{name}: {old} → {new}" for name, old, new in changes[:20]])
                if len(changes) > 20:
                    summary += f"\n... and {len(changes) - 20} more"
                messagebox.showinfo(
                    "Migration Complete",
                    f"Successfully migrated {len(changes)} products:\n\n{summary}",
                    parent=self
                )
            else:
                messagebox.showinfo("Migration Complete", "All SKUs are already in the correct format.", parent=self)
        except Exception as exc:
            messagebox.showerror("Migration Error", str(exc), parent=self)

    def _load_selected(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        product_id = int(self.tree.item(item_id, "text"))
        product = next((row for row in self._all_products if row["id"] == product_id), None)
        if product is None:
            return
        self.selected_product_id = product_id
        self.sku_var.set(product["sku"])
        self.name_var.set(product["name"])
        self.category_var.set(product.get("category_name") or "")
        self._original_category_name = product.get("category_name") or ""
        self.supplier_var.set(product.get("supplier") or "")
        self.cost_price_var.set(str(product.get("cost_price") or 0))
        self.price_var.set(str(product["unit_price"]))
        self.stock_var.set(str(product["stock_qty"]))
        self.threshold_var.set(str(product["low_stock_threshold"]))
        self.description_var.set(product.get("description") or "")
        self.unit_var.set(product.get("measurement_unit") or "pcs")

    def _reset_form(self) -> None:
        self.selected_product_id = None
        self._original_category_name = ""
        for variable in (self.sku_var, self.name_var, self.category_var, self.supplier_var, self.description_var):
            variable.set("")
        self.cost_price_var.set("0")
        self.price_var.set("0")
        self.stock_var.set("0")
        self.threshold_var.set("5")
        self.unit_var.set("pcs")
        for selected in self.tree.selection():
            self.tree.selection_remove(selected)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        categories = self.inventory_service.list_categories()
        self.category_lookup = {category["name"]: category["id"] for category in categories}
        self.category_box["values"] = list(self.category_lookup.keys())
        units = self.settings_service.get_measurement_units()
        self.unit_box["values"] = units
        if self.unit_var.get() not in units and units:
            self.unit_var.set(units[0])
        self._all_products = self.inventory_service.list_products()
        self._render_tree(self._all_products)
