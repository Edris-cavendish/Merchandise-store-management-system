from __future__ import annotations

from pathlib import Path
import textwrap


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def export_text_as_pdf(
    text: str,
    output_path: str,
    *,
    landscape: bool = False,
    font_size: int = 11,
    margin: int = 36,
) -> None:
    """Export plain text to a portable multi-page PDF with optional landscape layout."""
    page_width, page_height = (842, 612) if landscape else (612, 842)
    line_height = max(font_size + 4, 12)
    usable_width = max(page_width - (margin * 2), 100)
    # Courier's average character width is roughly 0.6em.
    max_chars = max(int(usable_width / max(font_size * 0.6, 1)), 20)
    lines_per_page = max(int((page_height - (margin * 2)) / line_height), 1)

    source_lines = text.splitlines() or [""]
    wrapped_lines: list[str] = []
    for raw_line in source_lines:
        line = raw_line.expandtabs(4)
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.wrap(line, width=max_chars, replace_whitespace=False, drop_whitespace=False))

    pages: list[list[str]] = []
    for index in range(0, len(wrapped_lines), lines_per_page):
        pages.append(wrapped_lines[index : index + lines_per_page])
    if not pages:
        pages = [[""]]

    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")

    page_count = len(pages)
    first_page_id = 3
    kids = " ".join(f"{first_page_id + (i * 2)} 0 R" for i in range(page_count))
    objects.append(f"2 0 obj << /Type /Pages /Count {page_count} /Kids [{kids}] >> endobj\n".encode("latin-1"))

    font_id = first_page_id + (page_count * 2)
    for i, page_lines in enumerate(pages):
        page_id = first_page_id + (i * 2)
        content_id = page_id + 1

        content_lines: list[str] = []
        y_position = page_height - margin
        for line in page_lines:
            escaped = _escape_pdf_text(line)
            content_lines.append(f"BT /F1 {font_size} Tf {margin} {y_position} Td ({escaped}) Tj ET")
            y_position -= line_height

        stream = "\n".join(content_lines).encode("latin-1", errors="replace")
        objects.append(
            (
                f"{page_id} 0 obj << /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {page_width} {page_height}] /Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> >> endobj\n"
            ).encode("latin-1")
        )
        objects.append(
            f"{content_id} 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1")
            + stream
            + b"\nendstream endobj\n"
        )

    objects.append(f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n".encode("latin-1"))

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
