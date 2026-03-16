from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.config import APP_NAME, COPYRIGHT_TEXT, STORE_NAME
from app.db.database import DatabaseManager
from app.services.access_control import default_permissions_for_role, sanitize_permissions_for_role, sort_permissions
from app.ui.theme import DEFAULT_THEME_NAME, apply_theme
from app.utils.security import verify_password


class AuthService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def authenticate(self, username: str, password: str) -> dict | None:
        row = self.database.fetch_one(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username.strip(),),
        )
        if row and verify_password(password, row["password_hash"]):
            user = dict(row)
            user["permissions"] = self._permissions_for_user(int(user["id"]), user.get("role", "Employee"))
            # Ensure theme_name is present
            if not user.get("theme_name"):
                user["theme_name"] = DEFAULT_THEME_NAME
            return user
        return None

    def prompt_login(self) -> dict | None:
        store_name = self._store_name()
        last_theme = self._last_theme()

        root = tk.Tk()
        root.title(f"{store_name} | Secure Login")
        width, height = 980, 620
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.resizable(False, False)

        style = ttk.Style(root)
        palette = apply_theme(style, last_theme)
        root.configure(bg=palette["bg"])
        try:
            root.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        result: dict | None = None
        status_var = tk.StringVar(value="Use your assigned credentials to continue.")

        shell = tk.Frame(root, bg=palette["bg"])
        shell.pack(fill="both", expand=True)
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=11, minsize=410)
        shell.columnconfigure(1, weight=13, minsize=470)

        frame_bg = palette["bg"]
        left_panel = tk.Frame(
            shell,
            bg=palette["surface"],
            highlightbackground=palette["card_border"],
            highlightthickness=1,
            bd=0,
            padx=0,
            pady=0,
        )
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(18, 8), pady=18)
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(4, weight=1)

        right_panel = tk.Frame(shell, bg=frame_bg)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 18), pady=18)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)

        left_header = tk.Frame(left_panel, bg=palette["surface_alt"], height=220)
        left_header.grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 8))
        left_header.grid_propagate(False)
        left_header.columnconfigure(0, weight=1)

        hero_canvas = tk.Canvas(
            left_header,
            bg=palette["surface_alt"],
            highlightthickness=0,
            borderwidth=0,
            height=160,
        )
        hero_canvas.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))

        left_pill = tk.Label(
            left_panel,
            text="MODERN RETAIL WORKSPACE",
            bg=palette["surface_alt"],
            fg=palette["accent"],
            font=("Segoe UI Semibold", 8),
            padx=12,
            pady=5,
        )
        left_pill.grid(row=1, column=0, sticky="w", padx=24, pady=(2, 10))

        hero_title = tk.Label(
            left_panel,
            text=store_name,
            bg=palette["surface"],
            fg=palette["text"],
            font=("Bahnschrift SemiBold", 24),
            justify="left",
            wraplength=320,
        )
        hero_title.grid(row=2, column=0, sticky="w", padx=24)

        hero_subtitle = tk.Label(
            left_panel,
            text=APP_NAME,
            bg=palette["surface"],
            fg=palette["accent"],
            font=("Segoe UI", 12),
            justify="left",
        )
        hero_subtitle.grid(row=3, column=0, sticky="w", padx=24, pady=(8, 0))

        hero_body = tk.Label(
            left_panel,
            text=(
                "A flexible desktop POS workspace for merchandise shops, retail counters, stock rooms, and payment tracking."
            ),
            bg=palette["surface"],
            fg=palette["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=320,
        )
        hero_body.grid(row=4, column=0, sticky="nw", padx=24, pady=(14, 0))

        feature_stack = tk.Frame(left_panel, bg=palette["surface"])
        feature_stack.grid(row=5, column=0, sticky="ew", padx=24, pady=(14, 14))
        feature_stack.columnconfigure(0, weight=1)
        features = (
            ("Fast Checkout", "Accurate billing, receipts, and totals."),
            ("Inventory Control", "Track stock and supplier balances."),
            ("Secure Access", "Role-based logins and themed views."),
        )
        for index, (title, body) in enumerate(features):
            card = tk.Frame(
                feature_stack,
                bg=palette["surface_alt"],
                highlightbackground=palette["card_border"],
                highlightthickness=1,
                padx=12,
                pady=10,
            )
            card.grid(row=index, column=0, sticky="ew", pady=(0, 8 if index < len(features) - 1 else 0))
            card.columnconfigure(0, weight=1)
            tk.Label(
                card,
                text=title,
                bg=palette["surface_alt"],
                fg=palette["text"],
                font=("Segoe UI Semibold", 10),
                anchor="w",
                justify="left",
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                card,
                text=body,
                bg=palette["surface_alt"],
                fg=palette["muted"],
                font=("Segoe UI", 9),
                anchor="w",
                justify="left",
                wraplength=290,
            ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        footer_note = tk.Label(
            left_panel,
            text=COPYRIGHT_TEXT,
            bg=palette["surface"],
            fg=palette["muted"],
            font=("Segoe UI", 8),
            justify="left",
            wraplength=310,
        )
        footer_note.grid(row=6, column=0, sticky="sw", padx=24, pady=(0, 18))

        form_shell = tk.Frame(
            right_panel,
            bg=palette["surface"],
            highlightbackground=palette["card_border"],
            highlightthickness=1,
            bd=0,
            padx=28,
            pady=26,
        )
        form_shell.grid(row=0, column=0, sticky="nsew")
        form_shell.columnconfigure(0, weight=1)

        top_band = tk.Frame(form_shell, bg=palette["surface"])
        top_band.grid(row=0, column=0, sticky="ew")
        top_band.columnconfigure(0, weight=1)

        tk.Label(
            top_band,
            text="SECURE ACCESS",
            bg=palette["surface"],
            fg=palette["accent"],
            font=("Segoe UI Semibold", 9),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            top_band,
            text="Welcome back",
            bg=palette["surface"],
            fg=palette["text"],
            font=("Bahnschrift SemiBold", 24),
        ).grid(row=1, column=0, sticky="w", pady=(10, 6))
        tk.Label(
            top_band,
            text="Sign in to continue into your themed POS workspace.",
            bg=palette["surface"],
            fg=palette["muted"],
            font=("Segoe UI", 11),
            justify="left",
            wraplength=400,
        ).grid(row=2, column=0, sticky="w", pady=(0, 16))

        account_chip = tk.Frame(
            form_shell,
            bg=palette["surface_alt"],
            highlightbackground=palette["card_border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        account_chip.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        account_chip.columnconfigure(1, weight=1)
        tk.Label(
            account_chip,
            text="A",
            bg=palette["accent"],
            fg=palette["hero_text"],
            font=("Bahnschrift SemiBold", 16),
            width=2,
        ).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))
        tk.Label(
            account_chip,
            text="Quick access",
            bg=palette["surface_alt"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=0, column=1, sticky="w")
        tk.Label(
            account_chip,
            text="Default administrator login: admin / admin123",
            bg=palette["surface_alt"],
            fg=palette["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))

        ttk.Label(form_shell, text="Username", style="FormLabel.TLabel").grid(row=2, column=0, sticky="w")
        username_var = tk.StringVar(value="admin")
        username_entry = ttk.Entry(form_shell, textvariable=username_var, font=("Segoe UI", 11))
        username_entry.grid(row=3, column=0, sticky="ew", pady=(5, 16))

        ttk.Label(form_shell, text="Password", style="FormLabel.TLabel").grid(row=4, column=0, sticky="w")
        password_var = tk.StringVar(value="admin123")
        password_entry = ttk.Entry(form_shell, textvariable=password_var, show="*", font=("Segoe UI", 11))
        password_entry.grid(row=5, column=0, sticky="ew", pady=(5, 10))

        show_password_var = tk.BooleanVar(value=False)

        def toggle_password() -> None:
            password_entry.configure(show="" if show_password_var.get() else "*")

        ttk.Checkbutton(
            form_shell,
            text="Show password",
            variable=show_password_var,
            command=toggle_password,
        ).grid(row=6, column=0, sticky="w", pady=(0, 18))

        status_label = tk.Label(
            form_shell,
            textvariable=status_var,
            bg=palette["surface_alt"],
            fg=palette["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=400,
            padx=14,
            pady=12,
            highlightbackground=palette["card_border"],
            highlightthickness=1,
        )
        status_label.grid(row=7, column=0, sticky="ew", pady=(0, 18))

        def close_dialog() -> None:
            root.quit()
            root.destroy()

        def attempt_login(*_args) -> None:
            nonlocal result
            if not username_var.get().strip() or not password_var.get():
                status_var.set("Enter both username and password to continue.")
                messagebox.showwarning("Missing Details", "Enter both username and password.", parent=root)
                return

            user = self.authenticate(username_var.get(), password_var.get())
            if user is None:
                status_var.set("Authentication failed. Check your details or ask an administrator to verify your account.")
                messagebox.showerror("Authentication Failed", "Invalid credentials or inactive account.", parent=root)
                return

            status_var.set("Authentication successful. Opening workspace...")
            result = user
            root.after(180, close_dialog)

        actions = ttk.Frame(form_shell, style="Surface.TFrame")
        actions.grid(row=8, column=0, sticky="ew")
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(actions, text="Cancel", style="Secondary.TButton", command=close_dialog).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(actions, text="Sign In", style="Primary.TButton", command=attempt_login).grid(
            row=0, column=1, sticky="ew"
        )

        bottom_note = tk.Label(
            form_shell,
            text="Your selected theme is respected on this screen and across the full workspace after sign-in.",
            bg=palette["surface"],
            fg=palette["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=400,
        )
        bottom_note.grid(row=9, column=0, sticky="w", pady=(18, 0))

        pulse_state = {"step": 0}

        def draw_brand_graphic() -> None:
            hero_canvas.delete("all")
            width = max(hero_canvas.winfo_width(), 320)
            height = max(hero_canvas.winfo_height(), 160)
            hero_canvas.create_rectangle(0, 0, width, height, fill=palette["surface_alt"], outline="")
            hero_canvas.create_oval(-40, -30, 120, 130, fill=palette["card"], outline="")
            hero_canvas.create_oval(width - 130, 18, width - 18, 130, fill=palette["card"], outline="")

            offset = (pulse_state["step"] % 10) * 1.5
            hero_canvas.create_oval(28, 32, 102, 106, fill=palette["accent"], outline="")
            hero_canvas.create_rectangle(66, 62, 172, 78, fill=palette["accent"], outline="")
            hero_canvas.create_rectangle(144, 56, 160, 84, fill=palette["accent"], outline="")
            hero_canvas.create_oval(width - 92 - offset, 42, width - 54 - offset, 80, outline="", fill=palette["accent"])
            hero_canvas.create_oval(width - 64 + offset, 82, width - 28 + offset, 118, outline="", fill=palette["accent_dark"])
            hero_canvas.create_text(
                226,
                62,
                text="POS",
                fill=palette["text"],
                font=("Bahnschrift SemiBold", 28),
            )
            hero_canvas.create_text(
                228,
                92,
                text="Retail Workspace",
                fill=palette["muted"],
                font=("Segoe UI", 11),
            )

        def animate_brand_graphic() -> None:
            pulse_state["step"] = (pulse_state["step"] + 1) % 24
            draw_brand_graphic()
            if root.winfo_exists():
                root.after(150, animate_brand_graphic)

        def fade_in(alpha: float = 0.0) -> None:
            try:
                root.attributes("-alpha", min(alpha, 1.0))
            except tk.TclError:
                return
            if alpha < 1.0 and root.winfo_exists():
                root.after(18, lambda: fade_in(alpha + 0.08))

        draw_brand_graphic()
        animate_brand_graphic()
        fade_in()

        root.bind("<Return>", attempt_login)
        root.protocol("WM_DELETE_WINDOW", close_dialog)
        root.update_idletasks()
        root.lift()
        root.focus_force()
        username_entry.focus_set()
        root.mainloop()

        return result

    def _store_name(self) -> str:
        row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("store_name",))
        return row["value"] if row else STORE_NAME

    def _last_theme(self) -> str:
        row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("last_theme",))
        return row["value"] if row else DEFAULT_THEME_NAME

    def _permissions_for_user(self, user_id: int, role: str) -> list[str]:
        rows = self.database.fetch_all(
            "SELECT permission_key FROM user_permissions WHERE user_id = ? ORDER BY permission_key",
            (user_id,),
        )
        if not rows:
            return sort_permissions(default_permissions_for_role(role))
        return sort_permissions(sanitize_permissions_for_role({row["permission_key"] for row in rows}, role))
