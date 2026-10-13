"""
Road Health Assessment Report: PDF layout (A4, selectable text, ReportLab).

Input is the dict built by road_health_report.build_road_health_detail. This module only lays
that data out and words it; it does not calculate scores or add figures. Where the data has no
value the report says "not recorded" or leaves the block out.
"""

import io
from datetime import datetime, timezone
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_W, PAGE_H = A4
MARGIN = 42
CONTENT_W = PAGE_W - 2 * MARGIN

INK = colors.HexColor("#111827")
BODY = colors.HexColor("#374151")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E5E7EB")
PANEL = colors.HexColor("#F4F5F7")
BRAND = colors.HexColor("#0B0B0C")

STATUS_COLOR = {
    "GOOD": colors.HexColor("#0F9D6B"),
    "FAIR": colors.HexColor("#C98A04"),
    "POOR": colors.HexColor("#DD6B20"),
    "CRITICAL": colors.HexColor("#C5302B"),
    "INSUFFICIENT_DATA": colors.HexColor("#8A8F98"),
}
SEVERITY_COLOR = {
    "CRITICAL": colors.HexColor("#C5302B"),
    "HIGH": colors.HexColor("#DD6B20"),
    "MEDIUM": colors.HexColor("#C98A04"),
    "LOW": colors.HexColor("#4B7C9B"),
}
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
STATUS_LABEL = {
    "GOOD": "Good",
    "FAIR": "Fair",
    "POOR": "Poor",
    "CRITICAL": "Critical",
    "INSUFFICIENT_DATA": "Not enough data",
}
DAMAGE_STATUS_LABEL = {
    "DETECTED": "Detected",
    "CONFIRMED": "Confirmed",
    "MAINTENANCE_SCHEDULED": "Repair scheduled",
    "IN_PROGRESS": "Repair in progress",
}

# Health score rules of health_engine (calculation version health-v1.1.0), restated for the
# methodology section. Keep in step with health_engine.calculate_segment_health.
HEALTH_BANDS = [("GOOD", 80, 100), ("FAIR", 60, 80), ("POOR", 40, 60), ("CRITICAL", 0, 40)]
DEDUCTION_RULES = {"CRITICAL": (25.0, 60.0), "HIGH": (15.0, 45.0), "MEDIUM": (7.0, 35.0), "LOW": (2.5, 20.0)}
RECURRENCE_RULE = (5.0, 25.0)

# General response guidance per severity level. The platform records no repair deadlines, so
# none are stated; due dates in the report come only from maintenance jobs.
SEVERITY_GUIDANCE = {
    "CRITICAL": "Requires immediate assessment or intervention.",
    "HIGH": "Requires prompt attention.",
    "MEDIUM": "Should be addressed within an appropriate maintenance cycle.",
    "LOW": "Monitor, or address through routine maintenance.",
}
MAX_DEFECT_ROWS = 150
MAX_PHOTOS = 6


def _style(name: str, **kw: Any) -> ParagraphStyle:
    base = {"fontName": "Helvetica", "fontSize": 9.5, "leading": 13.5, "textColor": BODY}
    base.update(kw)
    return ParagraphStyle(name, **base)


S = {
    "body": _style("body"),
    "small": _style("small", fontSize=8, leading=11, textColor=MUTED),
    "cell": _style("cell", fontSize=8.5, leading=11),
    "cellb": _style("cellb", fontSize=8.5, leading=11, fontName="Helvetica-Bold", textColor=INK),
    "th": _style("th", fontSize=7.5, leading=10, fontName="Helvetica-Bold", textColor=colors.white),
    "h1": _style("h1", fontSize=16, leading=20, fontName="Helvetica-Bold", textColor=INK, spaceBefore=4, spaceAfter=3),
    "h2": _style("h2", fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=INK, spaceBefore=10, spaceAfter=4),
    "eyebrow": _style("eyebrow", fontSize=7.5, leading=10, fontName="Helvetica-Bold", textColor=MUTED),
    "lead": _style("lead", fontSize=10.5, leading=15, textColor=INK),
    "label": _style("label", fontSize=7.5, leading=10, fontName="Helvetica-Bold", textColor=MUTED),
    "value": _style("value", fontSize=20, leading=23, fontName="Helvetica-Bold", textColor=INK),
    "note": _style("note", fontSize=8, leading=10.5, textColor=MUTED),
    "bullet": _style("bullet", leftIndent=12, bulletIndent=2, spaceAfter=2),
}


def _t(value: Any) -> str:
    """Text safe for the built-in PDF fonts (Windows-1252) and for Paragraph markup."""
    text = "" if value is None else str(value)
    return escape(text.encode("cp1252", "replace").decode("cp1252"))


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _dt(value: Any, missing: str = "Not recorded") -> str:
    dt = _parse(value)
    return f"{dt:%d %b %Y, %H:%M} UTC" if dt else missing


def _date(value: Any, missing: str = "Not recorded") -> str:
    dt = _parse(value)
    return f"{dt:%d %b %Y}" if dt else missing


def _score(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.1f}"


def _plural(n: int, word: str, plural: str | None = None) -> str:
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


class Chip(Flowable):
    """A small filled label, used for condition and severity."""

    def __init__(self, text: str, color: colors.Color, size: float = 7):
        super().__init__()
        self.text, self.color, self.size = text, color, size
        self.width = stringWidth(text, "Helvetica-Bold", size) + 10
        self.height = size + 6

    def wrap(self, *_: Any) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.width, self.height, 2.5, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", self.size)
        c.drawString(5, 3.4, self.text)


class ScoreGauge(Flowable):
    """0-100 scale with the four condition bands and a marker at the score."""

    def __init__(self, score: float | None, width: float = CONTENT_W):
        super().__init__()
        self.score, self.width, self.height = score, width, 46

    def wrap(self, *_: Any) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c, w, y, h = self.canv, self.width, 16, 10
        for status, lo, hi in HEALTH_BANDS:
            c.setFillColor(STATUS_COLOR[status])
            c.rect(w * lo / 100, y, w * (hi - lo) / 100, h, stroke=0, fill=1)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 7)
            c.drawCentredString(w * (lo + hi) / 200, 4, f"{STATUS_LABEL[status]} ({lo}-{hi if hi == 100 else hi - 1})")
        c.setStrokeColor(colors.white)
        c.setLineWidth(1)
        for mark in (40, 60, 80):
            c.line(w * mark / 100, y, w * mark / 100, y + h)
        if self.score is not None:
            x = max(4, min(w - 4, w * float(self.score) / 100))
            c.setFillColor(INK)
            path = c.beginPath()
            path.moveTo(x, y + h + 1)
            path.lineTo(x - 4.5, y + h + 8)
            path.lineTo(x + 4.5, y + h + 8)
            path.close()
            c.drawPath(path, stroke=0, fill=1)
            c.setFont("Helvetica-Bold", 9)
            label = f"{float(self.score):.1f}"
            lx = max(stringWidth(label, "Helvetica-Bold", 9) / 2, min(w - stringWidth(label, "Helvetica-Bold", 9) / 2, x))
            c.drawCentredString(lx, y + h + 10.5, label)


class StackedBar(Flowable):
    """One horizontal bar split by category, with a legend underneath."""

    def __init__(self, parts: list[tuple[str, int, colors.Color]], width: float = CONTENT_W):
        super().__init__()
        self.parts, self.width, self.height = parts, width, 34

    def wrap(self, *_: Any) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c, total = self.canv, sum(n for _, n, _ in self.parts)
        x = 0.0
        if total == 0:
            c.setFillColor(LINE)
            c.rect(0, 18, self.width, 12, stroke=0, fill=1)
        for _, n, color in self.parts:
            if n <= 0:
                continue
            seg = self.width * n / total
            c.setFillColor(color)
            c.rect(x, 18, seg, 12, stroke=0, fill=1)
            if seg > 14:
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 8)
                c.drawCentredString(x + seg / 2, 21.3, str(n))
            x += seg
        lx = 0.0
        c.setFont("Helvetica", 7.5)
        for label, n, color in self.parts:
            c.setFillColor(color)
            c.rect(lx, 3, 7, 7, stroke=0, fill=1)
            c.setFillColor(BODY)
            text = f"{label}: {n}"
            c.drawString(lx + 10, 3.5, text)
            lx += stringWidth(text, "Helvetica", 7.5) + 26


class BarList(Flowable):
    """Horizontal bars for a short list of (label, count)."""

    def __init__(self, rows: list[tuple[str, int]], width: float = CONTENT_W, color: colors.Color = INK):
        super().__init__()
        self.rows, self.width, self.color = rows, width, color
        self.height = 16 * len(rows) + 2

    def wrap(self, *_: Any) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        label_w = 150
        top = max((n for _, n in self.rows), default=0) or 1
        y = self.height - 14
        for label, n in self.rows:
            c.setFillColor(BODY)
            c.setFont("Helvetica", 8.5)
            c.drawString(0, y + 2, label[:34])
            bar = (self.width - label_w - 30) * n / top
            c.setFillColor(self.color)
            c.rect(label_w, y, max(bar, 1), 9, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(label_w + max(bar, 1) + 5, y + 1.5, str(n))
            y -= 16


class LocationPlot(Flowable):
    """Stored segment lines and defect positions plotted from their recorded coordinates.
    It is a position plot, not a base map: no streets or imagery are drawn."""

    def __init__(self, segments: list[dict[str, Any]], defects: list[dict[str, Any]], width: float = CONTENT_W, height: float = 225):
        super().__init__()
        self.segments = [s for s in segments if s.get("line")]
        self.defects = [d for d in defects if d.get("lat") is not None and d.get("lon") is not None]
        self.width, self.height = width, height

    def wrap(self, *_: Any) -> tuple[float, float]:
        return self.width, self.height

    def has_data(self) -> bool:
        return bool(self.segments or self.defects)

    def draw(self) -> None:
        c = self.canv
        lons = [p[0] for s in self.segments for p in s["line"]] + [d["lon"] for d in self.defects]
        lats = [p[1] for s in self.segments for p in s["line"]] + [d["lat"] for d in self.defects]
        c.setFillColor(PANEL)
        c.setStrokeColor(LINE)
        c.rect(0, 0, self.width, self.height, stroke=1, fill=1)
        if not lons:
            return
        import math

        lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
        kx = math.cos(math.radians((lat0 + lat1) / 2)) or 1.0  # keep distances in proportion
        span_x = max((lon1 - lon0) * kx, 1e-5)
        span_y = max(lat1 - lat0, 1e-5)
        pad = 22
        scale = min((self.width - 2 * pad) / span_x, (self.height - 2 * pad) / span_y)
        off_x = (self.width - span_x * scale) / 2
        off_y = (self.height - span_y * scale) / 2

        def xy(lon: float, lat: float) -> tuple[float, float]:
            return off_x + (lon - lon0) * kx * scale, off_y + (lat - lat0) * scale

        c.setLineCap(1)
        for s in self.segments:
            c.setStrokeColor(STATUS_COLOR.get(s["status"], MUTED))
            c.setLineWidth(3)
            path = c.beginPath()
            x, y = xy(*s["line"][0])
            path.moveTo(x, y)
            for pt in s["line"][1:]:
                path.lineTo(*xy(*pt))
            c.drawPath(path, stroke=1, fill=0)
        for d in reversed(self.defects):  # most severe drawn last, on top
            x, y = xy(d["lon"], d["lat"])
            c.setFillColor(SEVERITY_COLOR.get(d["severity"], MUTED))
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.8)
            c.circle(x, y, 3.6, stroke=1, fill=1)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawString(4, 4, f"SW {lat0:.5f}, {lon0:.5f}")
        c.drawRightString(self.width - 4, self.height - 9, f"NE {lat1:.5f}, {lon1:.5f}")
        c.drawRightString(self.width - 4, 4, "North is up. Plotted from stored coordinates; no base map.")


def _table(data: list[list[Any]], widths: list[float], header: bool = True, zebra: bool = True) -> Table:
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), INK), ("LINEBELOW", (0, 0), (-1, 0), 0, INK)]
    if zebra:
        style.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#FAFAFB")]))
    table.setStyle(TableStyle(style))
    return table


def _th(*labels: str) -> list[Paragraph]:
    return [P(_t(label), "th") for label in labels]


def _cards(cards: list[tuple[str, str, str, colors.Color | None]]) -> Table:
    cells = []
    for label, value, note, color in cards:
        value_style = ParagraphStyle("v", parent=S["value"], textColor=color or INK)
        cells.append([P(_t(label).upper(), "label"), Paragraph(_t(value), value_style), P(_t(note), "note")])
    gap = 8
    width = (CONTENT_W - gap * (len(cells) - 1)) / len(cells)
    row, widths = [], []
    for i, cell in enumerate(cells):
        inner = Table([[c] for c in cell], colWidths=[width - 20])
        inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        row.append(inner)
        widths.append(width)
        if i < len(cells) - 1:
            row.append("")
            widths.append(gap)
    table = Table([row], colWidths=widths)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]
    for i in range(0, len(row), 2):
        style += [
            ("BACKGROUND", (i, 0), (i, 0), PANEL),
            ("LEFTPADDING", (i, 0), (i, 0), 10),
            ("RIGHTPADDING", (i, 0), (i, 0), 10),
            ("TOPPADDING", (i, 0), (i, 0), 9),
            ("BOTTOMPADDING", (i, 0), (i, 0), 9),
        ]
    table.setStyle(TableStyle(style))
    return table


def _callout(text: str, color: colors.Color = INK) -> Table:
    table = Table([[P(text, "body")]], colWidths=[CONTENT_W])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _section(number: int, title: str) -> list[Flowable]:
    return [CondPageBreak(170), Spacer(1, 10), P(f"SECTION {number}", "eyebrow"), P(_t(title), "h1")]


def H2(title: str) -> list[Flowable]:
    """Sub-heading that never sits alone at the bottom of a page."""
    return [CondPageBreak(90), P(_t(title), "h2")]


def _where(item: dict[str, Any]) -> str:
    road = item.get("road") or "Road not recorded"
    return f"{road}, {item.get('segment')}"


def _basis(defect: dict[str, Any]) -> str:
    if str(defect.get("source")).upper() != "AI":
        return "Entered by a person"
    return "AI detection, reviewed" if defect.get("reviewed") else "AI detection, not yet reviewed"


def _action(defect: dict[str, Any], now: datetime | None = None) -> tuple[str, str]:
    """(recommended action, due date text), from the defect's stored status and maintenance job."""
    job = defect.get("job")
    if job:
        title = f"\"{job.get('title')}\""
        status = str(job.get("status") or "").upper()
        due_at = _parse(job.get("due_at"))
        due = _date(job.get("due_at"), "No due date recorded")
        if status in ("COMPLETED", "VERIFICATION_PENDING"):
            return f"Verify the completed repair: job {title} is waiting for verification.", due
        if status == "REJECTED":
            return f"Redo the repair: job {title} was rejected at verification.", due
        if due_at is not None and now is not None and due_at < now:
            due += " (overdue)"
        if status == "IN_PROGRESS":
            return f"Finish the repair in progress: job {title}.", due
        return f"Carry out maintenance job {title} (currently {status.replace('_', ' ').lower()}).", due
    status = defect.get("status")
    if status == "DETECTED":
        return "Have a reviewer confirm the detection, then schedule a repair.", "No job yet"
    if status == "CONFIRMED":
        return "Create and schedule a maintenance job.", "No job yet"
    return "Follow up the repair recorded for this defect; no open job is linked to it.", "No due date recorded"


def _photo(defect: dict[str, Any], max_w: float, max_h: float) -> Image | None:
    """The stored inspection photo, reduced for print. None when it cannot be read."""
    ref = defect.get("photo")
    if not ref:
        return None
    try:
        from PIL import Image as PILImage
        from PIL import ImageOps

        from app.services.storage import get_storage_backend

        path = get_storage_backend().fetch_to_local_path(ref["bucket"], ref["path"])
        with PILImage.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((1100, 1100))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=78)
            w, h = img.size
        buf.seek(0)
        ratio = min(max_w / w, max_h / h)
        return Image(buf, width=w * ratio, height=h * ratio)
    except Exception:  # noqa: BLE001 - a missing or unreadable photo must never fail the report
        return None


class _NumberedCanvas(Canvas):
    """Draws the running header and footer once the total page count is known."""

    def __init__(self, *args: Any, meta: dict[str, str] | None = None, **kwargs: Any):
        kwargs["pdfVersion"] = (1, 4)
        super().__init__(*args, **kwargs)
        self._meta = meta or {}
        self._pages: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._pages)
        for number, state in enumerate(self._pages, 1):
            self.__dict__.update(state)
            self._chrome(number, total)
            super().showPage()
        super().save()

    def _chrome(self, number: int, total: int) -> None:
        self.setFont("Helvetica", 7.5)
        self.setFillColor(MUTED)
        self.setStrokeColor(LINE)
        self.setLineWidth(0.5)
        self.line(MARGIN, 34, PAGE_W - MARGIN, 34)
        self.drawString(MARGIN, 23, f"Report ID {self._meta.get('report_id', '')}  |  Generated {self._meta.get('generated', '')}")
        self.drawRightString(PAGE_W - MARGIN, 23, f"Page {number} of {total}")
        if number > 1:
            self.drawString(MARGIN, PAGE_H - 28, "ROAD HEALTH ASSESSMENT REPORT")
            self.drawRightString(PAGE_W - MARGIN, PAGE_H - 28, self._meta.get("scope", ""))
            self.line(MARGIN, PAGE_H - 34, PAGE_W - MARGIN, PAGE_H - 34)


def _cover_band(canvas: Canvas, _doc: Any) -> None:
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 250, PAGE_W, 250, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN, PAGE_H - 62, "ROAD INTELLIGENCE")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#A1A1AA"))
    canvas.drawString(MARGIN, PAGE_H - 75, "Road condition monitoring and pothole management platform")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawString(MARGIN, PAGE_H - 165, "Road Health")
    canvas.drawString(MARGIN, PAGE_H - 198, "Assessment Report")
    canvas.restoreState()


def render_road_health_pdf(detail: dict[str, Any]) -> bytes:
    summary = detail.get("summary") or {}
    segments: list[dict[str, Any]] = detail.get("segments") or []
    defects: list[dict[str, Any]] = detail.get("defects") or []
    scope = detail.get("scope") or {}
    period = detail.get("period") or {}
    trend = detail.get("trend") or {}
    org = detail.get("organization") or {}
    sev = {k: int((summary.get("severity_counts") or {}).get(k, 0)) for k in SEVERITIES}
    dist = {k: int((summary.get("distribution") or {}).get(k, 0)) for k in ("GOOD", "FAIR", "POOR", "CRITICAL")}
    avg = summary.get("average_score")
    avg_status = summary.get("average_status")
    scored = int(summary.get("segments_scored") or 0)
    insufficient = int(summary.get("segments_insufficient") or 0)
    open_defects = int(summary.get("open_defects") or 0)
    urgent = sev["CRITICAL"] + sev["HIGH"]
    pending = int(summary.get("pending_review") or 0)
    roads = scope.get("roads") or []

    org_name = org.get("name") or "Organization name not recorded"
    if scope.get("road"):
        scope_text = scope["road"]
    elif len(roads) == 1:
        scope_text = roads[0]
    else:
        scope_text = f"All assessed roads ({len(roads)})" if roads else "No assessed roads"
    period_text = period.get("label") or "Not specified"
    if period.get("start"):
        period_text += f" ({_date(period['start'])} to {_date(period.get('end'))})"
    worst = [s for s in segments if s.get("status") in ("CRITICAL", "POOR")]
    status_color = STATUS_COLOR.get(avg_status or "INSUFFICIENT_DATA", MUTED)
    condition = STATUS_LABEL.get(avg_status or "INSUFFICIENT_DATA", "Not enough data")

    story: list[Flowable] = []

    # ------------------------------------------------------------------ 1. cover
    story.append(Spacer(1, 228))
    story.append(P(_t(scope_text), "h1"))
    story.append(P(_t(org_name), "body"))
    story.append(Spacer(1, 14))
    if avg is not None:
        headline = (
            f"<b>Overall condition: {condition}</b> &nbsp;|&nbsp; average health score <b>{_score(avg)} out of 100</b> "
            f"across {_plural(scored, 'assessed road segment')}. "
            f"{_plural(open_defects, 'open defect')} recorded, of which <b>{urgent}</b> "
            f"{'is' if urgent == 1 else 'are'} critical or high severity."
        )
    else:
        headline = "<b>No road segment has a health score yet.</b> A score is produced once a segment has an inspection or a damage record."
    story.append(_callout(headline, status_color))
    story.append(Spacer(1, 16))
    ident = [
        ["Report ID", detail.get("report_id") or "Not recorded"],
        ["Organization", org_name + (f" ({org.get('code')})" if org.get("code") else "")],
        ["Roads covered", ", ".join(roads) if roads else "None"],
        ["Assessment date", _dt(detail.get("generated_at"))],
        ["Reporting period", period_text],
        ["Scoring rules", f"Rule-based health score, version {detail.get('calculation_version') or 'not recorded'}"],
    ]
    if scope.get("area"):
        ident.insert(3, ["Administrative area", scope["area"]])
    cover = Table([[P(_t(k).upper(), "label"), P(_t(v), "cell")] for k, v in ident], colWidths=[120, CONTENT_W - 120])
    cover.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(cover)
    story.append(Spacer(1, 14))
    notes = ["Health scores show each segment as of its latest calculation. The reporting period is used only for the comparisons in Section 8."]
    if scope.get("requested_road_not_found"):
        notes.append("The requested road was not found in this organization, so the report covers all assessed roads.")
    notes.append("This is an automated, rule-based assessment from platform records. It is not a certified engineering inspection.")
    story.append(P(" ".join(notes), "small"))
    story.append(PageBreak())

    # ------------------------------------------------------------------ 2. executive summary
    story += _section(2, "Executive Summary")
    story.append(_cards([
        ("Overall condition", condition if avg is not None else "n/a", f"Average score {_score(avg)} / 100" if avg is not None else "No scored segments", status_color if avg is not None else None),
        ("Segments assessed", str(scored), f"{insufficient} more without enough data" if insufficient else "All have a score", None),
        ("Open defects", str(open_defects), "Counted in the health score", None),
        ("Critical or high", str(urgent), f"{sev['CRITICAL']} critical, {sev['HIGH']} high", SEVERITY_COLOR["CRITICAL"] if urgent else None),
    ]))
    story.append(Spacer(1, 12))
    if avg is None:
        story.append(P("No segment in this report has a health score, so there is no overall condition to report. Segments get a score after their first inspection or damage record.", "lead"))
    else:
        text = (
            f"{_plural(scored, 'road segment')} across {_plural(len(roads), 'road')} "
            f"{'has' if scored == 1 else 'have'} a health score. The average is <b>{_score(avg)} out of 100</b>, which is in the "
            f"<b>{condition}</b> band of the platform's scale. "
        )
        if worst:
            text += f"<b>{_plural(len(worst), 'segment')}</b> {'is' if len(worst) == 1 else 'are'} rated Poor or Critical and {'needs' if len(worst) == 1 else 'need'} attention first. "
        else:
            text += "No segment is rated Poor or Critical. "
        if open_defects:
            text += f"{_plural(open_defects, 'defect')} {'is' if open_defects == 1 else 'are'} open: {sev['CRITICAL']} critical, {sev['HIGH']} high, {sev['MEDIUM']} medium and {sev['LOW']} low."
        else:
            text += "There are no open defects on record."
        story.append(P(text, "lead"))
    story += H2("Condition of assessed segments")
    story.append(StackedBar([(STATUS_LABEL[k], dist[k], STATUS_COLOR[k]) for k in ("GOOD", "FAIR", "POOR", "CRITICAL")]))
    story += H2("What needs attention")
    points: list[str] = []
    for s in worst[:4]:
        points.append(f"<b>{_t(s['road'])}, {_t(s['segment'])}</b> is rated {STATUS_LABEL[s['status']]} with a score of {_score(s['score'])} and {_plural(s['open_defects'], 'open defect')}.")
    if sev["CRITICAL"]:
        places = sorted({_where(d) for d in defects if d["severity"] == "CRITICAL"})
        points.append(f"<b>{_plural(sev['CRITICAL'], 'critical defect')}</b> on {_t('; '.join(places[:3]))}{' and other locations' if len(places) > 3 else ''}.")
    unscheduled = [d for d in defects if d["severity"] in ("CRITICAL", "HIGH") and not d.get("job")]
    if unscheduled:
        points.append(f"<b>{_plural(len(unscheduled), 'critical or high defect')}</b> {'has' if len(unscheduled) == 1 else 'have'} no open maintenance job.")
    if insufficient:
        points.append(f"{_plural(insufficient, 'segment')} {'has' if insufficient == 1 else 'have'} no inspection or damage data and could not be scored.")
    if pending:
        points.append(f"{_plural(pending, 'AI detection')} {'is' if pending == 1 else 'are'} waiting for human review and {'is' if pending == 1 else 'are'} not counted in any figure in this report.")
    if not points:
        points.append("Nothing in the current records needs urgent attention.")
    for point in points:
        story.append(Paragraph(point, S["bullet"], bulletText="\u2022"))

    # ------------------------------------------------------------------ 3. overall assessment
    story += _section(3, "Overall Road Health Assessment")
    if avg is not None:
        story.append(P(f"The marker shows the average health score of the {_plural(scored, 'assessed segment')} on the platform's 0 to 100 scale.", "body"))
        story.append(Spacer(1, 6))
        story.append(ScoreGauge(avg))
    band_rows = [_th("Condition", "Score", "Meaning")]
    meaning = {
        "GOOD": "Few or only minor open defects. Routine monitoring.",
        "FAIR": "Some open defects are reducing the score. Plan repairs.",
        "POOR": "Several or severe open defects. Prioritize for repair.",
        "CRITICAL": "Heavy deductions from severe or repeated defects. Address first.",
    }
    for status, lo, hi in HEALTH_BANDS:
        band_rows.append([Chip(STATUS_LABEL[status].upper(), STATUS_COLOR[status]), P(f"{lo} to {hi if hi == 100 else hi - 1}", "cell"), P(meaning[status], "cell")])
    story.append(KeepTogether([P("What the condition bands mean", "h2"), _table(band_rows, [90, 70, CONTENT_W - 160])]))
    total_ded = {k: sum(float((s.get("deductions") or {}).get(k.lower(), 0.0)) for s in segments) for k in SEVERITIES}
    recurrence_ded = sum(float((s.get("deductions") or {}).get("recurrence", 0.0)) for s in segments)
    drivers = [_th("Factor", "Open count", "Points deducted (all segments)")]
    for k in SEVERITIES:
        drivers.append([Chip(k, SEVERITY_COLOR[k]), P(str(sev[k]), "cell"), P(f"{total_ded[k]:.1f}", "cell")])
    drivers.append([P("Repeat damage after repair", "cell"), P(str(int(summary.get("recurrences") or 0)), "cell"), P(f"{recurrence_ded:.1f}", "cell")])
    story.append(KeepTogether([P("What is driving the scores", "h2"), _table(drivers, [190, 110, CONTENT_W - 300])]))
    traffic_known = sum(1 for s in segments if s.get("traffic_class"))
    story.append(Spacer(1, 4))
    story.append(P(
        f"Each segment starts at 100 and loses points for every open defect. Traffic volume is recorded for the road of {traffic_known} of {len(segments)} segments; "
        "where it is not recorded, no traffic adjustment is applied. Section 9 gives the full rules.", "small"))
    story += H2("Segment results, worst first")
    if segments:
        rows = [_th("Road", "Segment", "Score", "Condition", "Open C / H / M / L", "Repeats", "Inspected")]
        for s in segments:
            sv = s.get("severity") or {}
            fresh = s.get("freshness_days")
            rows.append([
                P(_t(s["road"]), "cellb"),
                P(_t(s["segment"]), "cell"),
                P(_score(s["score"]), "cellb"),
                Chip("NO SCORE" if s["score"] is None else STATUS_LABEL.get(s["status"], s["status"]).upper(), STATUS_COLOR.get(s["status"], MUTED)),
                P(f"{sv.get('critical', 0)} / {sv.get('high', 0)} / {sv.get('medium', 0)} / {sv.get('low', 0)}", "cell"),
                P(str(s.get("recurrences", 0)), "cell"),
                P("Not recorded" if fresh is None else ("Same day" if fresh == 0 else f"{_plural(int(fresh), 'day')} before"), "cell"),
            ])
        story.append(_table(rows, [118, 112, 38, 70, 76, 42, 55]))
        story.append(Spacer(1, 3))
        story.append(P("Open C / H / M / L: open defects of critical, high, medium and low severity when the score was calculated. Inspected: days between the latest inspection and the score calculation.", "small"))
    else:
        story.append(P("No road segment has been assessed yet.", "body"))

    # ------------------------------------------------------------------ 4. defects
    story += _section(4, "Detailed Defect Analysis")
    if not defects:
        story.append(_callout("No open defects are recorded for the roads in this report."))
    else:
        types = sorted((summary.get("type_counts") or {}).items(), key=lambda kv: -kv[1])
        story.append(P(
            f"{_plural(open_defects, 'open defect')} {'is' if open_defects == 1 else 'are'} on record. The most common type is "
            f"<b>{_t(types[0][0])}</b> ({types[0][1]}). Open means detected or confirmed and not yet repaired; these are the defects the health score counts.", "body"))
        story += H2("Open defects by type and severity")
        matrix = [_th("Defect type", "Critical", "High", "Medium", "Low", "Total")]
        for name, count in types:
            per = {k: sum(1 for d in defects if d["type"] == name and d["severity"] == k) for k in SEVERITIES}
            matrix.append([P(_t(name), "cellb")] + [P(str(per[k]) if per[k] else "-", "cell") for k in SEVERITIES] + [P(str(count), "cellb")])
        matrix.append([P("All types", "cellb")] + [P(str(sev[k]), "cellb") for k in SEVERITIES] + [P(str(open_defects), "cellb")])
        story.append(_table(matrix, [CONTENT_W - 5 * 62] + [62] * 5))
        story += H2("Defect register, most severe first")
        shown = defects[:MAX_DEFECT_ROWS]
        rows = [_th("Ref", "Type", "Severity", "Location", "Detected", "AI conf.", "Status", "Basis")]
        for d in shown:
            conf = d.get("confidence")
            rows.append([
                P(_t(d["ref"]), "cellb"),
                P(_t(d["type"]), "cell"),
                Chip(d["severity"], SEVERITY_COLOR.get(d["severity"], MUTED)),
                P(_t(_where(d)), "cell"),
                P(_date(d.get("detected_at")), "cell"),
                P("-" if conf is None or str(d.get("source")).upper() != "AI" else f"{conf * 100:.0f}%", "cell"),
                P(DAMAGE_STATUS_LABEL.get(d["status"], str(d["status"]).replace("_", " ").title()), "cell"),
                P(_basis(d), "cell"),
            ])
        story.append(_table(rows, [38, 70, 58, 122, 56, 38, 60, 69]))
        story.append(Spacer(1, 3))
        extra = f" Showing the {MAX_DEFECT_ROWS} most severe of {len(defects)}; the full list is in the platform." if len(defects) > len(shown) else ""
        story.append(P("AI conf.: the detection model's confidence in its own detection, not a measure of severity. A dash means no model confidence applies (for example, a defect entered by a person)." + extra, "small"))

    # ------------------------------------------------------------------ 5. location and evidence
    story += _section(5, "Location and Visual Evidence")
    plot = LocationPlot(segments, defects)
    located = len(plot.defects)
    if plot.has_data():
        story.append(P(
            f"The plot shows the stored geometry of {_plural(len(plot.segments), 'segment')} (coloured by condition) and the recorded position of "
            f"{located} of {_plural(open_defects, 'open defect')} (coloured by severity).", "body"))
        story.append(Spacer(1, 6))
        story.append(plot)
        legend = [(STATUS_LABEL[k] + " segment", 0, STATUS_COLOR[k]) for k in ("GOOD", "FAIR", "POOR", "CRITICAL")]
        story.append(Spacer(1, 4))
        story.append(P("Lines: " + ", ".join(f'<font color="{c.hexval().replace("0x", "#")}"><b>{_t(label)}</b></font>' for label, _, c in legend)
                       + ". Dots: " + ", ".join(f'<font color="{SEVERITY_COLOR[k].hexval().replace("0x", "#")}"><b>{k.title()} defect</b></font>' for k in SEVERITIES) + ".", "small"))
    else:
        story.append(P("No segment geometry or defect coordinates are stored for the roads in this report, so no location plot can be drawn.", "body"))
    photos: list[tuple[dict[str, Any], Image]] = []
    cell_w = (CONTENT_W - 12) / 2
    shared: dict[str, list[str]] = {}
    for d in defects:
        ref = d.get("photo")
        if not ref:
            continue
        key = f"{ref.get('bucket')}/{ref.get('path')}"
        if key in shared:
            shared[key].append(d["ref"])
            continue
        if len(photos) >= MAX_PHOTOS:
            continue
        img = _photo(d, cell_w - 12, 150)
        if img is not None:
            shared[key] = [d["ref"]]
            photos.append((d, img))
    story += H2("Inspection photos of the most severe defects")
    if photos:
        cells = []
        for d, img in photos:
            coords = f"{d['lat']:.5f}, {d['lon']:.5f}" if d.get("lat") is not None else "position not recorded"
            also = shared.get(f"{d['photo'].get('bucket')}/{d['photo'].get('path')}", [])[1:]
            also_text = f" Also recorded in this photo: {', '.join(also)}." if also else ""
            caption = P(f"<b>{_t(d['ref'])}</b> {_t(d['type'])}, {d['severity'].title()} severity. {_t(_where(d))}. {coords}. Photo taken {_date((d.get('photo') or {}).get('captured_at'), 'on an unrecorded date')}.{_t(also_text)}", "small")
            cells.append([img, Spacer(1, 3), caption])
        if len(cells) % 2:
            cells.append("")
        grid = Table([cells[i:i + 2] for i in range(0, len(cells), 2)], colWidths=[cell_w + 6, cell_w + 6])
        grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
        story.append(grid)
        story.append(P("Each photo is the original inspection image in which the defect was first recorded. It shows the whole frame, not only the defect.", "small"))
    else:
        story.append(P("No inspection photo could be loaded for the open defects in this report.", "body"))

    # ------------------------------------------------------------------ 6. risk and priority
    story += _section(6, "Risk and Priority Assessment")
    story.append(P("Defects are grouped by the platform's four severity levels. The points shown are what one open defect of that level deducts from its segment's health score.", "body"))
    for k in SEVERITIES:
        group = [d for d in defects if d["severity"] == k]
        per, cap = DEDUCTION_RULES[k]
        if group:
            places: dict[str, int] = {}
            for d in group:
                places[_where(d)] = places.get(_where(d), 0) + 1
            where = "; ".join(f"{name} ({n})" for name, n in sorted(places.items(), key=lambda kv: -kv[1])[:5])
            if len(places) > 5:
                where += f"; and {_plural(len(places) - 5, 'more location')}"
            kinds: dict[str, int] = {}
            for d in group:
                kinds[d["type"]] = kinds.get(d["type"], 0) + 1
            found = ", ".join(f"{n} {name.lower()}" for name, n in sorted(kinds.items(), key=lambda kv: -kv[1]))
            no_job = sum(1 for d in group if not d.get("job"))
            body = (
                f"<b>Found:</b> {_t(found)}.<br/><b>Why it matters:</b> each one deducts {per:g} points from its segment (up to {cap:g}).<br/>"
                f"<b>Where:</b> {_t(where)}.<br/><b>Action:</b> {SEVERITY_GUIDANCE[k]} "
                + (f"All {len(group)} are linked to an open maintenance job." if no_job == 0 and len(group) > 1 else "It is linked to an open maintenance job." if no_job == 0 else f"{no_job} of {len(group)} {'has' if no_job == 1 else 'have'} no open maintenance job yet.")
            )
        else:
            body = "None open."
        block = Table([[Chip(f"{k}  {len(group)}", SEVERITY_COLOR[k], 8), P(body, "cell")]], colWidths=[92, CONTENT_W - 92])
        block.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
        story.append(KeepTogether(block))

    # ------------------------------------------------------------------ 7. recommended actions
    story += _section(7, "Recommended Maintenance Actions")
    story.append(P("Each action comes from a defect's current status and maintenance job in the platform. Due dates are shown only where a job has one; the platform sets no other deadlines. Refs point to the register in Section 4.", "body"))
    grouped: dict[tuple[str, str, str, str], list[str]] = {}
    for d in defects:
        action, due = _action(d, _parse(detail.get("generated_at")))
        grouped.setdefault((d["severity"], _where(d), action, due), []).append(d["ref"])

    def action_rows(levels: tuple[str, ...]) -> list[list[Any]]:
        rows = [_th("Priority", "Location", "Recommended action", "Defects", "Due")]
        for (level, where, action, due), refs in grouped.items():
            if level not in levels:
                continue
            ref_text = ", ".join(refs[:6]) + (f" +{len(refs) - 6}" if len(refs) > 6 else "")
            rows.append([Chip(level, SEVERITY_COLOR[level]), P(_t(where), "cell"), P(_t(action), "cell"), P(_t(ref_text), "cell"), P(_t(due), "cell")])
        return rows

    widths = [58, 112, 181, 86, 74]
    urgent_rows = action_rows(("CRITICAL", "HIGH"))
    story += H2("Urgent: critical and high severity")
    story.append(_table(urgent_rows, widths) if len(urgent_rows) > 1 else P("No critical or high severity defects are open.", "body"))
    routine_rows = action_rows(("MEDIUM", "LOW"))
    story += H2("Routine: medium and low severity")
    story.append(_table(routine_rows, widths) if len(routine_rows) > 1 else P("No medium or low severity defects are open.", "body"))
    other: list[str] = []
    if insufficient:
        names = "; ".join(f"{s['road']}, {s['segment']}" for s in segments if s["score"] is None)
        other.append(f"Inspect the {_plural(insufficient, 'segment')} that could not be scored: {_t(names)}.")
    if pending:
        other.append(f"Review the {_plural(pending, 'AI detection')} waiting for confirmation so that real damage is counted and false detections are rejected.")
    if other:
        story += H2("Other follow-up")
        for line in other:
            story.append(Paragraph(line, S["bullet"], bulletText="\u2022"))

    # ------------------------------------------------------------------ 8. statistics and trends
    story += _section(8, "Supporting Statistics and Trends")
    story.append(P(f"Reporting period: {_t(period_text)}.", "body"))
    stats = [_th("Measure", "Value", "Note")]
    if period.get("start"):
        stats.append([P("Open defects first detected in the period", "cell"), P(str(trend.get("new_defects_in_period") or 0), "cellb"), P(f"Of {open_defects} open defects in total.", "cell")])
        earlier = int(trend.get("segments_with_earlier_score") or 0)
        if earlier and trend.get("average_at_period_start") is not None:
            same = [s for s in segments if s.get("score_at_period_start") is not None and s.get("score") is not None]
            now_avg = sum(s["score"] for s in same) / len(same) if same else None
            change = None if now_avg is None else now_avg - float(trend["average_at_period_start"])
            stats.append([
                P("Average score at the start of the period", "cell"),
                P(_score(trend["average_at_period_start"]), "cellb"),
                P(f"For the {_plural(earlier, 'segment')} that had a score then. Their average is now {_score(now_avg)}" + ("" if change is None else f" ({change:+.1f})") + ".", "cell"),
            ])
        else:
            stats.append([P("Average score at the start of the period", "cell"), P("n/a", "cellb"), P("No segment had a health score before the period began, so no change can be shown.", "cell")])
    else:
        stats.append([P("Change over time", "cell"), P("n/a", "cellb"), P("The report covers all recorded history, so there is no starting point to compare with.", "cell")])
    stats.append([P("Repeat damage after repair", "cell"), P(str(int(summary.get("recurrences") or 0)), "cellb"), P("Active recurrence records on the assessed segments.", "cell")])
    jobs = summary.get("open_jobs") or {}
    job_note = ", ".join(f"{n} {str(k).replace('_', ' ').lower()}" for k, n in sorted(jobs.items())) or "None open."
    stats.append([P("Open maintenance jobs", "cell"), P(str(sum(jobs.values())), "cellb"), P(_t(job_note), "cell")])
    stats.append([P("AI detections awaiting review", "cell"), P(str(pending), "cellb"), P("Not counted as defects until a reviewer confirms them.", "cell")])
    story.append(_table(stats, [190, 60, CONTENT_W - 250]))
    changed = [s for s in segments if s.get("score_at_period_start") is not None and s.get("score") is not None and abs(s["score"] - s["score_at_period_start"]) >= 0.05]
    if changed:
        story += H2("Segments whose score changed in the period")
        rows = [_th("Road", "Segment", "At start", "Now", "Change")]
        for s in sorted(changed, key=lambda s: s["score"] - s["score_at_period_start"]):
            rows.append([P(_t(s["road"]), "cellb"), P(_t(s["segment"]), "cell"), P(_score(s["score_at_period_start"]), "cell"), P(_score(s["score"]), "cell"), P(f"{s['score'] - s['score_at_period_start']:+.1f}", "cellb")])
        story.append(_table(rows, [190, 120, 67, 67, 67]))
    type_rows = sorted((summary.get("type_counts") or {}).items(), key=lambda kv: -kv[1])
    if type_rows:
        story += H2("Open defects by type")
        story.append(BarList([(name, n) for name, n in type_rows]))

    # ------------------------------------------------------------------ 9. methodology
    story += _section(9, "Methodology, Limitations and Glossary")
    story += H2("How the assessment is made")
    method = [
        "Inspectors photograph the road with the field app. Each inspection stores the phone's GPS position.",
        "A trained detection model (YOLO11s, trained on the RDD2022 India road damage dataset) proposes defects in the photos. A person reviews the proposals; rejected ones are not counted.",
        "Severity (critical, high, medium, low) is assigned by fixed rules from the defect's type and its size in the photo. It is not a model prediction.",
        f"The health score is rule-based (version {_t(detail.get('calculation_version'))}). Each segment starts at 100. Every open defect deducts points: "
        + ", ".join(f"{k.lower()} {DEDUCTION_RULES[k][0]:g} (at most {DEDUCTION_RULES[k][1]:g})" for k in SEVERITIES)
        + f". Each repeat of damage after a repair deducts {RECURRENCE_RULE[0]:g} (at most {RECURRENCE_RULE[1]:g}).",
        "Where a road has a documented traffic volume class, defect deductions are multiplied by 1.0 (low), 1.1 (medium), 1.2 (high) or 1.3 (very high). Unknown traffic applies no adjustment.",
        "The score is then placed in a band: 80 and above Good, 60 to 79 Fair, 40 to 59 Poor, below 40 Critical. The overall figure is the plain average of the segment scores, placed on the same bands.",
    ]
    for line in method:
        story.append(Paragraph(line, S["bullet"], bulletText="\u2022"))
    story += H2("Limitations")
    limits = [
        "This is an automated assessment from platform records, not a certified engineering inspection. It makes no statement about structural safety or accident risk.",
        "Only defects that were photographed and recorded are counted. Damage on parts of a road that were not inspected is not reflected.",
        "Positions come from phone GPS and carry the accuracy the phone reported.",
        "The location plot draws stored coordinates only; it has no base map.",
        "Defect areas are estimated from photos where available and are not surveyed measurements.",
        "Text that the PDF fonts cannot show (for example Devanagari) appears as a question mark.",
    ]
    for line in limits:
        story.append(Paragraph(line, S["bullet"], bulletText="\u2022"))
    story += H2("Glossary")
    glossary = [
        ("Segment", "A defined stretch of a road. Health is calculated per segment."),
        ("Open defect", "A damage record that is detected, confirmed, scheduled for repair or being repaired."),
        ("Health score", "0 to 100. Higher is better. 100 means no open defects and no repeat damage."),
        ("AI confidence", "How sure the detection model was that it found a defect, from 0 to 100%."),
        ("Reviewed", "A person has confirmed the AI detection."),
        ("Repeat damage", "New damage found close to a location that was repaired before."),
        ("Not enough data", "The segment has no inspection and no damage record, so it has no score."),
    ]
    story.append(_table([[P(_t(a), "cellb"), P(_t(b), "cell")] for a, b in glossary], [120, CONTENT_W - 120], header=False))

    # ------------------------------------------------------------------ 10. final summary
    closing: list[Flowable] = _section(10, "Final Summary")
    if avg is None:
        final = "No road segment could be scored, so the first step is to inspect the roads in scope."
    else:
        final = f"<b>Condition:</b> {condition}, with an average score of {_score(avg)} out of 100 across {_plural(scored, 'segment')} on {_plural(len(roads), 'road')}.<br/>"
        final += f"<b>Main findings:</b> {_plural(open_defects, 'open defect')}, {sev['CRITICAL']} critical and {sev['HIGH']} high; {_plural(len(worst), 'segment')} rated Poor or Critical.<br/>"
        if worst:
            top = worst[0]
            final += f"<b>Start with:</b> {_t(top['road'])}, {_t(top['segment'])} (score {_score(top['score'])})"
            final += f", and the {_plural(len(unscheduled), 'critical or high defect')} without a maintenance job.<br/>" if unscheduled else ".<br/>"
        elif urgent:
            final += f"<b>Start with:</b> the {_plural(urgent, 'critical or high defect')} listed in Section 7.<br/>"
        else:
            final += "<b>Next step:</b> continue routine inspection and maintenance.<br/>"
        caveats = []
        if insufficient:
            caveats.append(f"{_plural(insufficient, 'segment')} could not be scored")
        if pending:
            caveats.append(f"{_plural(pending, 'AI detection')} still awaiting review")
        final += "<b>Keep in mind:</b> " + ("; ".join(caveats) + ". " if caveats else "") + "This is a rule-based assessment, not a certified engineering inspection."
    closing.append(_callout(final, status_color))
    closing.append(Spacer(1, 10))
    closing.append(Paragraph("End of report", ParagraphStyle("end", parent=S["small"], alignment=TA_CENTER)))
    story.append(KeepTogether(closing))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=48, bottomMargin=48,
        title="Road Health Assessment Report", author="Road Intelligence", subject=scope_text,
    )
    meta = {"report_id": str(detail.get("report_id") or ""), "generated": _dt(detail.get("generated_at")), "scope": scope_text[:70]}
    doc.build(story, onFirstPage=_cover_band, canvasmaker=lambda *a, **k: _NumberedCanvas(*a, meta=meta, **k))
    return buf.getvalue()
