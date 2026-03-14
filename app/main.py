from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from app.config import APP_NAME
from app.db.database import DatabaseManager
from app.services.auth_service import AuthService
from app.ui.app import SupermarketApp


def main() -> None:
    database = DatabaseManager()
    database.initialize()

    auth_service = AuthService(database)

    while True:
        current_user = auth_service.prompt_login()
        if current_user is None:
            return

        root = tk.Tk()
        root.title(APP_NAME)
        session_state = {"logout": False}

        def request_logout() -> None:
            session_state["logout"] = True
            root.after(0, root.destroy)

        try:
            app = SupermarketApp(root, database, current_user, on_logout=request_logout)
            app.pack(fill="both", expand=True)
            root.mainloop()
        except Exception as exc:
            if root.winfo_exists():
                messagebox.showerror("Application Error", str(exc), parent=root)
                root.destroy()
            else:
                fallback = tk.Tk()
                fallback.withdraw()
                messagebox.showerror("Application Error", str(exc), parent=fallback)
                fallback.destroy()
            break

        if not session_state["logout"]:
            break


if __name__ == "__main__":
    main()
