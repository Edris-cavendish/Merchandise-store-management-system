from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.config import APP_NAME, COPYRIGHT_TEXT, WINDOW_SIZE
from app.db.database import DatabaseManager
from app.services.access_control import has_permission
from app.services.analytics_service import AnalyticsService
from app.services.attendance_service import AttendanceService
from app.services.dashboard_service import DashboardService
from app.services.employee_service import EmployeeService
from app.services.expenses_service import ExpensesService
from app.services.inventory_service import InventoryService
from app.services.payroll_service import PayrollService
from app.services.sales_service import SalesService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.ui.tabs.analytics_tab import AnalyticsTab
from app.ui.tabs.dashboard_tab import DashboardTab
from app.ui.tabs.expenses_tab import ExpensesTab
from app.ui.tabs.inventory_tab import InventoryTab
from app.ui.tabs.payroll_tab import PayrollTab
from app.ui.tabs.receipts_tab import ReceiptsTab
from app.ui.tabs.sales_tab import SalesTab
from app.ui.tabs.settings_tab import SettingsTab
from app.ui.tabs.staff_tab import StaffTab
from app.ui.theme import apply_theme


def _initials(full_name: str) -> str:
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return full_name[:2].upper() if full_name else "??"


class SupermarketApp(ttk.Frame):
    def __init__(
        self,
        parent: tk.Tk,
        database: DatabaseManager,
        current_user: dict,
        on_logout=None,
    ) -> None:
        self.parent = parent
        self.database = database
        self.current_user = current_user
        self.on_logout = on_logout

        self.style = ttk.Style(parent)
        self.palette = apply_theme(self.style, self.current_user.get("theme_name"))

        super().__init__(parent, style="App.TFrame", padding=16)

        self.dashboard_service = DashboardService(database)
        self.inventory_service = InventoryService(database)
        self.employee_service = EmployeeService(database)
        self.attendance_service = AttendanceService(database)
        self.sales_service = SalesService(database)
        self.user_service = UserService(database)
        self.settings_service = SettingsService(database)
        self.payroll_service = PayrollService(database)
        self.expenses_service = ExpensesService(database)
        self.analytics_service = AnalyticsService(database)
        self.app_settings = self.settings_service.get_app_settings()
        self.store_name = self.app_settings["store_name"]

        self._configure_window(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.store_name_var = tk.StringVar(value=self.store_name)
        self.user_header_var = tk.StringVar()
        self.role_badge_var = tk.StringVar()
        self.avatar_var = tk.StringVar()

        self.dashboard_tab = None
        self.inventory_tab = None
        self.staff_tab = None
        self.sales_tab = None
        self.receipts_tab = None
        self.my_receipts_tab = None
        self.analytics_tab = None
        self.expenses_tab = None
        self.payroll_tab = None
        self.settings_tab = None
        self.notebook = None

        self._build_header()
        self._build_notebook()
        self._build_footer()
        self._refresh_header_text()
        self._apply_palette_to_tabs()

    # ── Window setup ─────────────────────────────────────────────────────────

    def _configure_window(self, parent: tk.Tk) -> None:
        requested_width, requested_height = map(int, WINDOW_SIZE.split("x"))
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        width = min(requested_width, max(screen_width - 80, 980))
        height = min(requested_height, max(screen_height - 80, 680))
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        parent.geometry(f"{width}x{height}+{x}+{y}")
        parent.minsize(980, 680)
        parent.title(self._window_title())
        parent.configure(bg=self.palette["bg"])

    def _window_title(self) -> str:
        return f"{self.store_name} | {APP_NAME}"

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        p = self.palette
        header = ttk.Frame(self, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=3)
        header.columnconfigure(1, weight=2)

        # ─ Hero card (left) ───────────────────────────────────────────────────
        hero = tk.Frame(header, background=p["accent"])
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        hero.columnconfigure(0, weight=1)

        # Pill badge
        pill = tk.Label(
            hero,
            text="  ● RETAIL CONTROL HUB  ",
            bg=p["accent_dark"],
            fg=p["hero_text"],
            font=("Segoe UI Semibold", 8),
            padx=8,
            pady=3,
        )
        pill.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 0))

        # Store name
        tk.Label(
            hero,
            textvariable=self.store_name_var,
            bg=p["accent"],
            fg=p["hero_text"],
            font=("Bahnschrift SemiBold", 26),
            justify="left",
            wraplength=640,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(10, 4))

        # App sub-title
        tk.Label(
            hero,
            text=APP_NAME,
            bg=p["accent"],
            fg=p["hero_text"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=640,
        ).grid(row=2, column=0, sticky="w", padx=20)

        # Description
        tk.Label(
            hero,
            text="Retail operations · inventory · billing · supplier payables · payroll · analytics · reporting",
            bg=p["accent"],
            fg=p["hero_text"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=640,
        ).grid(row=3, column=0, sticky="w", padx=20, pady=(6, 18))

        # ─ Meta card (right) ─────────────────────────────────────────────────
        meta = ttk.Frame(header, style="Surface.TFrame", padding=20)
        meta.grid(row=0, column=1, sticky="nsew")
        meta.columnconfigure(0, weight=1)
        meta.columnconfigure(1, weight=0)

        # Avatar initials circle
        self._avatar_label = tk.Label(
            meta,
            textvariable=self.avatar_var,
            bg=p["accent"],
            fg=p["hero_text"],
            font=("Bahnschrift SemiBold", 16),
            width=3,
            anchor="center",
            relief="flat",
        )
        self._avatar_label.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(10, 0))

        ttk.Label(meta, text="Signed In User", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(meta, textvariable=self.role_badge_var, style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="e", padx=(0, 40)
        )
        ttk.Label(
            meta,
            textvariable=self.user_header_var,
            style="HeaderMetaTitle.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 16))

        ttk.Separator(meta, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14)
        )

        button_row = ttk.Frame(meta, style="Surface.TFrame")
        button_row.grid(row=3, column=0, columnspan=2, sticky="ew")
        button_row.columnconfigure((0, 1), weight=1)
        ttk.Button(
            button_row, text="↻  Refresh", style="Secondary.TButton",
            command=self.refresh_all,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            button_row, text="Sign Out", style="Danger.TButton",
            command=self._logout,
        ).grid(row=0, column=1, sticky="ew")

    # ── Notebook ──────────────────────────────────────────────────────────────

    def _build_notebook(self) -> None:
        if self.notebook is not None:
            self.notebook.destroy()

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        self.dashboard_tab = None
        if has_permission(self.current_user, "view_dashboard"):
            self.dashboard_tab = DashboardTab(
                self.notebook,
                self.dashboard_service,
                self.inventory_service,
                self.attendance_service,
                self.payroll_service,
                self.settings_service,
                self.current_user,
            )
            self.notebook.add(self.dashboard_tab, text="  Dashboard  ")

        self.inventory_tab = None
        if has_permission(self.current_user, "manage_inventory"):
            self.inventory_tab = InventoryTab(self.notebook, self.inventory_service, self.settings_service)
            self.notebook.add(self.inventory_tab, text="  Inventory  ")

        self.staff_tab = None
        if has_permission(self.current_user, "manage_staff"):
            self.staff_tab = StaffTab(self.notebook, self.employee_service, self.attendance_service, self.settings_service)
            self.notebook.add(self.staff_tab, text="  Staff & Attendance  ")

        self.sales_tab = None
        if has_permission(self.current_user, "process_sales"):
            self.sales_tab = SalesTab(
                self.notebook,
                self.inventory_service,
                self.sales_service,
                self.settings_service,
                self.current_user,
                store_name=self.store_name,
                refresh_callbacks=[self.refresh_all],
            )
            self.notebook.add(self.sales_tab, text="  Sales & Billing  ")

        self.receipts_tab = None
        self.my_receipts_tab = None
        self.analytics_tab = None
        self.expenses_tab = None
        if self.current_user.get("role") == "Administrator":
            self.receipts_tab = ReceiptsTab(
                self.notebook,
                self.sales_service,
                self.settings_service,
                self.current_user,
                scope="all",
                allow_export=True,
                title="Receipt Archive",
            )
            self.notebook.add(self.receipts_tab, text="  Receipt Archive  ")

            self.analytics_tab = AnalyticsTab(self.notebook, self.analytics_service, self.settings_service)
            self.notebook.add(self.analytics_tab, text="  Analytics & Reports  ")

            self.expenses_tab = ExpensesTab(
                self.notebook,
                self.current_user,
                self.expenses_service,
                self.inventory_service,
                self.settings_service,
            )
            self.notebook.add(self.expenses_tab, text="  Expenses & Suppliers  ")
        else:
            self.my_receipts_tab = ReceiptsTab(
                self.notebook,
                self.sales_service,
                self.settings_service,
                self.current_user,
                scope="mine",
                allow_export=False,
                title="My Receipts",
            )
            self.notebook.add(self.my_receipts_tab, text="  My Receipts  ")

        self.payroll_tab = None
        if has_permission(self.current_user, "view_payroll"):
            self.payroll_tab = PayrollTab(self.notebook, self.current_user, self.payroll_service, self.settings_service)
            self.notebook.add(self.payroll_tab, text="  My Pay  ")

        self.settings_tab = SettingsTab(
            self.notebook,
            self.current_user,
            self.user_service,
            self.employee_service,
            self.settings_service,
            on_profile_updated=self.handle_profile_update,
            on_branding_updated=self.handle_branding_updated,
        )
        self.notebook.add(self.settings_tab, text="  Settings & Security  ")

        self.notebook.bind("<<NotebookTabChanged>>", self._handle_tab_change)
        self.refresh_all()
        self._apply_palette_to_tabs()
        self._select_default_tab()

    def _select_default_tab(self) -> None:
        if self.payroll_tab is not None and self.current_user.get("role") == "Employee":
            self.notebook.select(self.payroll_tab)
        elif self.dashboard_tab is not None:
            self.notebook.select(self.dashboard_tab)
        elif self.receipts_tab is not None:
            self.notebook.select(self.receipts_tab)
        elif self.my_receipts_tab is not None:
            self.notebook.select(self.my_receipts_tab)
        else:
            self.notebook.select(self.settings_tab)

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, style="App.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Separator(footer, orient="horizontal").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Label(footer, text=COPYRIGHT_TEXT, style="Footer.TLabel").grid(row=1, column=0, sticky="e")

    # ── Header text refresh ───────────────────────────────────────────────────

    def _refresh_header_text(self) -> None:
        full_name = self.current_user.get("full_name", "")
        self.user_header_var.set(f"{full_name}  ·  @{self.current_user['username']}")
        self.role_badge_var.set(f"Role: {self.current_user['role']}")
        self.avatar_var.set(_initials(full_name))

    # ── Tab change ────────────────────────────────────────────────────────────

    def _handle_tab_change(self, _event=None) -> None:
        if self.settings_tab is not None and self.notebook.select() == str(self.settings_tab):
            self.settings_tab.refresh()
        self.refresh_all()

    # ── Palette propagation ───────────────────────────────────────────────────

    def _apply_palette_to_tabs(self) -> None:
        for tab in (
            self.dashboard_tab,
            self.inventory_tab,
            self.staff_tab,
            self.sales_tab,
            self.receipts_tab,
            self.my_receipts_tab,
            self.analytics_tab,
            self.expenses_tab,
            self.payroll_tab,
            self.settings_tab,
        ):
            if tab is not None and hasattr(tab, "apply_palette"):
                tab.apply_palette(self.palette)

    def _repaint_header(self) -> None:
        """Repaint all plain tk widgets in the header with the new palette colours."""
        p = self.palette
        # Find the header frame (it's a ttk.Frame, so we need to check by style or traverse all)
        for widget in self.winfo_children():
            # The header is the first child, a ttk.Frame with Header.TFrame style
            if isinstance(widget, ttk.Frame):
                # This is the header - now find and repaint its tk children
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):
                        # This is the hero card - repaint it
                        child.configure(bg=p["accent"])
                        _repaint_tk_frame(child, p)
                    elif isinstance(child, ttk.Frame):
                        # This is the meta card - check for avatar label inside
                        for meta_child in child.winfo_children():
                            if isinstance(meta_child, tk.Label) and meta_child.cget("textvariable") == self.avatar_var:
                                # This is the avatar label
                                meta_child.configure(bg=p["accent"], fg=p["hero_text"])

    # ── Actions ───────────────────────────────────────────────────────────────

    def _logout(self) -> None:
        if not messagebox.askyesno(
            "Sign Out",
            "Sign out of this session and return to the secure login screen?",
            parent=self.parent,
        ):
            return
        if callable(self.on_logout):
            self.on_logout()
        else:
            self.parent.destroy()

    def handle_profile_update(self, updated_user: dict) -> None:
        previous_role = self.current_user.get("role")
        previous_permissions = set(self.current_user.get("permissions", []))

        self.current_user.update(updated_user)
        self.palette = apply_theme(self.style, self.current_user.get("theme_name"))
        self.parent.configure(bg=self.palette["bg"])
        self.configure(style="App.TFrame")
        self._refresh_header_text()
        self._repaint_header()

        permissions_changed = previous_role != self.current_user.get("role") or previous_permissions != set(
            self.current_user.get("permissions", [])
        )
        if permissions_changed:
            self._build_notebook()
        else:
            self._apply_palette_to_tabs()
            if self.settings_tab is not None:
                self.settings_tab.update_current_user(self.current_user)
            self.refresh_all()

    def handle_branding_updated(self, updated_settings: dict) -> None:
        self.app_settings.update(updated_settings)
        self.store_name = updated_settings["store_name"]
        self.store_name_var.set(self.store_name)
        self.parent.title(self._window_title())
        if self.sales_tab is not None:
            self.sales_tab.update_store_name(self.store_name)
        self.refresh_all()

    def refresh_all(self) -> None:
        if self.dashboard_tab is not None:
            self.dashboard_tab.refresh()
        if self.inventory_tab is not None:
            self.inventory_tab.refresh()
        if self.staff_tab is not None:
            self.staff_tab.refresh()
        if self.sales_tab is not None:
            self.sales_tab.refresh_products()
            self.sales_tab.refresh_currency_view()
        if self.receipts_tab is not None:
            self.receipts_tab.refresh()
        if self.my_receipts_tab is not None:
            self.my_receipts_tab.refresh()
        if self.analytics_tab is not None:
            self.analytics_tab.refresh()
        if self.expenses_tab is not None:
            self.expenses_tab.refresh()
        if self.payroll_tab is not None:
            self.payroll_tab.refresh()


def _repaint_tk_frame(widget: tk.Widget, p: dict) -> None:
    """Recursively update bg colour on plain tk.Frame / tk.Label widgets in the header."""
    for child in widget.winfo_children():
        try:
            if isinstance(child, (tk.Frame,)):
                bg = child.cget("bg")
                # Only repaint accent-coloured frames (hero + avatar)
                if bg not in ("#FFFFFF", "white", p["bg"], p["surface"]):
                    child.configure(bg=p["accent"])
            elif isinstance(child, tk.Label):
                bg = child.cget("bg")
                if bg not in ("#FFFFFF", "white", p["bg"], p["surface"]):
                    child.configure(bg=p["accent"])
        except tk.TclError:
            pass
        _repaint_tk_frame(child, p)
