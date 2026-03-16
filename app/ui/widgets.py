from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.theme import get_palette


# ---------------------------------------------------------------------------
# ScrollablePage  — base class for every tab
# ---------------------------------------------------------------------------

class ScrollablePage(ttk.Frame):
    def __init__(self, parent: tk.Misc, padding: int = 6) -> None:
        super().__init__(parent, style="App.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            background=get_palette()["bg"],
            borderwidth=0,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.body = ttk.Frame(self.canvas, style="App.TFrame", padding=padding)
        self.body.columnconfigure(0, weight=1)
        self.window_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", self._sync_scrollregion)
        self.canvas.bind("<Configure>", self._resize_body)
        self.bind("<Enter>", self._bind_mousewheel)
        self.bind("<Leave>", self._unbind_mousewheel)
        self.body.bind("<Enter>", self._bind_mousewheel)
        self.body.bind("<Leave>", self._unbind_mousewheel)

    def _sync_scrollregion(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_body(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)) * 3, "units")

    def _bind_mousewheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def apply_palette(self, palette: dict[str, str]) -> None:
        self.canvas.configure(background=palette["bg"])


# ---------------------------------------------------------------------------
# StatCard  — the beautiful KPI card used on dashboard and analytics tabs
# ---------------------------------------------------------------------------

class StatCard(ttk.Frame):
    """A metric card with a coloured left accent bar, large value, and detail subtitle."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        value: str,
        detail: str,
    ) -> None:
        super().__init__(parent, style="Card.TFrame")
        self.columnconfigure(1, weight=1)

        palette = get_palette()

        # Left accent bar
        self._bar = tk.Frame(self, width=4, background=palette["accent"])
        self._bar.grid(row=0, column=0, sticky="ns", padx=(0, 0))

        # Content area
        inner = ttk.Frame(self, style="Card.TFrame", padding=(14, 16))
        inner.grid(row=0, column=1, sticky="nsew")
        inner.columnconfigure(0, weight=1)

        ttk.Label(inner, text=title.upper(), style="Kicker.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.value_var = tk.StringVar(value=value)
        ttk.Label(inner, textvariable=self.value_var, style="CardValue.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 4)
        )
        self.detail_var = tk.StringVar(value=detail)
        ttk.Label(
            inner,
            textvariable=self.detail_var,
            style="CardTitle.TLabel",
            wraplength=260,
            justify="left",
        ).grid(row=2, column=0, sticky="w")

    def update_content(self, value: str, detail: str) -> None:
        self.value_var.set(value)
        self.detail_var.set(detail)

    def apply_palette(self, palette: dict[str, str]) -> None:
        self._bar.configure(background=palette["accent"])


# ---------------------------------------------------------------------------
# SectionHeader  — reusable page headline + subtitle block
# ---------------------------------------------------------------------------

class SectionHeader(ttk.Frame):
    """Headline + optional subtitle used at the top of every tab body."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        subtitle: str = "",
        wrap: int = 980,
    ) -> None:
        super().__init__(parent, style="App.TFrame")
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=title, style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(4, 6)
        )
        if subtitle:
            ttk.Label(
                self,
                text=subtitle,
                style="MutedBg.TLabel",
                wraplength=wrap,
                justify="left",
            ).grid(row=1, column=0, sticky="w", pady=(0, 14))


# ---------------------------------------------------------------------------
# ToolbarRow  — a horizontal button bar used in many tabs
# ---------------------------------------------------------------------------

class ToolbarRow(ttk.Frame):
    """Horizontal row of evenly-spaced buttons."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, style="Surface.TFrame")
        self._col = 0

    def add_button(
        self,
        text: str,
        command,
        style: str = "Secondary.TButton",
        side: str = "left",
        padx=(0, 8),
    ) -> ttk.Button:
        btn = ttk.Button(self, text=text, style=style, command=command)
        btn.pack(side=side, fill="x", expand=True, padx=padx)
        return btn


# ---------------------------------------------------------------------------
# make_labeled_entry  — field-label + entry helper
# ---------------------------------------------------------------------------

def make_labeled_entry(
    parent: tk.Misc,
    label: str,
    variable: tk.Variable,
    row: int,
    column: int,
    width: int = 18,
    help_text: str = "",
    **entry_kwargs,
) -> ttk.Entry:
    ttk.Label(parent, text=label, style="FormLabel.TLabel").grid(
        row=row,
        column=column,
        sticky="w",
        pady=(0, 3),
        padx=(0, 10),
    )
    entry = ttk.Entry(parent, textvariable=variable, width=width, **entry_kwargs)
    entry.grid(row=row + 1, column=column, sticky="ew", padx=(0, 10), pady=(0, 10))
    if help_text:
        ttk.Label(parent, text=help_text, style="FormLabel.TLabel").grid(
            row=row + 2, column=column, sticky="w", padx=(0, 10), pady=(0, 6)
        )
    return entry


# ---------------------------------------------------------------------------
# apply_treeview_stripes  — zebra-stripe helper for any Treeview
# ---------------------------------------------------------------------------

def apply_treeview_stripes(tree: ttk.Treeview, palette: dict[str, str]) -> None:
    """Reapply alternating row colours to a Treeview after a palette change."""
    tree.tag_configure("odd",  background=palette["entry"])
    tree.tag_configure("even", background=palette["surface_alt"])


def repopulate_with_stripes(tree: ttk.Treeview) -> None:
    """Re-tag all existing rows in a Treeview with alternating stripe tags."""
    for index, item in enumerate(tree.get_children()):
        tag = "even" if index % 2 == 0 else "odd"
        tree.item(item, tags=(tag,))
