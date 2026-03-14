from __future__ import annotations

from pathlib import Path


APP_NAME = "Supermarket Attendance & Management System"
WINDOW_SIZE = "1480x900"
COPYRIGHT_TEXT = "Developed by Ssemujju Edris | Copyright 2026"
STORE_NAME = "Edris Supermarket"
DEFAULT_VAT_RATE = 0.16
DEFAULT_DISCOUNT_RATE = 0.00
OVERTIME_MULTIPLIER = 1.5
STANDARD_SHIFT_HOURS = 8
STANDARD_MONTHLY_HOURS = 176

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATA_DIR / "supermarket.db"
