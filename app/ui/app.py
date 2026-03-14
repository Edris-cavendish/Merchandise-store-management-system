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

        super().__init__(parent, style="App.TFrame", padding=18)

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

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=3)
        header.columnconfigure(1, weight=2)

        hero = ttk.Frame(header, style="HeroCard.TFrame", padding=22)
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        hero.columnconfigure(0, weight=1)

        ttk.Label(hero, text="Retail Control Hub", style="HeroPill.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(hero, textvariable=self.store_name_var, style="HeroAccent.TLabel", wraplength=620, justify="left").grid(
            row=1, column=0, sticky="w", pady=(16, 8)
        )
        ttk.Label(hero, text=APP_NAME, style="HeroSub.TLabel", wraplength=620, justify="left").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Label(
            hero,
            text="Professional attendance, payroll, inventory, billing, reporting, supplier credit, and receipt control in one secure desktop workspace.",
            style="HeroSub.TLabel",
            wraplength=620,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))

        meta = ttk.Frame(header, style="Surface.TFrame", padding=18)
        meta.grid(row=0, column=1, sticky="nsew")
        meta.columnconfigure(0, weight=1)
        meta.columnconfigure(1, weight=1)

        ttk.Label(meta, text="Signed In User", style="HeaderMetaTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(meta, textvariable=self.role_badge_var, style="HeaderMetaTitle.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(meta, textvariable=self.user_header_var, style="HeaderMetaText.TLabel", wraplength=360, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 18)
        )

        button_row = ttk.Frame(meta, style="Surface.TFrame")
        button_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        button_row.columnconfigure((0, 1), weight=1)
        ttk.Button(button_row, text="Refresh View", style="Secondary.TButton", command=self.refresh_all).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(button_row, text="Log Out", style="Primary.TButton", command=self._logout).grid(
            row=0, column=1, sticky="ew"
        )

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
            self.notebook.add(self.dashboard_tab, text="Dashboard")

        self.inventory_tab = None
        if has_permission(self.current_user, "manage_inventory"):
            self.inventory_tab = InventoryTab(self.notebook, self.inventory_service, self.settings_service)
            self.notebook.add(self.inventory_tab, text="Inventory")

        self.staff_tab = None
        if has_permission(self.current_user, "manage_staff"):
            self.staff_tab = StaffTab(self.notebook, self.employee_service, self.attendance_service, self.settings_service)
            self.notebook.add(self.staff_tab, text="Staff & Attendance")

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
            self.notebook.add(self.sales_tab, text="Sales & Billing")

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
            self.notebook.add(self.receipts_tab, text="Receipt Archive")

            self.analytics_tab = AnalyticsTab(self.notebook, self.analytics_service, self.settings_service)
            self.notebook.add(self.analytics_tab, text="Analytics & Reports")

            self.expenses_tab = ExpensesTab(
                self.notebook,
                self.current_user,
                self.expenses_service,
                self.inventory_service,
                self.settings_service,
            )
            self.notebook.add(self.expenses_tab, text="Expenses & Suppliers")
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
            self.notebook.add(self.my_receipts_tab, text="My Receipts")

        self.payroll_tab = None
        if has_permission(self.current_user, "view_payroll"):
            self.payroll_tab = PayrollTab(self.notebook, self.current_user, self.payroll_service, self.settings_service)
            self.notebook.add(self.payroll_tab, text="My Pay")

        self.settings_tab = SettingsTab(
            self.notebook,
            self.current_user,
            self.user_service,
            self.employee_service,
            self.settings_service,
            on_profile_updated=self.handle_profile_update,
            on_branding_updated=self.handle_branding_updated,
        )
        self.notebook.add(self.settings_tab, text="Settings & Security")

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

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, style="App.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(footer, text=COPYRIGHT_TEXT, style="Footer.TLabel").pack(side="right")

    def _refresh_header_text(self) -> None:
        self.user_header_var.set(f"{self.current_user['full_name']} | Username: {self.current_user['username']}")
        self.role_badge_var.set(f"Role: {self.current_user['role']}")

    def _handle_tab_change(self, _event=None) -> None:
        if self.settings_tab is not None and self.notebook.select() == str(self.settings_tab):
            self.settings_tab.refresh()
        self.refresh_all()

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

    def _logout(self) -> None:
        if not messagebox.askyesno(
            "Log Out",
            "Log out of this account and return to the secure login screen?",
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
