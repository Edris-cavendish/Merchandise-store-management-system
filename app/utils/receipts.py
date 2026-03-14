from __future__ import annotations

from pathlib import Path

from app.config import COPYRIGHT_TEXT, STORE_NAME
from app.utils.currency import format_money


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
    lines = build_receipt_text(receipt_payload).splitlines()
    content_lines: list[str] = []
    y_position = 780
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"BT /F1 11 Tf 40 {y_position} Td ({escaped}) Tj ET")
        y_position -= 16

    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("latin-1")
    )
    Path(output_path).write_bytes(pdf)
