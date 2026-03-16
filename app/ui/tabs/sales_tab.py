from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.config import DEFAULT_VAT_RATE
from app.ui.widgets import ScrollablePage, make_labeled_entry, apply_treeview_stripes


class SalesTab(ScrollablePage):
    def __init__(
        self,
        parent,
        inventory_service,
        sales_service,
        settings_service,
        current_user,
        store_name: str,
        refresh_callbacks=None,
    ) -> None:
        super().__init__(parent, padding=14)
        self.inventory_service = inventory_service
        self.sales_service = sales_service
        self.settings_service = settings_service
        self.current_user = current_user
        self.refresh_callbacks = refresh_callbacks or []
        self.cart: list[dict] = []
        self.product_lookup: dict[str, dict] = {}
        self.current_receipt: dict | None = None
        self.current_totals = {"subtotal": 0.0, "discount_amount": 0.0, "tax_amount": 0.0, "total": 0.0}
        self.store_name_var = tk.StringVar(value=store_name)

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Sales & Billing Studio", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        self.main_panel = ttk.Frame(self.body, style="App.TFrame")
        self.main_panel.grid(row=1, column=0, sticky="nsew")
        self.main_panel.columnconfigure(0, weight=3)
        self.main_panel.columnconfigure(1, weight=2)

        self._build_product_panel()
        self._build_checkout_panel()
        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh_products()
        self.refresh_currency_view()

    # ── Cart panel (left) ─────────────────────────────────────────────────────

    def _build_product_panel(self) -> None:
        self.catalog_panel = ttk.LabelFrame(self.main_panel, text="Point of Sale — Cart", padding=14)
        self.catalog_panel.columnconfigure(0, weight=2)
        self.catalog_panel.columnconfigure(1, weight=1)
        self.catalog_panel.columnconfigure(2, weight=0)
        self.catalog_panel.rowconfigure(2, weight=1)

        self.product_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.discount_var = tk.StringVar(value="0")
        self.tax_var = tk.StringVar(value=f"{DEFAULT_VAT_RATE:.2f}")
        self.payment_var = tk.StringVar(value="Cash")

        ttk.Label(self.catalog_panel, text="Product", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 3)
        )
        ttk.Label(self.catalog_panel, text="Qty", style="FormLabel.TLabel").grid(
            row=0, column=1, sticky="w", pady=(0, 3)
        )
        self.product_box = ttk.Combobox(self.catalog_panel, textvariable=self.product_var, state="readonly")
        self.product_box.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))
        ttk.Entry(self.catalog_panel, textvariable=self.quantity_var, width=10).grid(
            row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 10)
        )
        ttk.Button(
            self.catalog_panel, text="  Add to Cart  ", style="Primary.TButton", command=self._add_to_cart
        ).grid(row=1, column=2, sticky="ew", pady=(0, 10))

        columns = ("name", "price", "qty", "total")
        self.cart_tree = ttk.Treeview(self.catalog_panel, columns=columns, show="headings", height=14)
        for key, title, width in (
            ("name",  "Item",       220),
            ("price", "Unit Price", 130),
            ("qty",   "Qty",         70),
            ("total", "Line Total", 140),
        ):
            self.cart_tree.heading(key, text=title)
            self.cart_tree.column(key, width=width, anchor="center")
        self.cart_tree.grid(row=2, column=0, columnspan=3, sticky="nsew")
        cart_y = ttk.Scrollbar(self.catalog_panel, orient="vertical", command=self.cart_tree.yview)
        cart_y.grid(row=2, column=3, sticky="ns")
        cart_x = ttk.Scrollbar(self.catalog_panel, orient="horizontal", command=self.cart_tree.xview)
        cart_x.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.cart_tree.configure(yscrollcommand=cart_y.set, xscrollcommand=cart_x.set)

        action_row = ttk.Frame(self.catalog_panel, style="Surface.TFrame")
        action_row.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        ttk.Button(action_row, text="Remove Selected", style="Secondary.TButton", command=self._remove_selected).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(action_row, text="Clear Cart", style="Secondary.TButton", command=self._clear_cart).pack(
            side="left", fill="x", expand=True
        )

    # ── Checkout panel (right) ────────────────────────────────────────────────

    def _build_checkout_panel(self) -> None:
        self.checkout_panel = ttk.LabelFrame(self.main_panel, text="Checkout Summary", padding=16)
        self.checkout_panel.columnconfigure(0, weight=1)

        ttk.Label(self.checkout_panel, textvariable=self.store_name_var, style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            self.checkout_panel,
            text="Fast totals, tax, discounts, and exportable receipts.",
            style="Muted.TLabel",
            wraplength=400,
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        # -- Discount / Tax / Payment fields --
        form = ttk.Frame(self.checkout_panel, style="Surface.TFrame")
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure((0, 1), weight=1)
        make_labeled_entry(form, "Discount Amount", self.discount_var, 0, 0)
        make_labeled_entry(form, "Tax Rate (0.00–1.00)", self.tax_var, 0, 1)

        ttk.Label(form, text="Payment Method", style="FormLabel.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 3)
        )
        ttk.Combobox(
            form,
            textvariable=self.payment_var,
            values=("Cash", "Mobile Money", "Card"),
            state="readonly",
        ).grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 12))
        ttk.Button(form, text="Recalculate", style="Secondary.TButton", command=self._update_totals).grid(
            row=3, column=1, sticky="ew", pady=(0, 12)
        )

        # -- Totals summary card --
        summary = ttk.Frame(self.checkout_panel, style="Card.TFrame", padding=16)
        summary.grid(row=4, column=0, sticky="ew", pady=(8, 14))
        summary.columnconfigure(1, weight=1)

        self.subtotal_var = tk.StringVar(value="")
        self.discount_amount_var = tk.StringVar(value="")
        self.tax_amount_var = tk.StringVar(value="")
        self.total_var = tk.StringVar(value="")

        rows = (
            ("Subtotal", self.subtotal_var, "CardTitle.TLabel", "CardTitle.TLabel"),
            ("Discount", self.discount_amount_var, "CardTitle.TLabel", "CardTitle.TLabel"),
            ("Tax", self.tax_amount_var, "CardTitle.TLabel", "CardTitle.TLabel"),
            ("TOTAL", self.total_var, "CardTitle.TLabel", "CardValue.TLabel"),
        )
        for row_index, (label, variable, label_style, value_style) in enumerate(rows):
            ttk.Label(summary, text=label, style=label_style).grid(row=row_index, column=0, sticky="w", pady=4)
            ttk.Label(summary, textvariable=variable, style=value_style).grid(
                row=row_index, column=1, sticky="e", pady=4
            )

        # -- Action buttons --
        ttk.Button(
            self.checkout_panel, text="✔  Complete Sale", style="Primary.TButton", command=self._checkout
        ).grid(row=5, column=0, sticky="ew")
        ttk.Button(
            self.checkout_panel, text="Save Receipt to File", style="Secondary.TButton", command=self._save_receipt
        ).grid(row=6, column=0, sticky="ew", pady=(10, 16))

        # -- Receipt preview --
        ttk.Label(self.checkout_panel, text="Receipt Preview", style="Section.TLabel").grid(
            row=7, column=0, sticky="w"
        )
        self.preview = tk.Text(
            self.checkout_panel,
            height=18,
            relief="flat",
            font=("Consolas", 10),
            wrap="none",
        )
        self.preview.grid(row=8, column=0, sticky="nsew")
        preview_y = ttk.Scrollbar(self.checkout_panel, orient="vertical", command=self.preview.yview)
        preview_y.grid(row=8, column=1, sticky="ns")
        preview_x = ttk.Scrollbar(self.checkout_panel, orient="horizontal", command=self.preview.xview)
        preview_x.grid(row=9, column=0, sticky="ew", pady=(6, 0))
        self.preview.configure(yscrollcommand=preview_y.set, xscrollcommand=preview_x.set)
        self.checkout_panel.rowconfigure(8, weight=1)

    # ── Responsive layout ─────────────────────────────────────────────────────

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        self.catalog_panel.grid_forget()
        self.checkout_panel.grid_forget()
        if width >= 1280:
            self.main_panel.columnconfigure(0, weight=3)
            self.main_panel.columnconfigure(1, weight=2)
            self.catalog_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            self.checkout_panel.grid(row=0, column=1, sticky="nsew")
        else:
            self.main_panel.columnconfigure(0, weight=1)
            self.main_panel.columnconfigure(1, weight=0)
            self.catalog_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
            self.checkout_panel.grid(row=1, column=0, sticky="nsew")
        self._sync_scrollregion()

    # ── Palette ───────────────────────────────────────────────────────────────

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        self.preview.configure(
            bg=palette["entry"],
            fg=palette["text"],
            insertbackground=palette["text"],
            selectbackground=palette["accent"],
            selectforeground=palette["hero_text"],
            highlightthickness=0,
            borderwidth=0,
        )
        apply_treeview_stripes(self.cart_tree, palette)

    def update_store_name(self, store_name: str) -> None:
        self.store_name_var.set(store_name)

    def refresh_currency_view(self) -> None:
        self._update_total_labels(self.current_totals)
        self._render_cart(refresh_totals=False)

    # ── Cart logic ────────────────────────────────────────────────────────────

    def _selected_product(self) -> dict:
        product_name = self.product_var.get()
        product = self.product_lookup.get(product_name)
        if product is None:
            raise ValueError("Select a valid product.")
        return product

    def _add_to_cart(self) -> None:
        try:
            product = self._selected_product()
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
            if quantity > int(product["stock_qty"]):
                raise ValueError("Requested quantity exceeds available stock.")
            existing = next((item for item in self.cart if item["product_id"] == product["id"]), None)
            if existing:
                if existing["quantity"] + quantity > int(product["stock_qty"]):
                    raise ValueError("Combined cart quantity exceeds available stock.")
                existing["quantity"] += quantity
            else:
                self.cart.append(
                    {
                        "product_id": product["id"],
                        "name": product["name"],
                        "quantity": quantity,
                        "unit_price": float(product["unit_price"]),
                    }
                )
            self.quantity_var.set("1")
            self._render_cart()
        except Exception as exc:
            messagebox.showerror("Cart Error", str(exc), parent=self)

    def _remove_selected(self) -> None:
        selection = self.cart_tree.selection()
        if not selection:
            messagebox.showwarning("Select Item", "Choose a cart item to remove.", parent=self)
            return
        cart_index = int(self.cart_tree.item(selection[0], "text"))
        self.cart.pop(cart_index)
        self._render_cart()

    def _clear_cart(self) -> None:
        self.cart.clear()
        self.current_receipt = None
        self.current_totals = {"subtotal": 0.0, "discount_amount": 0.0, "tax_amount": 0.0, "total": 0.0}
        self._render_cart(refresh_totals=False)
        self._update_total_labels(self.current_totals)
        self.preview.delete("1.0", tk.END)

    def _update_total_labels(self, totals: dict) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        self.subtotal_var.set(self.settings_service.format_money(totals["subtotal"], currency_settings))
        self.discount_amount_var.set(self.settings_service.format_money(totals["discount_amount"], currency_settings))
        self.tax_amount_var.set(self.settings_service.format_money(totals["tax_amount"], currency_settings))
        self.total_var.set(self.settings_service.format_money(totals["total"], currency_settings))

    def _update_totals(self) -> None:
        try:
            discount = float(self.discount_var.get())
            tax_rate = float(self.tax_var.get())
            self.current_totals = self.sales_service.calculate_totals(self.cart, discount, tax_rate)
            self._update_total_labels(self.current_totals)
        except Exception as exc:
            messagebox.showerror("Totals Error", str(exc), parent=self)

    def _render_cart(self, refresh_totals: bool = True) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        for index, item in enumerate(self.cart):
            tag = "even" if index % 2 == 0 else "odd"
            self.cart_tree.insert(
                "",
                "end",
                text=str(index),
                values=(
                    item["name"],
                    self.settings_service.format_money(item["unit_price"], currency_settings),
                    item["quantity"],
                    self.settings_service.format_money(item["quantity"] * item["unit_price"], currency_settings),
                ),
                tags=(tag,),
            )
        if refresh_totals:
            self._update_totals()

    def _checkout(self) -> None:
        try:
            discount = float(self.discount_var.get())
            tax_rate = float(self.tax_var.get())
            receipt = self.sales_service.create_sale(
                cashier_id=int(self.current_user["id"]),
                payment_method=self.payment_var.get(),
                cart_items=self.cart,
                discount=discount,
                tax_rate=tax_rate,
            )
            self.current_receipt = receipt
            self.preview.delete("1.0", tk.END)
            self.preview.insert("1.0", self.sales_service.receipt_preview(receipt))
            messagebox.showinfo("Sale Complete", f"Sale saved with receipt {receipt['receipt_no']}.", parent=self)
            self.cart = []
            self.current_totals = {"subtotal": 0.0, "discount_amount": 0.0, "tax_amount": 0.0, "total": 0.0}
            self._render_cart(refresh_totals=False)
            self._update_total_labels(self.current_totals)
            self.refresh_products()
            for callback in self.refresh_callbacks:
                callback()
        except Exception as exc:
            messagebox.showerror("Checkout Error", str(exc), parent=self)

    def _save_receipt(self) -> None:
        if self.current_receipt is None:
            messagebox.showwarning("No Receipt", "Complete a sale before exporting a receipt.", parent=self)
            return
        default_name = f"{self.current_receipt['receipt_no']}.pdf"
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Receipt",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF File", "*.pdf")],
        )
        if not file_path:
            return
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            self.sales_service.save_receipt(self.current_receipt, file_path)
            messagebox.showinfo("Receipt Saved", f"Receipt saved to:\n{file_path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Receipt Error", str(exc), parent=self)

    def refresh_products(self) -> None:
        products = self.inventory_service.list_products()
        self.product_lookup = {
            f"{product['name']} | {product['sku']} | stock {product['stock_qty']}": product
            for product in products
            if int(product["stock_qty"]) > 0
        }
        self.product_box["values"] = list(self.product_lookup.keys())
        if self.product_lookup and self.product_var.get() not in self.product_lookup:
            self.product_var.set(next(iter(self.product_lookup.keys())))
        elif not self.product_lookup:
            self.product_var.set("")
