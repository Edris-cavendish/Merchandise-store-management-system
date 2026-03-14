from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.ui.widgets import ScrollablePage, StatCard, make_labeled_entry


class SimpleBarChart(ttk.Frame):
    def __init__(self, parent, title: str) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=14)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.canvas = tk.Canvas(self, height=260, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.palette = None

    def apply_palette(self, palette: dict[str, str]) -> None:
        self.palette = palette
        self.canvas.configure(bg=palette["entry"])

    def set_data(self, items: list[dict], value_key: str) -> None:
        self.canvas.delete("all")
        palette = self.palette or {"entry": "#FFFFFF", "accent": "#2F7D4A", "muted": "#666", "text": "#111"}
        width = max(self.canvas.winfo_width(), 460)
        height = max(self.canvas.winfo_height(), 260)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        self.canvas.create_rectangle(0, 0, width, height, fill=palette["entry"], outline=palette["entry"])

        if not items:
            self.canvas.create_text(width / 2, height / 2, text="No data yet.", fill=palette["muted"], font=("Segoe UI", 11))
            return

        values = [max(float(item.get(value_key, 0) or 0), 0) for item in items]
        max_value = max(values) or 1
        chart_height = height - 70
        chart_width = width - 40
        bar_width = max(chart_width // max(len(items) * 2, 2), 36)
        spacing = bar_width
        start_x = 24
        baseline = height - 30

        for index, item in enumerate(items):
            value = values[index]
            bar_height = (value / max_value) * chart_height
            x1 = start_x + index * (bar_width + spacing)
            y1 = baseline - bar_height
            x2 = x1 + bar_width
            self.canvas.create_rectangle(x1, y1, x2, baseline, fill=palette["accent"], outline="")
            self.canvas.create_text((x1 + x2) / 2, y1 - 12, text=f"{value:,.0f}", fill=palette["text"], font=("Segoe UI", 9))
            label = str(item.get("label", "Item"))[:14]
            self.canvas.create_text((x1 + x2) / 2, baseline + 14, text=label, fill=palette["muted"], font=("Segoe UI", 9))


class AnalyticsTab(ScrollablePage):
    def __init__(self, parent, analytics_service, settings_service) -> None:
        super().__init__(parent, padding=6)
        self.analytics_service = analytics_service
        self.settings_service = settings_service
        self.start_date_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.end_date_var = tk.StringVar(value=date.today().isoformat())

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Analytics & Reports", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(4, 16)
        )
        ttk.Label(
            self.body,
            text="Track employee performance, product performance, daily profit movement, and export a simple profit report for the selected period.",
            style="Muted.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.cards_frame = ttk.Frame(self.body, style="App.TFrame")
        self.cards_frame.grid(row=2, column=0, sticky="ew")
        self.cards = [
            StatCard(self.cards_frame, "Revenue Today", "0", "All sales recorded today"),
            StatCard(self.cards_frame, "Expenses Today", "0", "All operating expenses recorded today"),
            StatCard(self.cards_frame, "Net Profit Today", "0", "Revenue minus stock cost and expenses"),
            StatCard(self.cards_frame, "Supplier Balance", "0", "Outstanding supplier credit still unpaid"),
        ]

        self.filters = ttk.LabelFrame(self.body, text="Report Period", padding=16)
        self.filters.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        self.filters.columnconfigure((0, 1, 2), weight=1)
        make_labeled_entry(self.filters, "Start Date", self.start_date_var, 0, 0)
        make_labeled_entry(self.filters, "End Date", self.end_date_var, 0, 1)
        ttk.Button(self.filters, text="Refresh Analytics", style="Primary.TButton", command=self.refresh).grid(
            row=1, column=2, sticky="ew", padx=(0, 10), pady=(24, 10)
        )

        self.charts_panel = ttk.Frame(self.body, style="App.TFrame")
        self.charts_panel.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        self.charts_panel.columnconfigure(0, weight=1)
        self.charts_panel.columnconfigure(1, weight=1)

        self.employee_chart = SimpleBarChart(self.charts_panel, "Employee Performance (Sales Value)")
        self.product_chart = SimpleBarChart(self.charts_panel, "Product Performance (Revenue)")
        self.profit_chart = SimpleBarChart(self.charts_panel, "Daily Net Profit (Last 7 Days)")

        self.report_panel = ttk.LabelFrame(self.body, text="Profit Report Preview", padding=16)
        self.report_panel.grid(row=5, column=0, sticky="nsew", pady=(16, 0))
        self.report_panel.columnconfigure(0, weight=1)
        self.report_panel.rowconfigure(1, weight=1)
        actions = ttk.Frame(self.report_panel, style="Surface.TFrame")
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(actions, text="Refresh Report", style="Secondary.TButton", command=self.refresh).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(actions, text="Export Report", style="Primary.TButton", command=self._export_report).grid(
            row=0, column=1, sticky="ew"
        )
        self.report_text = tk.Text(self.report_panel, height=18, relief="flat", font=("Consolas", 10), wrap="none")
        self.report_text.grid(row=1, column=0, sticky="nsew")
        report_y = ttk.Scrollbar(self.report_panel, orient="vertical", command=self.report_text.yview)
        report_y.grid(row=1, column=1, sticky="ns")
        report_x = ttk.Scrollbar(self.report_panel, orient="horizontal", command=self.report_text.xview)
        report_x.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.report_text.configure(yscrollcommand=report_y.set, xscrollcommand=report_x.set)

        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh()

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)
        for child in self.cards_frame.winfo_children():
            child.grid_forget()
        columns = 4 if width >= 1480 else 2 if width >= 860 else 1
        for column in range(4):
            self.cards_frame.columnconfigure(column, weight=0)
        for column in range(columns):
            self.cards_frame.columnconfigure(column, weight=1)
        for index, card in enumerate(self.cards):
            row = index // columns
            column = index % columns
            padx = (0, 8) if column < columns - 1 else (0, 0)
            pady = (0, 8) if index < len(self.cards) - columns else (0, 0)
            card.grid(row=row, column=column, sticky="nsew", padx=padx, pady=pady)

        for child in self.charts_panel.winfo_children():
            child.grid_forget()
        if width >= 1280:
            self.employee_chart.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
            self.product_chart.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
            self.profit_chart.grid(row=1, column=0, columnspan=2, sticky="nsew")
        else:
            self.employee_chart.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
            self.product_chart.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
            self.profit_chart.grid(row=2, column=0, sticky="nsew")

        self._sync_scrollregion()

    def apply_palette(self, palette: dict[str, str]) -> None:
        super().apply_palette(palette)
        self.report_text.configure(
            bg=palette["entry"],
            fg=palette["text"],
            insertbackground=palette["text"],
            selectbackground=palette["accent"],
            selectforeground="#FFFFFF",
            highlightthickness=0,
            borderwidth=0,
        )
        for chart in (self.employee_chart, self.product_chart, self.profit_chart):
            chart.apply_palette(palette)
            chart.set_data([], "value")

    def _export_report(self) -> None:
        report = self.analytics_service.report_text(self.start_date_var.get().strip(), self.end_date_var.get().strip())
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Admin Report",
            defaultextension=".txt",
            initialfile=f"profit-report-{self.end_date_var.get().strip() or date.today().isoformat()}.txt",
            filetypes=[("Text File", "*.txt")],
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(report, encoding="utf-8")
            messagebox.showinfo("Report Saved", f"Report saved to:\n{file_path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc), parent=self)

    def refresh(self) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        summary = self.analytics_service.summary_cards()
        values = [
            self.settings_service.format_money(summary["revenue_today"], currency_settings),
            self.settings_service.format_money(summary["expenses_today"], currency_settings),
            self.settings_service.format_money(summary["net_profit_today"], currency_settings),
            self.settings_service.format_money(summary["outstanding_supplier"], currency_settings),
        ]
        details = [
            "All recorded sales value for today",
            "Utilities, rent, and other expenses for today",
            "Revenue minus stock cost and expenses",
            "Unpaid supplier balances still pending",
        ]
        for card, value, detail in zip(self.cards, values, details):
            card.update_content(value, detail)

        self.employee_chart.set_data(self.analytics_service.employee_performance(), "total_amount")
        self.product_chart.set_data(self.analytics_service.product_performance(), "revenue")
        self.profit_chart.set_data(self.analytics_service.daily_financials(), "net_profit")

        report = self.analytics_service.report_text(self.start_date_var.get().strip(), self.end_date_var.get().strip())
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", report)
