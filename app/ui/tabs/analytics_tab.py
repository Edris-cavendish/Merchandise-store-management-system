from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.ui.widgets import ScrollablePage, StatCard, make_labeled_entry, apply_treeview_stripes
from app.utils.pdf_export import export_text_as_pdf


class AnimatedBarChart(ttk.Frame):
    """A modern bar chart with gridlines, value labels, and animated bars."""

    def __init__(self, parent, title: str) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=14)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.canvas = tk.Canvas(self, height=240, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.palette = None
        self._items: list[dict] = []
        self._value_key = "value"
        self._anim_step = 0

    def apply_palette(self, palette: dict[str, str]) -> None:
        self.palette = palette
        self.canvas.configure(bg=palette["surface"])

    def set_data(self, items: list[dict], value_key: str) -> None:
        self._items = items
        self._value_key = value_key
        self._anim_step = 0
        self._draw_frame()

    def _draw_frame(self, progress: float = 1.0) -> None:
        self.canvas.delete("all")
        p = self.palette or {
            "surface": "#FFFFFF", "surface_alt": "#F0F4F8",
            "accent": "#1D4ED8", "muted": "#666", "text": "#111",
            "outline": "#E0E6EE",
        }
        items = self._items
        value_key = self._value_key

        w = max(self.canvas.winfo_width(), 460)
        h = max(self.canvas.winfo_height(), 240)
        self.canvas.create_rectangle(0, 0, w, h, fill=p["surface"], outline="")

        if not items:
            self.canvas.create_text(w / 2, h / 2, text="No data yet.", fill=p["muted"], font=("Segoe UI", 11))
            return

        values = [max(float(item.get(value_key, 0) or 0), 0) for item in items]
        max_value = max(values) or 1

        pad_l, pad_r, pad_top, pad_bot = 44, 16, 24, 36
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_top - pad_bot
        baseline_y = h - pad_bot

        # Gridlines at 0%, 25%, 50%, 75%, 100%
        for frac in (0.25, 0.5, 0.75, 1.0):
            gy = baseline_y - frac * chart_h
            self.canvas.create_line(pad_l, gy, w - pad_r, gy, fill=p["outline"], dash=(4, 4))
            label_val = max_value * frac
            self.canvas.create_text(
                pad_l - 4, gy,
                text=f"{label_val:,.0f}",
                anchor="e",
                fill=p["muted"],
                font=("Segoe UI", 8),
            )

        # Baseline
        self.canvas.create_line(pad_l, baseline_y, w - pad_r, baseline_y, fill=p["outline"])

        n = len(items)
        max_bar_w = min(chart_w // max(n, 1) - 8, 60)
        bar_w = max(max_bar_w, 18)
        total_bars_w = n * bar_w + (n - 1) * max(4, (chart_w - n * bar_w) // max(n - 1, 1))
        start_x = pad_l + (chart_w - total_bars_w) // 2
        gap = (chart_w - n * bar_w) // max(n, 1)

        # Accent colour shades
        accent = p["accent"]

        for i, item in enumerate(items):
            v = values[i]
            full_h = (v / max_value) * chart_h
            bar_h = full_h * progress
            x1 = start_x + i * (bar_w + gap)
            x2 = x1 + bar_w
            y1 = baseline_y - bar_h
            y2 = baseline_y

            # Gradient simulation: draw several rectangles getting lighter
            steps = max(int(bar_h / 4), 1)
            for s in range(steps):
                alpha = 0.55 + 0.45 * (s / max(steps - 1, 1))
                shade = _blend_hex(accent, p["surface"], 1 - alpha)
                seg_y1 = y1 + s * (bar_h / steps)
                seg_y2 = y1 + (s + 1) * (bar_h / steps)
                self.canvas.create_rectangle(x1, seg_y1, x2, seg_y2, fill=shade, outline="")

            # Value label at top
            if progress >= 0.95:
                self.canvas.create_text(
                    (x1 + x2) / 2, y1 - 10,
                    text=f"{v:,.0f}",
                    fill=p["text"],
                    font=("Segoe UI Semibold", 9),
                )

            # X-axis label
            label = str(item.get("label", f"#{i+1}"))[:12]
            self.canvas.create_text(
                (x1 + x2) / 2, baseline_y + 14,
                text=label,
                fill=p["muted"],
                font=("Segoe UI", 8),
            )

    def animate(self) -> None:
        """Animate bars growing from 0 to full height over ~400ms."""
        steps = 20
        delay = 20  # ms per step

        def _step(i: int) -> None:
            progress = i / steps
            self._draw_frame(progress=progress)
            if i < steps:
                self.after(delay, lambda: _step(i + 1))

        _step(1)


def _blend_hex(hex1: str, hex2: str, t: float) -> str:
    """Blend two hex colours. t=0 → hex1, t=1 → hex2."""
    try:
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return hex1


class AnalyticsTab(ScrollablePage):
    def __init__(self, parent, analytics_service, settings_service) -> None:
        super().__init__(parent, padding=14)
        self.analytics_service = analytics_service
        self.settings_service = settings_service
        self.start_date_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.end_date_var = tk.StringVar(value=date.today().isoformat())

        self.body.columnconfigure(0, weight=1)

        ttk.Label(self.body, text="Analytics & Reports", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            self.body,
            text="Track employee performance, product revenue, daily profit movement, and export a profit report for any period.",
            style="MutedBg.TLabel",
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 14))

        # ── Stat cards ────────────────────────────────────────────────────────
        self.cards_frame = ttk.Frame(self.body, style="App.TFrame")
        self.cards_frame.grid(row=2, column=0, sticky="ew")
        self.cards = [
            StatCard(self.cards_frame, "Gross Receipts Today", "0", "All receipts collected today (incl tax)"),
            StatCard(self.cards_frame, "Net Sales Today", "0", "Subtotal minus discounts (ex tax)"),
            StatCard(self.cards_frame, "Tax Collected Today", "0", "Tax portion collected from customers"),
            StatCard(self.cards_frame, "Operating Profit Today", "0", "Net sales minus COGS and operating expenses"),
        ]

        # ── Report period filter ──────────────────────────────────────────────
        self.filters = ttk.LabelFrame(self.body, text="📅  Report Period", padding=14)
        self.filters.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        self.filters.columnconfigure((0, 1, 2), weight=1)
        make_labeled_entry(self.filters, "Start Date", self.start_date_var, 0, 0)
        make_labeled_entry(self.filters, "End Date", self.end_date_var, 0, 1)
        ttk.Button(self.filters, text="Refresh Analytics", style="Primary.TButton", command=self.refresh).grid(
            row=1, column=2, sticky="ew", padx=(0, 10), pady=(18, 10)
        )

        # ── Charts ────────────────────────────────────────────────────────────
        self.charts_panel = ttk.Frame(self.body, style="App.TFrame")
        self.charts_panel.grid(row=4, column=0, sticky="nsew", pady=(14, 0))
        self.charts_panel.columnconfigure(0, weight=1)
        self.charts_panel.columnconfigure(1, weight=1)

        self.employee_chart = AnimatedBarChart(self.charts_panel, "Employee Performance (Sales Value)")
        self.product_chart = AnimatedBarChart(self.charts_panel, "Product Performance (Revenue)")
        self.profit_chart = AnimatedBarChart(self.charts_panel, "Daily Operating Profit (Last 7 Days)")

        # ── Report preview ────────────────────────────────────────────────────
        self.report_panel = ttk.LabelFrame(self.body, text="Profit Report Preview", padding=16)
        self.report_panel.grid(row=5, column=0, sticky="nsew", pady=(14, 0))
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
            selectforeground=palette["hero_text"],
            highlightthickness=0,
            borderwidth=0,
        )
        for card in self.cards:
            card.apply_palette(palette)
        for chart in (self.employee_chart, self.product_chart, self.profit_chart):
            chart.apply_palette(palette)
            chart.set_data([], "value")

    def _export_report(self) -> None:
        report = self.analytics_service.report_text(self.start_date_var.get().strip(), self.end_date_var.get().strip())
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Admin Report",
            defaultextension=".pdf",
            initialfile=f"profit-report-{self.end_date_var.get().strip() or date.today().isoformat()}.pdf",
            filetypes=[("PDF File", "*.pdf")],
        )
        if not file_path:
            return
        try:
            export_text_as_pdf(report, file_path)
            messagebox.showinfo("Report Saved", f"Report saved to:\n{file_path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc), parent=self)

    def refresh(self) -> None:
        currency_settings = self.settings_service.get_currency_settings()
        summary = self.analytics_service.summary_cards()
        values = [
            self.settings_service.format_money(summary["gross_receipts_today"], currency_settings),
            self.settings_service.format_money(summary["net_sales_today"], currency_settings),
            self.settings_service.format_money(summary["tax_collected_today"], currency_settings),
            self.settings_service.format_money(summary["operating_profit_today"], currency_settings),
        ]
        details = [
            "Sum of total_amount for today",
            "Sum of subtotal minus discount_amount",
            "Sum of tax_amount collected today",
            (
                f"Gross margin {summary['gross_margin_percent_today']:.2f}% | "
                f"Operating margin {summary['operating_margin_percent_today']:.2f}%"
            ),
        ]
        for card, value, detail in zip(self.cards, values, details):
            card.update_content(value, detail)

        emp_data = self.analytics_service.employee_performance()
        prod_data = self.analytics_service.product_performance()
        profit_data = self.analytics_service.daily_financials()

        self.employee_chart.set_data(emp_data, "total_amount")
        self.product_chart.set_data(prod_data, "revenue")
        self.profit_chart.set_data(profit_data, "operating_profit")

        self.after(100, self.employee_chart.animate)
        self.after(150, self.product_chart.animate)
        self.after(200, self.profit_chart.animate)

        report = self.analytics_service.report_text(self.start_date_var.get().strip(), self.end_date_var.get().strip())
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", report)
