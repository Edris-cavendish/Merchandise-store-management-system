from __future__ import annotations

PERMISSION_DEFINITIONS = (
    ("view_dashboard", "Dashboard", "Open the main dashboard."),
    ("manage_inventory", "Inventory", "Manage products, stock, and categories."),
    ("manage_staff", "Staff & Attendance", "Manage employees, attendance, and payroll setup."),
    ("process_sales", "Sales & Billing", "Use the POS and generate receipts."),
    ("view_payroll", "My Pay", "View personal pay, overtime, and salary summaries."),
    ("manage_users", "User Accounts & Branding", "Manage logins, branding, and global settings."),
    ("manage_themes", "Theme Preferences", "Change interface theme settings."),
)

PERMISSION_KEYS = tuple(item[0] for item in PERMISSION_DEFINITIONS)
PERMISSION_LABELS = {key: label for key, label, _description in PERMISSION_DEFINITIONS}
PERMISSION_DESCRIPTIONS = {key: description for key, _label, description in PERMISSION_DEFINITIONS}

ROLE_PERMISSIONS = {
    "Administrator": {
        "view_dashboard",
        "manage_inventory",
        "manage_staff",
        "process_sales",
        "manage_users",
        "manage_themes",
    },
    "Manager": {
        "view_dashboard",
        "manage_inventory",
        "manage_staff",
        "process_sales",
        "manage_themes",
    },
    "Cashier": {
        "view_dashboard",
        "process_sales",
        "manage_themes",
    },
    "Employee": {
        "view_dashboard",
        "view_payroll",
        "manage_themes",
    },
}

ROLE_OPTIONS = tuple(ROLE_PERMISSIONS.keys())


def sanitize_permissions_for_role(
    permissions: set[str] | list[str] | tuple[str, ...],
    role: str,
) -> set[str]:
    permission_set = {permission for permission in permissions if permission in PERMISSION_KEYS}
    if role == "Employee":
        permission_set.add("view_payroll")
    else:
        permission_set.discard("view_payroll")
    return permission_set


def default_permissions_for_role(role: str) -> set[str]:
    return sanitize_permissions_for_role(ROLE_PERMISSIONS.get(role, set()), role)


def sort_permissions(permissions: set[str] | list[str] | tuple[str, ...]) -> list[str]:
    permission_set = set(permissions)
    return [key for key in PERMISSION_KEYS if key in permission_set]


def permission_label(permission: str) -> str:
    return PERMISSION_LABELS.get(permission, permission.replace("_", " ").title())


def permission_labels(permissions: set[str] | list[str] | tuple[str, ...]) -> list[str]:
    return [permission_label(permission) for permission in sort_permissions(set(permissions))]


def resolve_permissions(user_or_role: dict | str) -> set[str]:
    if isinstance(user_or_role, str):
        return default_permissions_for_role(user_or_role)

    explicit = user_or_role.get("permissions")
    if explicit is None:
        return default_permissions_for_role(user_or_role.get("role", ""))

    explicit_set = sanitize_permissions_for_role(explicit, user_or_role.get("role", ""))
    return explicit_set if explicit_set else default_permissions_for_role(user_or_role.get("role", ""))


def has_permission(user_or_role: dict | str, permission: str) -> bool:
    return permission in resolve_permissions(user_or_role)


def role_summary(user_or_role: dict | str) -> str:
    role = user_or_role if isinstance(user_or_role, str) else user_or_role.get("role", "")
    base_summaries = {
        "Administrator": "Full system control for branding, security, inventory, staff, and sales operations.",
        "Manager": "Strong operational access for staff, stock, sales, and shared business oversight.",
        "Cashier": "Focused selling access with dashboard visibility and theme preferences.",
        "Employee": "Personal work access with dashboard, pay information, and account preferences.",
    }
    labels = permission_labels(resolve_permissions(user_or_role))
    access_text = ", ".join(labels) if labels else "No platform areas assigned"
    return f"{base_summaries.get(role, 'Restricted account.')} Accessible areas: {access_text}."
