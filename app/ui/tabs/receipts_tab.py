from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.ui.widgets import ScrollablePage
from app.utils.currency import format_money


class ReceiptsTab(ScrollablePage):
    def __init__(
        self,
        parent,
        sales_service,
        settings_service,
        current_user: dict,
        scope: str = "all",
        allow_export: bool = True,
        title: str = "Receipt Archive",
        description: str | None = None,
    ) -> None:
        super().__init__(parent, padding=6)
        self.sales_service = sales_service
        self.settings_service = settings_service
        self.current_user = current_user
        self.scope = scope
        self.allow_export = allow_export
        self.selected_sale_id: int | None = None
        self.current_receipt: dict | None = None

        if description is None:
            if scope == "mine":
                description = "View only your own past receipts. Editing and deleting are disabled to preserve integrity."
            else:
                description = "Review every saved receipt in the database, preview the original sale details, and export a copy whenever needed."

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text=title, style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(4, 16)
        )
        ttk.Label(
            self.body,
            text=description,
            style="Muted.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.main_panel = ttk.Frame(self.body, style="App.TFrame")
        self.main_panel.grid(row=2, column=0, sticky="nsew")
        self.main_panel.columnconfigure(0, weight=3)
        self.main_panel.columnconfigure(1, weight=2)
        self.main_panel.rowconfigure(0, weight=1)

        self._build_grid()
        self._build_preview()
        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh()

    def _build_grid(self) -> None:
        label = "My Receipts" if self.scope == "mine" else "Stored Receipts"
        self.grid_panel = ttk.LabelFrame(self.main_panel, text=label, padding=14)
        self.grid_panel.columnconfigure(0, weight=1)
        self.grid_panel.rowconfigure(0, weight=1)

        columns = ("receipt", "date", "cashier", "payment", "total", "store")
        self.tree = ttk.Treeview(self.grid_panel, columns=columns, show="headings", height=16)
        for key, title, width in (
            ("receipt", "Receipt No", 170),
            ("date", "Date/Time", 170),
            ("cashier", "Cashier", 170),
            ("payment", "Payment", 120),
            ("total", "Total", 130),
            ("store", "Store", 190),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._load_selected_receipt)

        tree_y = ttk.Scrollbar(self.grid_panel, orient="vertical", command=self.tree.yview)
        tree_y.grid(row=0, column=1, sticky="ns")
        tree_x = ttk.Scrollbar(self.grid_panel, orient="horizontal", command=self.tree.xview)
        tree_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.tree.configure(yscrollcommand=tree_y.set, xscrollcommand=tree_x.set)

    def _build_preview(self) -> None:
        self.preview_panel = ttk.LabelFrame(self.main_panel, text="Receipt Preview", padding=16)
        self.preview_panel.columnconfigure(0, weight=1)
        self.preview_panel.rowconfigure(2, weight=1)

        ttk.Label(
            self.preview_panel,
            text="Select a receipt to view the exact transaction details stored in the database.",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        action_row = ttk.Frame(self.preview_panel, style="Surface.TFrame")
        action_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        action_row.columnconfigure((0, 1), weight=1)
        ttk.Button(action_row, text="Refresh Receipts", style="Secondary.TButton", command=self.refresh).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        if self.allow_export:
            ttk.Button(action_row, text="Export Selected Receipt", style="Primary.TButton", command=self._export_selected).grid(
                row=0, column=1, sticky="ew"
            )
        else:
            ttk.Label(
                action_row,
                text="View only mode",
                style="HeaderMetaText.TLabel",
            ).grid(row=0, column=1, sticky="e")

        self.preview = tk.Text(
            self.preview_panel,
            height=22,
            relief="flat",
            font=("Consolas", 10),
            wrap="none",
        )
        self.preview.grid(row=2, column=0, sticky="nsew")
        preview_y = ttk.Scrollbar(self.preview_panel, orient="vertical", command=self.preview.yview)
        preview_y.grid(row=2, column=1, sticky="ns")
        preview_x = ttk.Scrollbar(self.preview_panel, orient="horizontal", command=self.preview.xview)
        preview_x.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.preview.configure(yscrollcommand=preview_y.set, xscrollcommand=preview_x.set)

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        self.grid_panel.grid_forget()
        self.preview_panel.grid_forget()

        if width >= 1320:
            self.main_panel.columnconfigure(0, weight=3)
            self.main_panel.columnconfigure(1, weight=2)
            self.grid_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            self.preview_panel.grid(row=0, column=1, sticky="nsew")
        else:
            self.main_panel.columnconfigure(0, weight=1)
            self.main_panel.columnconfigure(1, weight=0)
            self.grid_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
            self.preview_panel.grid(row=1, column=0, sticky="nsew")

        self._sync_scrollregion()

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        self.preview.configure(
            bg=palette["entry"],
            fg=palette["text"],
            insertbackground=palette["text"],
            selectbackground=palette["accent"],
            selectforeground="#FFFFFF",
            highlightthickness=0,
            borderwidth=0,
        )

    def _cashier_scope(self) -> int | None:
        return int(self.current_user["id"]) if self.scope == "mine" else None

    def _load_selected_receipt(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        self.selected_sale_id = int(self.tree.item(item_id, "text"))
        try:
            self.current_receipt = self.sales_service.get_receipt_payload(self.selected_sale_id, cashier_id=self._cashier_scope())
            self.preview.delete("1.0", tk.END)
            self.preview.insert("1.0", self.sales_service.receipt_preview(self.current_receipt))
        except Exception as exc:
            self.preview.delete("1.0", tk.END)
            self.current_receipt = None
            messagebox.showerror("Receipt Error", str(exc), parent=self)

    def _export_selected(self) -> None:
        if self.current_receipt is None:
            messagebox.showwarning("No Receipt", "Select a stored receipt before exporting it.", parent=self)
            return

        default_name = f"{self.current_receipt['receipt_no']}.pdf"
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Stored Receipt",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF File", "*.pdf"), ("Text File", "*.txt")],
        )
        if not file_path:
            return

        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            self.sales_service.save_receipt(self.current_receipt, file_path)
            messagebox.showinfo("Receipt Saved", f"Receipt saved to:\n{file_path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Receipt Error", str(exc), parent=self)

    def refresh(self) -> None:
        receipts = self.sales_service.list_receipts(cashier_id=self._cashier_scope())
        selected_item = None

        for item in self.tree.get_children():
            self.tree.delete(item)

        for receipt in receipts:
            total = format_money(
                receipt["total_amount"],
                receipt.get("currency_symbol"),
                bool(receipt.get("use_decimals", 1)),
            )
            item_id = self.tree.insert(
                "",
                "end",
                text=str(receipt["id"]),
                values=(
                    receipt["receipt_no"],
                    receipt["created_at"],
                    receipt.get("cashier_name") or "System User",
                    receipt["payment_method"],
                    total,
                    receipt.get("store_name") or "Store",
                ),
            )
            if self.selected_sale_id is not None and int(receipt["id"]) == int(self.selected_sale_id):
                selected_item = item_id

        if selected_item is None and receipts:
            selected_item = self.tree.get_children()[0]

        if selected_item is not None:
            self.tree.selection_set(selected_item)
            self.tree.focus(selected_item)
            self._load_selected_receipt()
        else:
            self.selected_sale_id = None
            self.current_receipt = None
            self.preview.delete("1.0", tk.END)
            self.preview.insert("1.0", "No receipts were found for this view yet.")

        self._sync_scrollregion()
