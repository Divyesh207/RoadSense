"""
Report artifact renderers: the same report content (a JSON-serialisable dict built from live
analytics) rendered as JSON, CSV or PDF. No values are added or estimated here; CSV and PDF
are flattened views of exactly the data in the JSON representation.

The Road Health report has its own designed PDF layout (road_health_pdf), used when the content
carries the "road_health_detail" data. Every other report type uses the plain PDF 1.4 text
writer below (Helvetica, A4, multi-page, no third-party dependencies).
"""

import csv
import io
import json
from typing import Any

SUPPORTED_FORMATS = {
    "JSON": ("json", "application/json"),
    "CSV": ("csv", "text/csv"),
    "PDF": ("pdf", "application/pdf"),
}


def flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten nested dicts/lists into (dotted.path, value) rows."""
    rows: list[tuple[str, str]] = []
    if isinstance(value, dict):
        if not value and prefix:
            rows.append((prefix, ""))
        for k, v in value.items():
            rows.extend(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(value, list):
        if not value and prefix:
            rows.append((prefix, "(none)"))
        for i, v in enumerate(value):
            rows.extend(flatten(v, f"{prefix}[{i}]"))
    else:
        rows.append((prefix, "" if value is None else str(value)))
    return rows


def render_json(content: dict[str, Any]) -> bytes:
    return json.dumps(content, default=str, indent=2).encode("utf-8")


def render_csv(content: dict[str, Any]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["section", "field", "value"])
    for key in ("report_type", "organization_id", "generated_at"):
        writer.writerow(["report", key, content.get(key, "")])
    for path, value in flatten(content.get("parameters") or {}):
        writer.writerow(["parameters", path, value])
    for section, data in (content.get("sections") or {}).items():
        rows = flatten(data)
        if not rows:
            writer.writerow([section, "", "(no data)"])
        for path, value in rows:
            writer.writerow([section, path, value])
    return out.getvalue().encode("utf-8")


# --- PDF -------------------------------------------------------------------------------------

_PAGE_W, _PAGE_H = 595, 842  # A4 in points
_MARGIN = 50
_LEADING = 13
_MAX_CHARS = 95


def _pdf_text(s: str) -> str:
    # Helvetica (WinAnsi) covers Latin-1; anything else is replaced rather than corrupting the file.
    s = s.encode("latin-1", "replace").decode("latin-1")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(line: str, width: int = _MAX_CHARS) -> list[str]:
    if len(line) <= width:
        return [line]
    out, rest = [], line
    while len(rest) > width:
        cut = rest.rfind(" ", 0, width)
        cut = cut if cut > width // 3 else width
        out.append(rest[:cut])
        rest = "    " + rest[cut:].lstrip()
    out.append(rest)
    return out


def _report_lines(content: dict[str, Any]) -> list[tuple[str, str]]:
    """(style, text) lines; style is 'title', 'heading' or 'body'."""
    title = str(content.get("report_type", "REPORT")).replace("_", " ").title() + " Report"
    lines: list[tuple[str, str]] = [("title", title)]
    lines.append(("body", f"Generated at: {content.get('generated_at', '')}"))
    lines.append(("body", f"Organization: {content.get('organization_id', '')}"))
    params = {k: v for k, v in (content.get("parameters") or {}).items()}
    if params:
        lines.append(("body", "Parameters: " + ", ".join(f"{k}={v}" for k, v in params.items())))
    lines.append(("body", "Values are taken from the platform's stored records at generation time."))
    for section, data in (content.get("sections") or {}).items():
        lines.append(("heading", section.replace("_", " ").title()))
        rows = flatten(data)
        if not rows:
            lines.append(("body", "(no data)"))
        for path, value in rows:
            for part in _wrap(f"{path}: {value if value != '' else '-'}"):
                lines.append(("body", part))
    return lines


def render_pdf(content: dict[str, Any]) -> bytes:
    detail = content.get("road_health_detail")
    if detail:
        from app.services.road_health_pdf import render_road_health_pdf

        return render_road_health_pdf(detail)
    styles = {"title": ("F2", 16, 2.0), "heading": ("F2", 12, 1.6), "body": ("F1", 9, 1.0)}
    pages: list[list[str]] = [[]]
    y = _PAGE_H - _MARGIN
    for style, text in _report_lines(content):
        font, size, gap = styles[style]
        step = _LEADING * gap
        if y - step < _MARGIN:
            pages.append([])
            y = _PAGE_H - _MARGIN
        y -= step
        pages[-1].append(f"BT /{font} {size} Tf {_MARGIN} {y:.1f} Td ({_pdf_text(text)}) Tj ET")
    total = len(pages)
    for n, ops in enumerate(pages, 1):
        ops.append(f"BT /F1 8 Tf {_PAGE_W - _MARGIN - 60} 30 Td (Page {n} of {total}) Tj ET")

    objects: list[bytes] = []

    def add(obj: str | bytes) -> int:
        objects.append(obj.encode("latin-1") if isinstance(obj, str) else obj)
        return len(objects)

    catalog = add("")  # placeholder, filled once the pages object id is known
    pages_id = add("")
    font1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    page_ids = []
    for ops in pages:
        stream = "\n".join(ops).encode("latin-1")
        content_id = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_ids.append(add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
            f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R >> >> /Contents {content_id} 0 R >>"
        ))
    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1")
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode("latin-1") + obj + b"\nendobj\n")
    xref = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets:
        buf.write(f"{off:010d} 00000 n \n".encode("latin-1"))
    buf.write(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1"))
    return buf.getvalue()


RENDERERS = {"JSON": render_json, "CSV": render_csv, "PDF": render_pdf}
