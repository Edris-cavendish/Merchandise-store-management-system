from __future__ import annotations

from pathlib import Path

from app.config import COPYRIGHT_TEXT, STORE_NAME
from app.utils.currency import format_money
from app.utils.pdf_export import export_text_as_pdf


def build_receipt_text(receipt_payload: dict) -> str:
    store_name = receipt_payload.get("store_name", STORE_NAME)
    currency_symbol = receipt_payload.get("currency_symbol")
    use_decimals = receipt_payload.get("use_decimals", True)

    lines = [
        store_name,
        "Professional Sales Receipt",
        "=" * 60,
        f"Receipt No: {receipt_payload['receipt_no']}",
        f"Date/Time : {receipt_payload['date_time']}",
        f"Cashier   : {receipt_payload['cashier_name']}",
        f"Payment   : {receipt_payload['payment_method']}",
        "-" * 60,
        "Items",
        "-" * 60,
    ]
    for item in receipt_payload["items"]:
        unit_price = format_money(item["unit_price"], currency_symbol, use_decimals)
        line_total = format_money(item["line_total"], currency_symbol, use_decimals)
        lines.append(
            f"{item['name'][:20]:20} {item['quantity']:>3} x {unit_price:>12} = {line_total:>12}"
        )
    lines.extend(
        [
            "-" * 60,
            f"Subtotal : {format_money(receipt_payload['subtotal'], currency_symbol, use_decimals):>44}",
            f"Discount : {format_money(receipt_payload['discount_amount'], currency_symbol, use_decimals):>44}",
            f"Tax      : {format_money(receipt_payload['tax_amount'], currency_symbol, use_decimals):>44}",
            f"Total    : {format_money(receipt_payload['total'], currency_symbol, use_decimals):>44}",
            "=" * 60,
            COPYRIGHT_TEXT,
        ]
    )
    return "\n".join(lines)


def export_receipt_text(receipt_payload: dict, output_path: str) -> None:
    Path(output_path).write_text(build_receipt_text(receipt_payload), encoding="utf-8")


def export_receipt_pdf(receipt_payload: dict, output_path: str) -> None:
    export_text_as_pdf(build_receipt_text(receipt_payload), output_path)
