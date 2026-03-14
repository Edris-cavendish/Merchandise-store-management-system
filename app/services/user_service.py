from __future__ import annotations

from app.db.database import DatabaseManager
from app.services.access_control import (
    ROLE_OPTIONS,
    default_permissions_for_role,
    sanitize_permissions_for_role,
    sort_permissions,
)
from app.ui.theme import DEFAULT_THEME_NAME, THEME_OPTIONS, normalize_theme_name
from app.utils.security import hash_password, validate_password_strength, verify_password


class UserService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def list_users(self) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT
                u.id,
                u.employee_id,
                u.username,
                u.full_name,
                u.role,
                u.is_active,
                u.theme_name,
                u.created_at,
                e.full_name AS employee_name,
                e.employee_code
            FROM users u
            LEFT JOIN employees e ON e.id = u.employee_id
            ORDER BY COALESCE(e.full_name, u.full_name), u.username
            """
        )
        users = [dict(row) for row in rows]
        for user in users:
            user["permissions"] = self._permissions_for_user(int(user["id"]), user["role"])
        return users

    def get_user(self, user_id: int) -> dict:
        row = self.database.fetch_one(
            """
            SELECT
                u.id,
                u.employee_id,
                u.username,
                u.full_name,
                u.role,
                u.is_active,
                u.theme_name,
                u.created_at,
                u.password_hash,
                e.full_name AS employee_name,
                e.employee_code
            FROM users u
            LEFT JOIN employees e ON e.id = u.employee_id
            WHERE u.id = ?
            """,
            (user_id,),
        )
        if row is None:
            raise ValueError("User account not found.")
        user = dict(row)
        user["permissions"] = self._permissions_for_user(user_id, user["role"])
        return user

    def update_theme_preference(self, user_id: int, theme_name: str) -> dict:
        normalized_theme = normalize_theme_name(theme_name)
        self.database.execute(
            "UPDATE users SET theme_name = ? WHERE id = ?",
            (normalized_theme, user_id),
        )
        updated = self.get_user(user_id)
        updated.pop("password_hash", None)
        return updated

    def create_user(self, payload: dict) -> int:
        username = payload.get("username", "").strip()
        password = payload.get("password", "")
        role = payload.get("role", "Employee")
        theme_name = normalize_theme_name(payload.get("theme_name", DEFAULT_THEME_NAME))
        is_active = 1 if payload.get("is_active", True) else 0
        employee = self._employee_record(payload.get("employee_id"))
        permissions = self._normalized_permissions(payload.get("permissions"), role)

        if employee is None:
            raise ValueError("Select an existing employee before creating login credentials.")
        if not username:
            raise ValueError("Username is required.")
        if role not in ROLE_OPTIONS:
            raise ValueError("Choose a valid privilege level.")
        if theme_name not in THEME_OPTIONS:
            raise ValueError("Choose a valid theme.")

        self._ensure_username_available(username)
        self._ensure_employee_available(int(employee["id"]))
        validate_password_strength(password)

        user_id = self.database.execute(
            """
            INSERT INTO users (employee_id, username, password_hash, full_name, role, is_active, theme_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(employee["id"]),
                username,
                hash_password(password),
                employee["full_name"],
                role,
                is_active,
                theme_name,
            ),
        )
        self._save_permissions(user_id, permissions)
        return user_id

    def update_user(self, user_id: int, payload: dict, actor_user_id: int) -> dict:
        existing = self.get_user(user_id)
        username = payload.get("username", existing["username"]).strip()
        role = payload.get("role", existing["role"])
        theme_name = normalize_theme_name(payload.get("theme_name", existing["theme_name"]))
        is_active = 1 if payload.get("is_active", bool(existing["is_active"])) else 0
        password = payload.get("password", "")
        employee = self._employee_record(payload.get("employee_id", existing.get("employee_id")))
        permissions = self._normalized_permissions(payload.get("permissions"), role)

        if not username:
            raise ValueError("Username is required.")
        if role not in ROLE_OPTIONS:
            raise ValueError("Choose a valid privilege level.")
        if user_id == actor_user_id and (is_active == 0 or role != existing["role"]):
            raise ValueError("You cannot deactivate or change your own privilege level while signed in.")
        if employee is None and role != "Administrator":
            raise ValueError("Select an existing employee for this account.")

        self._ensure_username_available(username, exclude_user_id=user_id)
        if employee is not None:
            self._ensure_employee_available(int(employee["id"]), exclude_user_id=user_id)
            full_name = employee["full_name"]
            employee_id = int(employee["id"])
        else:
            full_name = existing["full_name"]
            employee_id = None

        if password:
            validate_password_strength(password)
            password_hash = hash_password(password)
        else:
            password_hash = existing["password_hash"]

        self.database.execute(
            """
            UPDATE users
            SET employee_id = ?, username = ?, full_name = ?, role = ?, is_active = ?, theme_name = ?, password_hash = ?
            WHERE id = ?
            """,
            (employee_id, username, full_name, role, is_active, theme_name, password_hash, user_id),
        )
        self._save_permissions(user_id, permissions)
        return self.get_user(user_id)

    def update_profile(
        self,
        user_id: int,
        full_name: str,
        username: str,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> dict:
        user = self.get_user(user_id)
        if not verify_password(current_password, user["password_hash"]):
            raise ValueError("Current password is incorrect.")

        full_name = full_name.strip()
        username = username.strip()
        if not full_name or not username:
            raise ValueError("Full name and username are required.")

        self._ensure_username_available(username, exclude_user_id=user_id)

        password_hash = user["password_hash"]
        if new_password or confirm_password:
            if new_password != confirm_password:
                raise ValueError("New password and confirmation do not match.")
            validate_password_strength(new_password)
            password_hash = hash_password(new_password)

        self.database.execute(
            """
            UPDATE users
            SET full_name = ?, username = ?, password_hash = ?
            WHERE id = ?
            """,
            (full_name, username, password_hash, user_id),
        )
        updated = self.get_user(user_id)
        updated.pop("password_hash", None)
        return updated

    def _employee_record(self, employee_id: int | str | None) -> dict | None:
        if employee_id in (None, ""):
            return None
        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Choose a valid employee record.") from exc

        row = self.database.fetch_one(
            "SELECT id, full_name, employee_code FROM employees WHERE id = ?",
            (employee_id,),
        )
        if row is None:
            raise ValueError("Select an existing employee from the staff records.")
        return dict(row)

    def _ensure_username_available(self, username: str, exclude_user_id: int | None = None) -> None:
        existing = self.database.fetch_one("SELECT id FROM users WHERE username = ?", (username,))
        if existing and int(existing["id"]) != exclude_user_id:
            raise ValueError("That username is already in use.")

    def _ensure_employee_available(self, employee_id: int, exclude_user_id: int | None = None) -> None:
        existing = self.database.fetch_one("SELECT id FROM users WHERE employee_id = ?", (employee_id,))
        if existing and int(existing["id"]) != exclude_user_id:
            raise ValueError("This employee already has login credentials assigned.")

    def _permissions_for_user(self, user_id: int, role: str) -> list[str]:
        rows = self.database.fetch_all(
            "SELECT permission_key FROM user_permissions WHERE user_id = ? ORDER BY permission_key",
            (user_id,),
        )
        if not rows:
            return sort_permissions(default_permissions_for_role(role))
        return sort_permissions(sanitize_permissions_for_role({row["permission_key"] for row in rows}, role))

    def _normalized_permissions(self, permissions, role: str) -> list[str]:
        if permissions is None:
            return sort_permissions(default_permissions_for_role(role))
        return sort_permissions(sanitize_permissions_for_role(set(permissions), role))

    def _save_permissions(self, user_id: int, permissions: list[str]) -> None:
        self.database.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        if permissions:
            self.database.execute_many(
                "INSERT INTO user_permissions (user_id, permission_key) VALUES (?, ?)",
                [(user_id, permission) for permission in permissions],
            )
