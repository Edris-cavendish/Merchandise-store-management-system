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
            return user
        return None

    def prompt_login(self) -> dict | None:
        store_name = self._store_name()
        root = tk.Tk()
        root.title(f"{store_name} | Secure Login")
        root.geometry("900x520")
        root.resizable(False, False)

        style = ttk.Style(root)
        palette = apply_theme(style, DEFAULT_THEME_NAME)
        root.configure(bg=palette["bg"])

        result: dict | None = None

        shell = ttk.Frame(root, style="App.TFrame", padding=26)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=5)
        shell.columnconfigure(1, weight=4)
        shell.rowconfigure(0, weight=1)

        hero = ttk.Frame(shell, style="HeroCard.TFrame", padding=30)
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        hero.columnconfigure(0, weight=1)

        ttk.Label(hero, text="Secure Retail Workspace", style="HeroPill.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(hero, text=store_name, style="HeroAccent.TLabel", wraplength=420, justify="left").grid(
            row=1, column=0, sticky="w", pady=(18, 8)
        )
        ttk.Label(
            hero,
            text=APP_NAME,
            style="HeroSub.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=2, column=0, sticky="w")
        ttk.Label(
            hero,
            text=(
                "Professional desktop control for attendance, payroll, stock, sales, receipts, and access security. "
                "Only active accounts can enter the system."
            ),
            style="HeroSub.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(18, 18))
        ttk.Label(
            hero,
            text="What this login protects:\n- staff and payroll information\n- inventory and pricing records\n- receipt history and sales controls\n- branding, themes, and user privileges",
            style="HeroSub.TLabel",
            justify="left",
        ).grid(row=4, column=0, sticky="w")
        ttk.Label(hero, text=COPYRIGHT_TEXT, style="HeroSub.TLabel").grid(row=5, column=0, sticky="w", pady=(36, 0))

        form = ttk.Frame(shell, style="Surface.TFrame", padding=30)
        form.grid(row=0, column=1, sticky="nsew")
        form.columnconfigure(0, weight=1)

        ttk.Label(form, text="Sign In", style="LoginTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            form,
            text="Enter your assigned username and password to open your dashboard. Disabled accounts are blocked automatically.",
            style="LoginBody.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 20))

        ttk.Label(form, text="Username", style="FormLabel.TLabel").grid(row=2, column=0, sticky="w")
        username_var = tk.StringVar(value="admin")
        username_entry = ttk.Entry(form, textvariable=username_var, font=("Segoe UI", 11))
        username_entry.grid(row=3, column=0, sticky="ew", pady=(4, 14))

        ttk.Label(form, text="Password", style="FormLabel.TLabel").grid(row=4, column=0, sticky="w")
        password_var = tk.StringVar(value="admin123")
        password_entry = ttk.Entry(
            form,
            textvariable=password_var,
            show="*",
            font=("Segoe UI", 11),
        )
        password_entry.grid(row=5, column=0, sticky="ew", pady=(4, 10))

        ttk.Label(
            form,
            text="Initial administrator login for a new database: admin / admin123",
            style="LoginBody.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=6, column=0, sticky="w", pady=(0, 18))

        def close_dialog() -> None:
            root.quit()
            root.destroy()

        def attempt_login() -> None:
            nonlocal result
            if not username_var.get().strip() or not password_var.get():
                messagebox.showwarning(
                    "Missing Details",
                    "Enter both username and password.",
                    parent=root,
                )
                return

            user = self.authenticate(username_var.get(), password_var.get())
            if user is None:
                messagebox.showerror(
                    "Authentication Failed",
                    "Invalid credentials or inactive account.",
                    parent=root,
                )
                return

            result = user
            close_dialog()

        button_row = ttk.Frame(form, style="Surface.TFrame")
        button_row.grid(row=7, column=0, sticky="ew", pady=(4, 18))
        button_row.columnconfigure((0, 1), weight=1)
        ttk.Button(button_row, text="Exit", style="Secondary.TButton", command=close_dialog).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(button_row, text="Sign In", style="Primary.TButton", command=attempt_login).grid(
            row=0, column=1, sticky="ew"
        )

        ttk.Label(
            form,
            text="Use Settings & Security after login to change usernames, passwords, supermarket name, theme, and currency.",
            style="LoginBody.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=8, column=0, sticky="w")

        root.bind("<Return>", lambda _event: attempt_login())
        root.protocol("WM_DELETE_WINDOW", close_dialog)
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (900 // 2)
        y = (root.winfo_screenheight() // 2) - (520 // 2)
        root.geometry(f"900x520+{x}+{y}")
        root.lift()
        root.focus_force()
        username_entry.focus_set()
        root.mainloop()
        return result

    def _store_name(self) -> str:
        row = self.database.fetch_one("SELECT value FROM app_settings WHERE key = ?", ("store_name",))
        return row["value"] if row else STORE_NAME

    def _permissions_for_user(self, user_id: int, role: str) -> list[str]:
        rows = self.database.fetch_all(
            "SELECT permission_key FROM user_permissions WHERE user_id = ? ORDER BY permission_key",
            (user_id,),
        )
        if not rows:
            return sort_permissions(default_permissions_for_role(role))
        return sort_permissions(sanitize_permissions_for_role({row["permission_key"] for row in rows}, role))
