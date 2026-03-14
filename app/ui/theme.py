from __future__ import annotations

from tkinter import ttk


THEMES = {
    "Green & White": {
        "bg": "#F3FAF5",
        "surface": "#FFFFFF",
        "surface_alt": "#E6F3EA",
        "card": "#D8ECDC",
        "accent": "#2F7D4A",
        "accent_dark": "#225C36",
        "success": "#2F7D4A",
        "danger": "#C25A49",
        "text": "#14261A",
        "muted": "#587160",
        "entry": "#FFFFFF",
        "outline": "#C7DECE",
    },
    "Dark Blue & White": {
        "bg": "#F3F7FB",
        "surface": "#FFFFFF",
        "surface_alt": "#E4EDF8",
        "card": "#D8E4F2",
        "accent": "#1F4E8C",
        "accent_dark": "#173963",
        "success": "#2D845C",
        "danger": "#C95E4C",
        "text": "#132233",
        "muted": "#5B7187",
        "entry": "#FFFFFF",
        "outline": "#C8D8EA",
    },
    "Yellow & White": {
        "bg": "#FFF9EE",
        "surface": "#FFFFFF",
        "surface_alt": "#FFF1CD",
        "card": "#F7E5A9",
        "accent": "#C69214",
        "accent_dark": "#916C0F",
        "success": "#4F8A48",
        "danger": "#C8694D",
        "text": "#33220A",
        "muted": "#7C673F",
        "entry": "#FFFFFF",
        "outline": "#E8D6A0",
    },
    "Brown & White": {
        "bg": "#FBF6F2",
        "surface": "#FFFFFF",
        "surface_alt": "#F2E6DC",
        "card": "#E7D6C5",
        "accent": "#7A4E2B",
        "accent_dark": "#58381E",
        "success": "#4D8150",
        "danger": "#C66A55",
        "text": "#2B1D14",
        "muted": "#6F5A49",
        "entry": "#FFFFFF",
        "outline": "#DCC5B1",
    },
}

DEFAULT_THEME_NAME = "Yellow & White"
THEME_OPTIONS = tuple(THEMES.keys())
PALETTE = THEMES[DEFAULT_THEME_NAME]


def normalize_theme_name(theme_name: str | None) -> str:
    return theme_name if theme_name in THEMES else DEFAULT_THEME_NAME


def get_palette(theme_name: str | None = None) -> dict[str, str]:
    return THEMES[normalize_theme_name(theme_name)]


def apply_theme(style: ttk.Style, theme_name: str | None = None) -> dict[str, str]:
    palette = get_palette(theme_name)
    style.theme_use("clam")
    style.configure(".", background=palette["bg"], foreground=palette["text"], font=("Segoe UI", 10))
    style.configure(
        "TEntry",
        fieldbackground=palette["entry"],
        foreground=palette["text"],
        insertcolor=palette["text"],
        borderwidth=1,
        relief="solid",
        padding=9,
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", "#E2E5E9"), ("readonly", palette["entry"])],
        foreground=[("disabled", "#74818D"), ("readonly", palette["text"])],
    )
    style.configure(
        "TCombobox",
        fieldbackground=palette["entry"],
        background=palette["entry"],
        foreground=palette["text"],
        arrowcolor=palette["text"],
        insertcolor=palette["text"],
        borderwidth=1,
        relief="solid",
        padding=7,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", palette["entry"])],
        background=[("readonly", palette["entry"])],
        foreground=[("readonly", palette["text"])],
        arrowcolor=[("readonly", palette["text"])],
    )
    style.configure("TCheckbutton", background=palette["surface"], foreground=palette["text"], font=("Segoe UI", 10))
    style.map(
        "TCheckbutton",
        background=[("active", palette["surface"])],
        foreground=[("disabled", palette["muted"])],
    )
    style.configure("TScrollbar", background=palette["surface_alt"], troughcolor=palette["bg"], arrowcolor=palette["accent"])
    style.configure("App.TFrame", background=palette["bg"])
    style.configure("Header.TFrame", background=palette["bg"])
    style.configure("Surface.TFrame", background=palette["surface"])
    style.configure("SurfaceAlt.TFrame", background=palette["surface_alt"])
    style.configure("Card.TFrame", background=palette["card"], relief="flat")
    style.configure("HeroCard.TFrame", background=palette["accent"], relief="flat")
    style.configure(
        "Hero.TLabel",
        background=palette["surface"],
        foreground=palette["text"],
        font=("Bahnschrift SemiBold", 19),
    )
    style.configure(
        "Headline.TLabel",
        background=palette["bg"],
        foreground=palette["text"],
        font=("Bahnschrift SemiBold", 21),
    )
    style.configure(
        "Section.TLabel",
        background=palette["surface"],
        foreground=palette["text"],
        font=("Bahnschrift SemiBold", 12),
    )
    style.configure(
        "Kicker.TLabel",
        background=palette["card"],
        foreground=palette["accent_dark"],
        font=("Segoe UI Semibold", 9),
    )
    style.configure(
        "CardTitle.TLabel",
        background=palette["card"],
        foreground=palette["text"],
        font=("Segoe UI Semibold", 11),
    )
    style.configure(
        "CardValue.TLabel",
        background=palette["card"],
        foreground=palette["text"],
        font=("Bahnschrift SemiBold", 22),
    )
    style.configure(
        "Muted.TLabel",
        background=palette["surface"],
        foreground=palette["muted"],
        font=("Segoe UI", 10),
    )
    style.configure(
        "Footer.TLabel",
        background=palette["bg"],
        foreground=palette["muted"],
        font=("Segoe UI", 9),
    )
    style.configure(
        "FormLabel.TLabel",
        background=palette["surface"],
        foreground=palette["muted"],
        font=("Segoe UI Semibold", 10),
    )
    style.configure(
        "Primary.TButton",
        background=palette["accent"],
        foreground="#FFFFFF",
        borderwidth=0,
        focusthickness=0,
        font=("Segoe UI Semibold", 10),
        padding=(16, 11),
    )
    style.map(
        "Primary.TButton",
        background=[("active", palette["accent_dark"])],
        foreground=[("disabled", "#8A949C")],
    )
    style.configure(
        "Secondary.TButton",
        background=palette["surface_alt"],
        foreground=palette["text"],
        borderwidth=0,
        focusthickness=0,
        font=("Segoe UI Semibold", 10),
        padding=(16, 11),
    )
    style.map("Secondary.TButton", background=[("active", palette["card"])])
    style.configure(
        "Treeview",
        background=palette["entry"],
        foreground=palette["text"],
        fieldbackground=palette["entry"],
        rowheight=30,
        borderwidth=0,
        font=("Segoe UI", 10),
    )
    style.map("Treeview", background=[("selected", palette["surface_alt"])], foreground=[("selected", palette["text"])])
    style.configure(
        "Treeview.Heading",
        background=palette["surface_alt"],
        foreground=palette["text"],
        font=("Segoe UI Semibold", 10),
        relief="flat",
        padding=(8, 9),
    )
    style.map("Treeview.Heading", background=[("active", palette["card"])])
    style.configure("TNotebook", background=palette["bg"], borderwidth=0, tabmargins=(0, 10, 0, 0))
    style.configure(
        "TNotebook.Tab",
        background=palette["surface"],
        foreground=palette["muted"],
        padding=(18, 11),
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", palette["accent"]), ("active", palette["surface_alt"])],
        foreground=[("selected", "#FFFFFF"), ("active", palette["text"])],
    )
    style.configure("TLabelframe", background=palette["surface"], foreground=palette["text"], borderwidth=0)
    style.configure(
        "TLabelframe.Label",
        background=palette["surface"],
        foreground=palette["accent"],
        font=("Segoe UI Semibold", 10),
    )

    style.configure(
        "HeroAccent.TLabel",
        background=palette["accent"],
        foreground="#FFFFFF",
        font=("Bahnschrift SemiBold", 22),
    )
    style.configure(
        "HeroSub.TLabel",
        background=palette["accent"],
        foreground="#F7FBFF",
        font=("Segoe UI", 10),
    )
    style.configure(
        "HeroPill.TLabel",
        background=palette["accent_dark"],
        foreground="#FFFFFF",
        font=("Segoe UI Semibold", 9),
    )
    style.configure(
        "HeaderMetaTitle.TLabel",
        background=palette["surface"],
        foreground=palette["text"],
        font=("Segoe UI Semibold", 10),
    )
    style.configure(
        "HeaderMetaText.TLabel",
        background=palette["surface"],
        foreground=palette["muted"],
        font=("Segoe UI", 10),
    )
    style.configure(
        "LoginTitle.TLabel",
        background=palette["surface"],
        foreground=palette["text"],
        font=("Bahnschrift SemiBold", 18),
    )
    style.configure(
        "LoginBody.TLabel",
        background=palette["surface"],
        foreground=palette["muted"],
        font=("Segoe UI", 10),
    )
    return palette
