from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.theme import get_palette


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
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def apply_palette(self, palette: dict[str, str]) -> None:
        self.canvas.configure(background=palette["bg"])


class StatCard(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, value: str, detail: str) -> None:
        super().__init__(parent, style="Card.TFrame", padding=18)
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=title.upper(), style="Kicker.TLabel").grid(row=0, column=0, sticky="w")
        self.value_var = tk.StringVar(value=value)
        ttk.Label(self, textvariable=self.value_var, style="CardValue.TLabel").grid(
            row=1, column=0, sticky="w", pady=(10, 6)
        )
        self.detail_var = tk.StringVar(value=detail)
        ttk.Label(
            self,
            textvariable=self.detail_var,
            style="CardTitle.TLabel",
            wraplength=220,
            justify="left",
        ).grid(row=2, column=0, sticky="w")

    def update_content(self, value: str, detail: str) -> None:
        self.value_var.set(value)
        self.detail_var.set(detail)


def make_labeled_entry(
    parent: tk.Misc,
    label: str,
    variable: tk.Variable,
    row: int,
    column: int,
    width: int = 18,
    **entry_kwargs,
) -> ttk.Entry:
    ttk.Label(parent, text=label, style="FormLabel.TLabel").grid(
        row=row,
        column=column,
        sticky="w",
        pady=(0, 4),
        padx=(0, 10),
    )
    entry = ttk.Entry(parent, textvariable=variable, width=width, **entry_kwargs)
    entry.grid(row=row + 1, column=column, sticky="ew", padx=(0, 10), pady=(0, 10))
    return entry
