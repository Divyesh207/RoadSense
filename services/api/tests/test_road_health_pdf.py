"""The designed Road Health PDF must render for full, partial and empty data."""

import base64
import re
import zlib

from app.services.report_render import render_pdf
from app.services.road_health_pdf import render_road_health_pdf


def _text(pdf: bytes) -> bytes:
    """The text shown on the pages, as one space-separated run."""
    out = b""
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.DOTALL):
        raw = match.group(1).strip()
        try:
            data = zlib.decompress(raw)
        except zlib.error:
            try:  # ReportLab ASCII85-encodes its compressed streams
                data = zlib.decompress(base64.a85decode(raw, adobe=True))
            except (ValueError, zlib.error):  # not a text stream (an image, for example)
                continue
        out += b" ".join(re.findall(rb"\((.*?)\) Tj", data)) + b" "
    return out.replace(b"\\(", b"(").replace(b"\\)", b")")


def _segment(**over):
    base = {
        "segment_id": "s1", "road": "Main Road", "road_code": None, "area": None, "segment": "Segment 1",
        "segment_number": 1, "length_m": 120.0, "score": 52.0, "status": "POOR", "calculated_at": "2026-10-01T10:00:00+00:00",
        "version": "health-v1.1.0", "severity": {"critical": 1, "high": 1, "medium": 0, "low": 0},
        "deductions": {"critical": 25.0, "high": 15.0, "recurrence": 0.0}, "recurrences": 0, "freshness_days": 3,
        "traffic_class": None, "open_defects": 2, "score_at_period_start": 80.0, "status_at_period_start": "GOOD",
        "line": [[73.76, 18.64], [73.77, 18.65]],
    }
    return {**base, **over}


def _defect(i, **over):
    base = {
        "ref": f"D{i:03d}", "type": "Pothole", "severity": "CRITICAL", "status": "CONFIRMED", "source": "AI",
        "reviewed": True, "road": "Main Road", "segment": "Segment 1", "segment_id": "s1", "lat": 18.645, "lon": 73.765,
        "detected_at": "2026-09-30T08:00:00+00:00", "confidence": 0.71, "area_m2": None, "observations": 1,
        "job": None, "photo": None,
    }
    return {**base, **over}


def _detail(segments, defects):
    return {
        "report_id": "11111111-2222-3333-4444-555555555555",
        "generated_at": "2026-10-06T06:28:19+00:00",
        "organization": {"name": "Test Authority", "code": "TEST"},
        "scope": {"road": None, "roads": sorted({s["road"] for s in segments}), "requested_road_not_found": False},
        "period": {"label": "Last 30 days", "start": "2026-09-06T06:28:19+00:00", "end": "2026-10-06T06:28:19+00:00"},
        "summary": {
            "average_score": 52.0 if segments else None, "average_status": "POOR" if segments else None,
            "distribution": {"GOOD": 0, "FAIR": 0, "POOR": len(segments), "CRITICAL": 0},
            "segments_scored": len(segments), "segments_insufficient": 0, "open_defects": len(defects),
            "severity_counts": {"CRITICAL": len(defects), "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "type_counts": {"Pothole": len(defects)} if defects else {}, "pending_review": 1, "recurrences": 0, "open_jobs": {},
        },
        "trend": {"new_defects_in_period": len(defects), "segments_with_earlier_score": 1, "average_at_period_start": 80.0},
        "segments": segments, "defects": defects, "calculation_version": "health-v1.1.0",
    }


def test_renders_with_data_and_states_the_real_figures():
    pdf = render_pdf({"report_type": "ROAD_HEALTH", "road_health_detail": _detail([_segment()], [_defect(1), _defect(2, severity="HIGH")])})
    assert pdf.startswith(b"%PDF-1.4")
    text = _text(pdf)
    for expected in (b"Executive Summary", b"Recommended Maintenance Actions", b"52.0", b"D001", b"Test Authority"):
        assert expected in text


def test_renders_with_no_segments_and_no_defects():
    pdf = render_road_health_pdf(_detail([], []))
    assert pdf.startswith(b"%PDF-1.4")
    text = _text(pdf)
    assert b"No open defects are recorded" in text
    assert b"No road segment has been assessed yet" in text


def test_renders_with_missing_fields_long_text_and_many_defects():
    long_name = "Old Highway Service Road (North Carriageway) between the Railway Station & the <Ring> Junction " * 2 + "आकु"
    defects = [
        _defect(i, road=long_name if i % 3 == 0 else None, lat=None, lon=None, detected_at="not-a-date" if i % 2 else None, confidence=None)
        for i in range(1, 321)
    ]
    segments = [_segment(road=long_name), _segment(segment_id="s2", score=None, status="INSUFFICIENT_DATA", line=[], freshness_days=None, score_at_period_start=None)]
    pdf = render_road_health_pdf(_detail(segments, defects))
    assert pdf.startswith(b"%PDF-1.4")
    assert len(re.findall(rb"/Type /Page\b", pdf)) > 10
    assert b"most severe of 320" in _text(pdf)


def test_renders_from_an_empty_dict():
    assert render_road_health_pdf({"report_id": "x"}).startswith(b"%PDF-1.4")


def test_other_report_types_keep_the_plain_writer():
    pdf = render_pdf({"report_type": "DAMAGE_SUMMARY", "sections": {"damage_trends": {"total_damages": 3}}})
    assert pdf.startswith(b"%PDF-1.4") and b"total_damages: 3" in pdf
