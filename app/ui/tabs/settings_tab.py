from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.access_control import (
    PERMISSION_DEFINITIONS,
    ROLE_OPTIONS,
    default_permissions_for_role,
    has_permission,
    permission_labels,
    role_summary,
)
from app.ui.theme import THEME_OPTIONS
from app.ui.widgets import ScrollablePage, make_labeled_entry


class SettingsTab(ScrollablePage):
    def __init__(
        self,
        parent,
        current_user: dict,
        user_service,
        employee_service,
        settings_service,
        on_profile_updated,
        on_branding_updated,
    ) -> None:
        super().__init__(parent, padding=14)
        self.current_user = current_user
        self.user_service = user_service
        self.employee_service = employee_service
        self.settings_service = settings_service
        self.on_profile_updated = on_profile_updated
        self.on_branding_updated = on_branding_updated
        self.selected_user_id: int | None = None
        self.employee_lookup_by_label: dict[str, dict] = {}
        self.employee_label_by_id: dict[int, str] = {}
        self.permission_checks: dict[str, ttk.Checkbutton] = {}

        self.body.columnconfigure(0, weight=1)
        self.body.columnconfigure(1, weight=1)

        ttk.Label(self.body, text="Settings & Security", style="Headline.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            self.body,
            text="Manage your login details, choose your colour theme, configure store branding, and administer employee accounts and permissions.",
            style="MutedBg.TLabel",
            wraplength=1100,
            justify="left",
        ).grid(row=0, column=1, sticky="w", padx=(20, 0), pady=(0, 4))

        self.top_panel = ttk.Frame(self.body, style="App.TFrame")
        self.top_panel.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.top_panel.columnconfigure(0, weight=1)
        self.top_panel.columnconfigure(1, weight=1)

        self._build_profile_section()
        self._build_branding_section()
        if has_permission(self.current_user, "manage_users"):
            self._build_user_admin_section()
            self._build_measurement_units_section()

        self.bind("<Configure>", self._on_resize)
        self.after(50, self._apply_layout)
        self.refresh()

    def _build_profile_section(self) -> None:
        self.profile_frame = ttk.LabelFrame(self.top_panel, text="My Profile", padding=18)
        self.profile_frame.columnconfigure(0, weight=1)

        self.profile_name_var = tk.StringVar()
        self.profile_username_var = tk.StringVar()
        self.current_password_var = tk.StringVar()
        self.new_password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.role_summary_var = tk.StringVar()

        ttk.Label(
            self.profile_frame,
            text="Update your name, username, and password here. For security, your current password is required before changes are saved.",
            style="Muted.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 14))

        make_labeled_entry(self.profile_frame, "Full Name", self.profile_name_var, 1, 0)
        make_labeled_entry(self.profile_frame, "Username", self.profile_username_var, 3, 0)

        ttk.Label(self.profile_frame, text="Access Summary", style="FormLabel.TLabel").grid(
            row=5, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            self.profile_frame,
            textvariable=self.role_summary_var,
            style="Muted.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=6, column=0, sticky="ew", pady=(0, 12))

        ttk.Separator(self.profile_frame, orient="horizontal").grid(row=7, column=0, sticky="ew", pady=(0, 14))

        make_labeled_entry(self.profile_frame, "Current Password", self.current_password_var, 8, 0, show="*")
        make_labeled_entry(self.profile_frame, "New Password", self.new_password_var, 10, 0, show="*")
        make_labeled_entry(self.profile_frame, "Confirm New Password", self.confirm_password_var, 12, 0, show="*")

        ttk.Button(
            self.profile_frame,
            text="Save Profile & Password",
            style="Primary.TButton",
            command=self._save_profile,
        ).grid(row=14, column=0, sticky="ew", pady=(8, 0))

    def _build_branding_section(self) -> None:
        self.branding_frame = ttk.LabelFrame(self.top_panel, text="Theme, Store Name & Currency", padding=18)
        self.branding_frame.columnconfigure(0, weight=1)

        self.live_theme_var = tk.StringVar()
        self.store_name_var = tk.StringVar()
        self.currency_symbol_var = tk.StringVar()
        self.use_decimals_var = tk.BooleanVar(value=True)
        self.theme_status_var = tk.StringVar(value="Theme changes are applied instantly across the app.")
        self.currency_preview_var = tk.StringVar(value="")

        ttk.Label(
            self.branding_frame,
            text="Choose a theme and the whole interface updates immediately. Store branding and currency formatting are saved globally for the whole application.",
            style="Muted.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 14))

        ttk.Label(self.branding_frame, text="Theme Palette", style="FormLabel.TLabel").grid(
            row=1, column=0, sticky="w", pady=(0, 4)
        )
        self.theme_box = ttk.Combobox(
            self.branding_frame,
            textvariable=self.live_theme_var,
            values=THEME_OPTIONS,
            state="readonly",
        )
        self.theme_box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.theme_box.bind("<<ComboboxSelected>>", self._apply_theme_selection)
        if not has_permission(self.current_user, "manage_themes"):
            self.theme_box.configure(state="disabled")

        ttk.Label(
            self.branding_frame,
            textvariable=self.theme_status_var,
            style="Muted.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=3, column=0, sticky="ew", pady=(0, 14))

        ttk.Separator(self.branding_frame, orient="horizontal").grid(row=4, column=0, sticky="ew", pady=(0, 14))

        ttk.Label(self.branding_frame, text="Store Name", style="FormLabel.TLabel").grid(row=5, column=0, sticky="w", pady=(0, 4))
        ttk.Label(self.branding_frame, text="Currency Symbol or Code", style="FormLabel.TLabel").grid(
            row=7, column=0, sticky="w", pady=(0, 4)
        )

        if has_permission(self.current_user, "manage_users"):
            self.store_name_entry = ttk.Entry(self.branding_frame, textvariable=self.store_name_var)
            self.store_name_entry.grid(row=6, column=0, sticky="ew", pady=(0, 10))
            self.currency_entry = ttk.Entry(self.branding_frame, textvariable=self.currency_symbol_var)
            self.currency_entry.grid(row=8, column=0, sticky="ew", pady=(0, 10))
            ttk.Checkbutton(
                self.branding_frame,
                text="Use decimal points in money values",
                variable=self.use_decimals_var,
                command=self._update_currency_preview,
            ).grid(row=9, column=0, sticky="w", pady=(0, 8))
            ttk.Label(
                self.branding_frame,
                text="Examples: $, USD, UGX, KES, EUR. Turn decimals off for currencies that do not normally use them.",
                style="Muted.TLabel",
                wraplength=500,
                justify="left",
            ).grid(row=10, column=0, sticky="ew", pady=(0, 8))
            ttk.Label(
                self.branding_frame,
                textvariable=self.currency_preview_var,
                style="Section.TLabel",
                wraplength=500,
                justify="left",
            ).grid(row=11, column=0, sticky="ew", pady=(0, 10))
            ttk.Button(
                self.branding_frame,
                text="Save Branding & Currency",
                style="Secondary.TButton",
                command=self._save_branding,
            ).grid(row=12, column=0, sticky="ew")
            self.currency_symbol_var.trace_add("write", self._handle_currency_change)
        else:
            ttk.Label(
                self.branding_frame,
                textvariable=self.store_name_var,
                style="Section.TLabel",
                wraplength=500,
                justify="left",
            ).grid(row=6, column=0, sticky="ew", pady=(0, 8))
            ttk.Label(
                self.branding_frame,
                textvariable=self.currency_preview_var,
                style="Muted.TLabel",
                wraplength=500,
                justify="left",
            ).grid(row=8, column=0, sticky="ew", pady=(0, 8))
            ttk.Label(
                self.branding_frame,
                text="Only an administrator can rename the supermarket or change global currency formatting.",
                style="Muted.TLabel",
                wraplength=500,
                justify="left",
            ).grid(row=9, column=0, sticky="ew")

    def _build_measurement_units_section(self) -> None:
        self.units_section = ttk.LabelFrame(self.body, text="Measurement Units", padding=18)
        self.units_section.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
        self.units_section.columnconfigure(0, weight=1)
        self.units_section.columnconfigure(1, weight=1)

        ttk.Label(
            self.units_section,
            text="Control which measurement units appear in the Inventory product form. Add new units or remove ones you don't use — no code changes needed.",
            style="Muted.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        list_frame = ttk.Frame(self.units_section, style="Surface.TFrame")
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        list_frame.columnconfigure(0, weight=1)

        ttk.Label(list_frame, text="Current Units", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.units_listbox = tk.Listbox(list_frame, height=8, selectmode="single", exportselection=False)
        self.units_listbox.grid(row=1, column=0, sticky="nsew")
        units_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.units_listbox.yview)
        units_scroll.grid(row=1, column=1, sticky="ns")
        self.units_listbox.configure(yscrollcommand=units_scroll.set)

        add_frame = ttk.Frame(self.units_section, style="Surface.TFrame")
        add_frame.grid(row=1, column=1, sticky="new")
        add_frame.columnconfigure(0, weight=1)

        self.new_unit_var = tk.StringVar()
        ttk.Label(add_frame, text="New Unit Name", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Entry(add_frame, textvariable=self.new_unit_var).grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(
            add_frame,
            text="Examples: pcs, kgs, ltrs, bags, bundles",
            style="Muted.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(0, 10))
        ttk.Button(
            add_frame, text="Add Unit", style="Primary.TButton", command=self._add_measurement_unit
        ).grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            add_frame, text="Remove Selected Unit", style="Secondary.TButton", command=self._remove_measurement_unit
        ).grid(row=4, column=0, sticky="ew")

    def _refresh_units_listbox(self) -> None:
        if not hasattr(self, "units_listbox"):
            return
        self.units_listbox.delete(0, "end")
        for unit in self.settings_service.get_measurement_units():
            self.units_listbox.insert("end", unit)

    def _add_measurement_unit(self) -> None:
        name = self.new_unit_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Unit", "Enter a unit name first.", parent=self)
            return
        try:
            self.settings_service.add_measurement_unit(name)
            self.new_unit_var.set("")
            self._refresh_units_listbox()
        except Exception as exc:
            messagebox.showerror("Unit Error", str(exc), parent=self)

    def _remove_measurement_unit(self) -> None:
        selection = self.units_listbox.curselection()
        if not selection:
            messagebox.showwarning("Select Unit", "Select a unit from the list to remove.", parent=self)
            return
        unit = self.units_listbox.get(selection[0])
        if not messagebox.askyesno("Confirm Remove", f"Remove unit '{unit}'?", parent=self):
            return
        try:
            self.settings_service.remove_measurement_unit(unit)
            self._refresh_units_listbox()
        except Exception as exc:
            messagebox.showerror("Remove Error", str(exc), parent=self)

    def _build_user_admin_section(self) -> None:
        self.admin_section = ttk.LabelFrame(self.body, text="User Accounts & Privileges", padding=18)
        self.admin_section.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
        self.admin_section.columnconfigure(0, weight=1)

        ttk.Label(
            self.admin_section,
            text="Create secure employee logins, assign exact platform access, and disable accounts when someone should not enter restricted areas. Employee names are selected from existing staff records only.",
            style="Muted.TLabel",
            wraplength=980,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.admin_main = ttk.Frame(self.admin_section, style="Surface.TFrame")
        self.admin_main.grid(row=1, column=0, sticky="nsew")
        self.admin_main.columnconfigure(0, weight=3)
        self.admin_main.columnconfigure(1, weight=2)

        self.user_grid_panel = ttk.Frame(self.admin_main, style="Surface.TFrame")
        self.user_grid_panel.columnconfigure(0, weight=1)
        self.user_grid_panel.rowconfigure(0, weight=1)

        columns = ("employee", "username", "role", "access", "status")
        self.user_tree = ttk.Treeview(self.user_grid_panel, columns=columns, show="headings", height=10)
        for key, title, width in (
            ("employee", "Employee", 220),
            ("username", "Username", 150),
            ("role", "Role", 130),
            ("access", "Accessible Areas", 340),
            ("status", "Status", 100),
        ):
            self.user_tree.heading(key, text=title)
            self.user_tree.column(key, width=width, anchor="center")
        self.user_tree.grid(row=0, column=0, sticky="nsew")
        self.user_tree.bind("<<TreeviewSelect>>", self._load_selected_user)
        user_y = ttk.Scrollbar(self.user_grid_panel, orient="vertical", command=self.user_tree.yview)
        user_y.grid(row=0, column=1, sticky="ns")
        user_x = ttk.Scrollbar(self.user_grid_panel, orient="horizontal", command=self.user_tree.xview)
        user_x.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.user_tree.configure(yscrollcommand=user_y.set, xscrollcommand=user_x.set)

        self.user_form_panel = ttk.Frame(self.admin_main, style="Surface.TFrame")
        self.user_form_panel.columnconfigure(0, weight=1)

        self.user_employee_var = tk.StringVar()
        self.user_username_var = tk.StringVar()
        self.user_role_var = tk.StringVar(value="Employee")
        self.user_theme_var = tk.StringVar(value=THEME_OPTIONS[0])
        self.user_password_var = tk.StringVar()
        self.user_confirm_var = tk.StringVar()
        self.user_active_var = tk.BooleanVar(value=True)
        self.employee_hint_var = tk.StringVar(
            value="Choose an existing employee from Staff & Attendance before creating login access."
        )
        self.permission_vars = {key: tk.BooleanVar(value=False) for key, _label, _desc in PERMISSION_DEFINITIONS}

        ttk.Label(self.user_form_panel, text="Linked Employee", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.employee_box = ttk.Combobox(
            self.user_form_panel,
            textvariable=self.user_employee_var,
            state="readonly",
        )
        self.employee_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.employee_box.bind("<<ComboboxSelected>>", self._on_employee_selected)
        ttk.Label(
            self.user_form_panel,
            textvariable=self.employee_hint_var,
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=2, column=0, sticky="ew", pady=(0, 12))

        make_labeled_entry(self.user_form_panel, "Username", self.user_username_var, 3, 0)

        ttk.Label(self.user_form_panel, text="Privilege Level", style="FormLabel.TLabel").grid(
            row=5, column=0, sticky="w", pady=(0, 4)
        )
        self.role_box = ttk.Combobox(
            self.user_form_panel,
            textvariable=self.user_role_var,
            values=ROLE_OPTIONS,
            state="readonly",
        )
        self.role_box.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        self.role_box.bind("<<ComboboxSelected>>", self._apply_role_defaults)
        ttk.Button(
            self.user_form_panel,
            text="Use Role Defaults",
            style="Secondary.TButton",
            command=self._apply_role_defaults,
        ).grid(row=7, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(
            self.user_form_panel,
            text="Tab & Security Access",
            style="FormLabel.TLabel",
        ).grid(row=8, column=0, sticky="w", pady=(0, 6))
        self.permission_frame = ttk.Frame(self.user_form_panel, style="Surface.TFrame")
        self.permission_frame.grid(row=9, column=0, sticky="ew", pady=(0, 12))
        self.permission_frame.columnconfigure(0, weight=1)
        self.permission_frame.columnconfigure(1, weight=1)

        for index, (key, label, description) in enumerate(PERMISSION_DEFINITIONS):
            check = ttk.Checkbutton(
                self.permission_frame,
                text=label,
                variable=self.permission_vars[key],
            )
            self.permission_checks[key] = check
            row = index // 2
            column = index % 2
            padx = (0, 12) if column == 0 else (12, 0)
            check.grid(row=row * 2, column=column, sticky="w", padx=padx)
            ttk.Label(
                self.permission_frame,
                text=description,
                style="Muted.TLabel",
                wraplength=180,
                justify="left",
            ).grid(row=row * 2 + 1, column=column, sticky="w", padx=padx, pady=(0, 10))

        ttk.Label(self.user_form_panel, text="Theme Palette", style="FormLabel.TLabel").grid(
            row=10, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Combobox(
            self.user_form_panel,
            textvariable=self.user_theme_var,
            values=THEME_OPTIONS,
            state="readonly",
        ).grid(row=11, column=0, sticky="ew", pady=(0, 10))

        make_labeled_entry(self.user_form_panel, "Temporary Password", self.user_password_var, 12, 0, show="*")
        make_labeled_entry(self.user_form_panel, "Confirm Password", self.user_confirm_var, 14, 0, show="*")
        ttk.Checkbutton(self.user_form_panel, text="Account is active", variable=self.user_active_var).grid(
            row=16, column=0, sticky="w", pady=(6, 10)
        )

        ttk.Label(
            self.user_form_panel,
            text="Note: My Pay access is reserved for employee accounts only. If you switch this account to another role, that tab is removed automatically.",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=17, column=0, sticky="ew", pady=(0, 10))

        actions = ttk.Frame(self.user_form_panel, style="Surface.TFrame")
        actions.grid(row=18, column=0, sticky="ew")
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(actions, text="Clear User Form", style="Secondary.TButton", command=self._reset_user_form).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(actions, text="Save User Account", style="Primary.TButton", command=self._save_user).grid(
            row=0, column=1, sticky="ew"
        )

    def _on_resize(self, _event=None) -> None:
        self.after_idle(self._apply_layout)

    def _apply_layout(self) -> None:
        width = max(self.winfo_width(), self.body.winfo_width(), 1)

        self.profile_frame.grid_forget()
        self.branding_frame.grid_forget()
        self.top_panel.columnconfigure(0, weight=0)
        self.top_panel.columnconfigure(1, weight=0)

        if width >= 1280:
            self.top_panel.columnconfigure(0, weight=1)
            self.top_panel.columnconfigure(1, weight=1)
            self.profile_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            self.branding_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.top_panel.columnconfigure(0, weight=1)
            self.profile_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
            self.branding_frame.grid(row=1, column=0, sticky="ew")

        if hasattr(self, "admin_main"):
            self.user_grid_panel.grid_forget()
            self.user_form_panel.grid_forget()
            self.admin_main.columnconfigure(0, weight=0)
            self.admin_main.columnconfigure(1, weight=0)

            if width >= 1400:
                self.admin_main.columnconfigure(0, weight=3)
                self.admin_main.columnconfigure(1, weight=2)
                self.user_grid_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
                self.user_form_panel.grid(row=0, column=1, sticky="nsew")
            else:
                self.admin_main.columnconfigure(0, weight=1)
                self.user_grid_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
                self.user_form_panel.grid(row=1, column=0, sticky="ew")

        self._sync_scrollregion()

    def update_current_user(self, current_user: dict) -> None:
        self.current_user = current_user
        self.refresh()

    def _save_profile(self) -> None:
        try:
            updated = self.user_service.update_profile(
                user_id=int(self.current_user["id"]),
                full_name=self.profile_name_var.get(),
                username=self.profile_username_var.get(),
                current_password=self.current_password_var.get(),
                new_password=self.new_password_var.get(),
                confirm_password=self.confirm_password_var.get(),
            )
            self.current_user.update(updated)
            self.on_profile_updated(updated)
            self.current_password_var.set("")
            self.new_password_var.set("")
            self.confirm_password_var.set("")
            self.refresh()
            messagebox.showinfo("Profile Updated", "Your account settings were saved successfully.", parent=self)
        except Exception as exc:
            messagebox.showerror("Profile Error", str(exc), parent=self)

    def _apply_theme_selection(self, _event=None) -> None:
        if self.live_theme_var.get() == self.current_user.get("theme_name"):
            return
        try:
            updated = self.user_service.update_theme_preference(int(self.current_user["id"]), self.live_theme_var.get())
            self.current_user.update(updated)
            self.theme_status_var.set(f"Theme saved: {updated['theme_name']}. Applied instantly across the app.")
            self.on_profile_updated(updated)
        except Exception as exc:
            self.theme_status_var.set("Theme changes are applied instantly across the app.")
            messagebox.showerror("Theme Error", str(exc), parent=self)
            self.refresh()

    def _handle_currency_change(self, *_args) -> None:
        self._update_currency_preview()

    def _update_currency_preview(self) -> None:
        preview = self.settings_service.format_money(
            12500.5,
            {
                "currency_symbol": self.currency_symbol_var.get(),
                "use_decimals": self.use_decimals_var.get(),
            },
        )
        self.currency_preview_var.set(f"Preview: {preview}")

    def _save_branding(self) -> None:
        try:
            updated = self.settings_service.update_branding(
                self.store_name_var.get(),
                self.currency_symbol_var.get(),
                self.use_decimals_var.get(),
            )
            self.on_branding_updated(updated)
            self._update_currency_preview()
            messagebox.showinfo("Branding Updated", "Store name and currency settings were saved successfully.", parent=self)
        except Exception as exc:
            messagebox.showerror("Branding Error", str(exc), parent=self)

    def _load_selected_user(self, _event=None) -> None:
        selection = self.user_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        self.selected_user_id = int(self.user_tree.item(item_id, "text"))
        user = self.user_service.get_user(self.selected_user_id)

        self.user_username_var.set(user["username"])
        self.user_role_var.set(user["role"])
        self.user_theme_var.set(user["theme_name"])
        self.user_active_var.set(bool(user["is_active"]))
        self.user_password_var.set("")
        self.user_confirm_var.set("")
        self._set_employee_selection(user.get("employee_id"), user)
        self._set_permission_selection(user.get("permissions", []))
        self._update_permission_controls()

    def _on_employee_selected(self, _event=None) -> None:
        employee = self.employee_lookup_by_label.get(self.user_employee_var.get())
        if employee is None:
            self.employee_hint_var.set("Choose an existing employee from Staff & Attendance before creating login access.")
            return
        self.employee_hint_var.set(
            f"Selected employee: {employee['full_name']} | Code: {employee['employee_code']} | Role: {employee['role']}"
        )

    def _selected_employee_id(self) -> int | None:
        employee = self.employee_lookup_by_label.get(self.user_employee_var.get())
        return int(employee["id"]) if employee else None

    def _set_employee_selection(self, employee_id: int | None, user: dict | None = None) -> None:
        if employee_id and int(employee_id) in self.employee_label_by_id:
            self.user_employee_var.set(self.employee_label_by_id[int(employee_id)])
            self._on_employee_selected()
            return

        self.user_employee_var.set("")
        if user and user.get("role") == "Administrator":
            self.employee_hint_var.set(
                "This administrator account is not linked to a staff record. New user accounts should be linked to existing employees."
            )
        else:
            self.employee_hint_var.set("Choose an existing employee from Staff & Attendance before creating login access.")

    def _set_permission_selection(self, permissions) -> None:
        selected = set(permissions or [])
        for key, variable in self.permission_vars.items():
            variable.set(key in selected)

    def _apply_role_defaults(self, _event=None) -> None:
        self._set_permission_selection(default_permissions_for_role(self.user_role_var.get()))
        self._update_permission_controls()

    def _update_permission_controls(self) -> None:
        if "view_payroll" not in self.permission_checks:
            return

        payroll_check = self.permission_checks["view_payroll"]
        if self.user_role_var.get() == "Employee":
            self.permission_vars["view_payroll"].set(True)
            payroll_check.state(["disabled"])
        else:
            self.permission_vars["view_payroll"].set(False)
            payroll_check.state(["disabled"])

    def _selected_permissions(self) -> list[str]:
        return [key for key, variable in self.permission_vars.items() if variable.get()]

    def _save_user(self) -> None:
        if self.user_password_var.get() != self.user_confirm_var.get():
            messagebox.showerror("Password Error", "Passwords do not match.", parent=self)
            return

        payload = {
            "employee_id": self._selected_employee_id(),
            "username": self.user_username_var.get(),
            "role": self.user_role_var.get(),
            "permissions": self._selected_permissions(),
            "theme_name": self.user_theme_var.get(),
            "password": self.user_password_var.get(),
            "is_active": self.user_active_var.get(),
        }

        try:
            if self.selected_user_id is None:
                if not payload["password"]:
                    raise ValueError("A password is required when creating a new login.")
                self.user_service.create_user(payload)
                messagebox.showinfo("User Saved", "New secure employee account created successfully.", parent=self)
            else:
                updated_user = self.user_service.update_user(
                    self.selected_user_id,
                    payload,
                    actor_user_id=int(self.current_user["id"]),
                )
                if updated_user["id"] == int(self.current_user["id"]):
                    updated_user.pop("password_hash", None)
                    self.current_user.update(updated_user)
                    self.on_profile_updated(updated_user)
                messagebox.showinfo("User Updated", "User account updated successfully.", parent=self)
            self.refresh()
            self._reset_user_form()
        except Exception as exc:
            messagebox.showerror("User Management Error", str(exc), parent=self)

    def _reset_user_form(self) -> None:
        self.selected_user_id = None
        self.user_employee_var.set("")
        self.user_username_var.set("")
        self.user_role_var.set("Employee")
        self.user_theme_var.set(THEME_OPTIONS[0])
        self.user_password_var.set("")
        self.user_confirm_var.set("")
        self.user_active_var.set(True)
        self.employee_hint_var.set("Choose an existing employee from Staff & Attendance before creating login access.")
        self._apply_role_defaults()
        if hasattr(self, "user_tree"):
            for selected in self.user_tree.selection():
                self.user_tree.selection_remove(selected)

    def refresh(self) -> None:
        self.profile_name_var.set(self.current_user.get("full_name", ""))
        self.profile_username_var.set(self.current_user.get("username", ""))
        self.live_theme_var.set(self.current_user.get("theme_name") or THEME_OPTIONS[0])
        self.role_summary_var.set(role_summary(self.current_user))
        if has_permission(self.current_user, "manage_themes"):
            self.theme_box.configure(state="readonly")
            self.theme_status_var.set("Theme changes are applied instantly across the app.")
        else:
            self.theme_box.configure(state="disabled")
            self.theme_status_var.set("Your account can view the current theme, but changing themes is disabled for this user.")

        branding = self.settings_service.get_app_settings()
        self.store_name_var.set(branding["store_name"])
        self.currency_symbol_var.set(branding["currency_symbol"])
        self.use_decimals_var.set(bool(branding["use_decimals"]))
        self._update_currency_preview()

        if not hasattr(self, "user_tree"):
            self._refresh_units_listbox()
            self._sync_scrollregion()
            return

        employees = self.employee_service.list_employees()
        self.employee_lookup_by_label = {
            f"{employee['employee_code']} | {employee['full_name']}": employee
            for employee in employees
        }
        self.employee_label_by_id = {
            int(employee["id"]): label
            for label, employee in self.employee_lookup_by_label.items()
        }
        self.employee_box["values"] = list(self.employee_lookup_by_label.keys())

        selected_user_id = self.selected_user_id
        selected_item = None

        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        for user in self.user_service.list_users():
            item_id = self.user_tree.insert(
                "",
                "end",
                text=str(user["id"]),
                values=(
                    user.get("employee_name") or user["full_name"],
                    user["username"],
                    user["role"],
                    ", ".join(permission_labels(user.get("permissions", []))),
                    "Active" if user["is_active"] else "Disabled",
                ),
            )
            if selected_user_id is not None and int(user["id"]) == int(selected_user_id):
                selected_item = item_id

        if selected_item is not None:
            self.user_tree.selection_set(selected_item)
            self.user_tree.focus(selected_item)
            self._load_selected_user()
        else:
            self._update_permission_controls()

        self._refresh_units_listbox()
        self._sync_scrollregion()

