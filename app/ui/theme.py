from __future__ import annotations

from tkinter import ttk


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------

THEMES: dict[str, dict[str, str]] = {
    # ── Dark Slate & Amber — premium dark-mode default ──────────────────────
    "Dark Slate & Amber": {
        "bg":          "#0F172A",
        "surface":     "#1E293B",
        "surface_alt": "#263348",
        "card":        "#1E293B",
        "accent":      "#F59E0B",
        "accent_dark": "#D97706",
        "success":     "#10B981",
        "danger":      "#EF4444",
        "text":        "#F1F5F9",
        "muted":       "#94A3B8",
        "entry":       "#1E293B",
        "outline":     "#334155",
        "card_border": "#334155",
        "hero_text":   "#FFFFFF",
    },
    # ── Forest & Cream — clean professional light ────────────────────────────
    "Forest & Cream": {
        "bg":          "#F4F9F6",
        "surface":     "#FFFFFF",
        "surface_alt": "#E3F0E9",
        "card":        "#EAF4EE",
        "accent":      "#166534",
        "accent_dark": "#14532D",
        "success":     "#16A34A",
        "danger":      "#DC2626",
        "text":        "#0F2318",
        "muted":       "#4D7A5E",
        "entry":       "#FFFFFF",
        "outline":     "#BBD9C8",
        "card_border": "#C2DCC9",
        "hero_text":   "#FFFFFF",
    },
    # ── Ocean & Cobalt — corporate clarity ──────────────────────────────────
    "Ocean & Cobalt": {
        "bg":          "#F0F6FF",
        "surface":     "#FFFFFF",
        "surface_alt": "#DBEAFE",
        "card":        "#E0ECFF",
        "accent":      "#1D4ED8",
        "accent_dark": "#1E40AF",
        "success":     "#059669",
        "danger":      "#DC2626",
        "text":        "#0F1E3D",
        "muted":       "#4B6890",
        "entry":       "#FFFFFF",
        "outline":     "#BFCFE8",
        "card_border": "#C4D4EC",
        "hero_text":   "#FFFFFF",
    },
    # ── Warm Sand & Terracotta — brand warmth ───────────────────────────────
    "Warm Sand": {
        "bg":          "#FEFBF3",
        "surface":     "#FFFFFF",
        "surface_alt": "#FEF3CD",
        "card":        "#FDE9B1",
        "accent":      "#B45309",
        "accent_dark": "#92400E",
        "success":     "#16A34A",
        "danger":      "#C0392B",
        "text":        "#3B1D07",
        "muted":       "#7A5C3A",
        "entry":       "#FFFFFF",
        "outline":     "#E8D4A0",
        "card_border": "#E1CB90",
        "hero_text":   "#FFFFFF",
    },
}

DEFAULT_THEME_NAME = "Dark Slate & Amber"
THEME_OPTIONS = tuple(THEMES.keys())
PALETTE = THEMES[DEFAULT_THEME_NAME]


def normalize_theme_name(theme_name: str | None) -> str:
    return theme_name if theme_name in THEMES else DEFAULT_THEME_NAME


def get_palette(theme_name: str | None = None) -> dict[str, str]:
    return THEMES[normalize_theme_name(theme_name)]


def apply_theme(style: ttk.Style, theme_name: str | None = None) -> dict[str, str]:  # noqa: C901
    p = get_palette(theme_name)
    style.theme_use("clam")

    # ── Global base ─────────────────────────────────────────────────────────
    style.configure(
        ".",
        background=p["bg"],
        foreground=p["text"],
        font=("Segoe UI", 10),
        borderwidth=0,
        focusthickness=0,
    )

    # ── Entry / Combobox ─────────────────────────────────────────────────────
    style.configure(
        "TEntry",
        fieldbackground=p["entry"],
        foreground=p["text"],
        insertcolor=p["text"],
        borderwidth=1,
        relief="solid",
        padding=(10, 8),
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", p["surface_alt"]), ("readonly", p["entry"])],
        foreground=[("disabled", p["muted"]), ("readonly", p["text"])],
        bordercolor=[("focus", p["accent"]), ("!focus", p["outline"])],
    )
    style.configure(
        "TCombobox",
        fieldbackground=p["entry"],
        background=p["entry"],
        foreground=p["text"],
        arrowcolor=p["accent"],
        insertcolor=p["text"],
        borderwidth=1,
        relief="solid",
        padding=(10, 8),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p["entry"])],
        background=[("readonly", p["entry"])],
        foreground=[("readonly", p["text"])],
        arrowcolor=[("readonly", p["accent"])],
        bordercolor=[("focus", p["accent"]), ("!focus", p["outline"])],
    )

    # ── Checkbutton ──────────────────────────────────────────────────────────
    style.configure(
        "TCheckbutton",
        background=p["surface"],
        foreground=p["text"],
        font=("Segoe UI", 10),
        indicatorcolor=p["entry"],
        indicatorrelief="flat",
    )
    style.map(
        "TCheckbutton",
        background=[("active", p["surface"])],
        foreground=[("disabled", p["muted"])],
        indicatorcolor=[("selected", p["accent"]), ("!selected", p["entry"])],
    )

    # ── Scrollbar ────────────────────────────────────────────────────────────
    style.configure(
        "TScrollbar",
        background=p["surface_alt"],
        troughcolor=p["bg"],
        arrowcolor=p["accent"],
        borderwidth=0,
        relief="flat",
    )

    # ── Frame styles ─────────────────────────────────────────────────────────
    style.configure("App.TFrame",      background=p["bg"])
    style.configure("Header.TFrame",   background=p["bg"])
    style.configure("Surface.TFrame",  background=p["surface"])
    style.configure("SurfaceAlt.TFrame", background=p["surface_alt"])
    style.configure("Card.TFrame",     background=p["card"], relief="flat")
    style.configure("HeroCard.TFrame", background=p["accent"], relief="flat")
    style.configure("Outline.TFrame",  background=p["surface"], relief="flat")

    # ── Label styles ─────────────────────────────────────────────────────────
    style.configure(
        "Hero.TLabel",
        background=p["surface"],
        foreground=p["text"],
        font=("Bahnschrift SemiBold", 20),
    )
    style.configure(
        "Headline.TLabel",
        background=p["bg"],
        foreground=p["text"],
        font=("Bahnschrift SemiBold", 22),
    )
    style.configure(
        "Section.TLabel",
        background=p["surface"],
        foreground=p["text"],
        font=("Bahnschrift SemiBold", 13),
    )
    style.configure(
        "Kicker.TLabel",
        background=p["card"],
        foreground=p["accent"],
        font=("Segoe UI Semibold", 8),
    )
    style.configure(
        "CardTitle.TLabel",
        background=p["card"],
        foreground=p["muted"],
        font=("Segoe UI Semibold", 10),
    )
    style.configure(
        "CardValue.TLabel",
        background=p["card"],
        foreground=p["text"],
        font=("Bahnschrift SemiBold", 26),
    )
    style.configure(
        "Muted.TLabel",
        background=p["surface"],
        foreground=p["muted"],
        font=("Segoe UI", 10),
    )
    style.configure(
        "MutedBg.TLabel",
        background=p["bg"],
        foreground=p["muted"],
        font=("Segoe UI", 10),
    )
    style.configure(
        "Footer.TLabel",
        background=p["bg"],
        foreground=p["muted"],
        font=("Segoe UI", 9),
    )
    style.configure(
        "FormLabel.TLabel",
        background=p["surface"],
        foreground=p["muted"],
        font=("Segoe UI Semibold", 9),
    )
    style.configure(
        "FormLabelBg.TLabel",
        background=p["bg"],
        foreground=p["muted"],
        font=("Segoe UI Semibold", 9),
    )

    # ── Accent-on-dark labels (used in hero card) ────────────────────────────
    style.configure(
        "HeroAccent.TLabel",
        background=p["accent"],
        foreground=p["hero_text"],
        font=("Bahnschrift SemiBold", 24),
    )
    style.configure(
        "HeroSub.TLabel",
        background=p["accent"],
        foreground=p["hero_text"],
        font=("Segoe UI", 10),
    )
    style.configure(
        "HeroPill.TLabel",
        background=p["accent_dark"],
        foreground=p["hero_text"],
        font=("Segoe UI Semibold", 9),
        padding=(8, 3),
    )
    style.configure(
        "HeaderMetaTitle.TLabel",
        background=p["surface"],
        foreground=p["text"],
        font=("Segoe UI Semibold", 11),
    )
    style.configure(
        "HeaderMetaText.TLabel",
        background=p["surface"],
        foreground=p["muted"],
        font=("Segoe UI", 10),
    )
    style.configure(
        "LoginTitle.TLabel",
        background=p["surface"],
        foreground=p["text"],
        font=("Bahnschrift SemiBold", 22),
    )
    style.configure(
        "LoginBody.TLabel",
        background=p["surface"],
        foreground=p["muted"],
        font=("Segoe UI", 10),
    )
    # Accent-coloured value for payroll highlight
    style.configure(
        "AccentValue.TLabel",
        background=p["card"],
        foreground=p["accent"],
        font=("Bahnschrift SemiBold", 15),
    )
    # Badge / pill label for status indicators
    style.configure(
        "BadgeActive.TLabel",
        background=p["success"],
        foreground="#FFFFFF",
        font=("Segoe UI Semibold", 8),
        padding=(6, 2),
    )
    style.configure(
        "BadgeInactive.TLabel",
        background=p["danger"],
        foreground="#FFFFFF",
        font=("Segoe UI Semibold", 8),
        padding=(6, 2),
    )
    # User avatar / initials pill
    style.configure(
        "AvatarPill.TLabel",
        background=p["accent"],
        foreground=p["hero_text"],
        font=("Bahnschrift SemiBold", 14),
        anchor="center",
        padding=(10, 6),
    )

    # ── Buttons ──────────────────────────────────────────────────────────────
    style.configure(
        "Primary.TButton",
        background=p["accent"],
        foreground=p["hero_text"],
        borderwidth=0,
        focusthickness=0,
        font=("Segoe UI Semibold", 10),
        padding=(18, 12),
    )
    style.map(
        "Primary.TButton",
        background=[("active", p["accent_dark"]), ("disabled", p["outline"])],
        foreground=[("disabled", p["muted"])],
    )
    style.configure(
        "Secondary.TButton",
        background=p["surface_alt"],
        foreground=p["text"],
        borderwidth=0,
        focusthickness=0,
        font=("Segoe UI Semibold", 10),
        padding=(18, 12),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", p["card"]), ("disabled", p["surface_alt"])],
        foreground=[("disabled", p["muted"])],
    )
    # Danger button — used for Logout and destructive actions
    style.configure(
        "Danger.TButton",
        background=p["danger"],
        foreground="#FFFFFF",
        borderwidth=0,
        focusthickness=0,
        font=("Segoe UI Semibold", 10),
        padding=(18, 12),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#C0392B"), ("disabled", p["outline"])],
        foreground=[("disabled", p["muted"])],
    )

    # ── Treeview ─────────────────────────────────────────────────────────────
    style.configure(
        "Treeview",
        background=p["entry"],
        foreground=p["text"],
        fieldbackground=p["entry"],
        rowheight=36,
        borderwidth=0,
        font=("Segoe UI", 10),
    )
    style.map(
        "Treeview",
        background=[("selected", p["accent"])],
        foreground=[("selected", p["hero_text"])],
    )
    style.configure(
        "Treeview.Heading",
        background=p["surface_alt"],
        foreground=p["text"],
        font=("Segoe UI Semibold", 10),
        relief="flat",
        padding=(10, 10),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", p["card"])],
    )

    # ── Notebook ─────────────────────────────────────────────────────────────
    style.configure(
        "TNotebook",
        background=p["bg"],
        borderwidth=0,
        tabmargins=(0, 8, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=p["surface"],
        foreground=p["muted"],
        padding=(22, 12),
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", p["accent"]), ("active", p["surface_alt"])],
        foreground=[("selected", p["hero_text"]), ("active", p["text"])],
    )

    # ── LabelFrame ───────────────────────────────────────────────────────────
    style.configure(
        "TLabelframe",
        background=p["surface"],
        foreground=p["text"],
        borderwidth=1,
        relief="solid",
        bordercolor=p["outline"],
        padding=(14, 10),
    )
    style.configure(
        "TLabelframe.Label",
        background=p["surface"],
        foreground=p["accent"],
        font=("Segoe UI Semibold", 10),
        padding=(4, 0),
    )

    # ── Separator ────────────────────────────────────────────────────────────
    style.configure(
        "TSeparator",
        background=p["outline"],
    )

    return p
