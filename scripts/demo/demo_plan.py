"""
The faculty demo dataset, as data.

Everything named here is DEMO / SYNTHETIC:
  - the organization, users and contractors are demo accounts;
  - the road and segment geometry is drawn for the demo around Akurdi / Pune and does not
    trace surveyed roads;
  - the photographs are RDD2022 India test images (third-party, CC BY-SA 4.0). They were
    NOT taken at these coordinates;
  - review decisions, severities chosen by the demo reviewer and maintenance notes are
    scripted demo decisions.

What is NOT scripted: AI detections, confidences, rule-based severity, road health,
deterioration estimates, priorities, repair-verification results and recurrence matches.
Those come from the running platform when the seed script drives its API.
"""

from __future__ import annotations

ORG_CODE = "FACULTY-DEMO"
ORG_NAME = "DEMO - RoadSense Faculty Demo Authority (SYNTHETIC)"
EMAIL_DOMAIN = "faculty-demo.roadsense.example"
MARK = "FDEMO"          # stable marker: road codes, inspection notes and job descriptions carry it
DEMO_NOTE = "DEMO / SYNTHETIC record."
PHOTO_NOTE = "Photo: RDD2022 India test image (third-party, CC BY-SA 4.0); not taken at this location."

USERS = {
    "supervisor": ("supervisor", "DEMO - Program Supervisor"),
    "inspector": ("inspector", "DEMO - Field Inspector"),
    "reviewer": ("reviewer", "DEMO - Damage Reviewer"),
    "engineer": ("engineer", "DEMO - Maintenance Engineer"),
}

CONTRACTORS = {
    "pune_roadworks": ("FDEMO-C-PRT", "DEMO - Pune Roadworks Team"),
    "akurdi_unit": ("FDEMO-C-AMU", "DEMO - Akurdi Maintenance Unit"),
    "contractor_a": ("FDEMO-C-RRA", "DEMO - Road Repair Contractor A"),
}

TRAFFIC_SOURCE = "DEMO / SYNTHETIC value for demonstration - not a traffic survey"

# Each road: polyline of (lat, lon) break points; consecutive pairs are its segments.
ROADS = {
    "R1": dict(code="FDEMO-R1", name="DEMO - Akurdi Main Road", road_type="ARTERIAL", traffic="HIGH", aadt=18000,
               area="DEMO - Akurdi (synthetic)",
               points=[(18.6490, 73.7600), (18.6490, 73.7640), (18.6490, 73.7680), (18.6490, 73.7720)]),
    "R2": dict(code="FDEMO-R2", name="DEMO - Akurdi Station Road", road_type="URBAN", traffic="MEDIUM", aadt=7500,
               area="DEMO - Akurdi (synthetic)",
               points=[(18.6440, 73.7660), (18.6465, 73.7660), (18.6488, 73.7660)]),
    "R3": dict(code="FDEMO-R3", name="DEMO - Akurdi Internal Road", road_type="LOCAL", traffic="LOW", aadt=900,
               area="DEMO - Akurdi (synthetic)",
               points=[(18.6455, 73.7690), (18.6455, 73.7715), (18.6455, 73.7740)]),
    "R4": dict(code="FDEMO-R4", name="DEMO - Akurdi College Road", road_type="URBAN", traffic=None, aadt=None,
               area="DEMO - Akurdi (synthetic)",
               points=[(18.6510, 73.7630), (18.6550, 73.7670), (18.6585, 73.7690)]),
    "R5": dict(code="FDEMO-R5", name="DEMO - Pune Demo Connector", road_type="HIGHWAY", traffic="VERY_HIGH", aadt=42000,
               area="DEMO - Pune (synthetic)",
               points=[(18.6420, 73.7740), (18.6360, 73.7820), (18.6300, 73.7900)]),
}

# Photos with no detection by the deployed model (clean-road inspections).
CLEAN = ["India_000004.jpg", "India_000752.jpg", "India_001718.jpg", "India_002758.jpg", "India_003786.jpg"]

# One entry per damage site. Fields:
#   road, seg (1-based), frac (position along the segment 0..1), photo, days_ago (demo capture date)
#   promote: damage types to promote from the model's detections (highest confidence of each type)
#   review:  {type: (decision, severity or None to keep the rule-based severity, note)}; types not
#            listed stay PENDING_REVIEW
#   job:     dict(title, target, user=..., contractor=..., cancel_reason=...)
#   repair:  dict(after=repaired|partial|unchanged|mismatch, mismatch_photo, before_evidence,
#                 human=(decision, final_result, note) or None, then=<job status to move to afterwards>)
#   recurrence: dict(photo, type, severity, review=(status, note) or None, job_title)  -> a later inspection
#               at the site; job_title opens a new job for the returned damage
#   regroup: True -> a second inspection ~2 m away with the same photo (GPS grouping demo)
#   followup_clean: photo -> a later clean inspection at the site
SITES = [
    dict(key="A", road="R1", seg=1, frac=0.35, photo="India_006296.jpg", days_ago=112, promote=["POTHOLE"],
         review={"POTHOLE": ("CONFIRMED", "HIGH", "Deep pothole in the wheel path.")},
         job=dict(title="DEMO - Pothole repair, Akurdi Main Road seg 1", target="COMPLETED", contractor="pune_roadworks"),
         repair=dict(after="repaired", before_evidence=True,
                     human=("CONFIRMED", None, "Patch is complete and level with the surface.")),
         recurrence=dict(photo="India_005268.jpg", type="POTHOLE", severity="CRITICAL",
                         review=("CONFIRMED", "Same location as the repaired pothole; repair has failed."),
                         job_title="DEMO - Re-repair after recurrence, Akurdi Main Road seg 1")),
    dict(key="B", road="R1", seg=2, frac=0.30, photo="India_000082.jpg", days_ago=98, promote=["POTHOLE"],
         review={"POTHOLE": ("CONFIRMED", "HIGH", "Large pothole across the lane.")},
         job=dict(title="DEMO - Pothole repair, Akurdi Main Road seg 2", target="COMPLETED", contractor="contractor_a"),
         repair=dict(after="partial", human=("CONFIRMED", None, "Part of the cavity was left open."))),
    dict(key="C", road="R2", seg=1, frac=0.40, photo="India_005667.jpg", days_ago=91, promote=["POTHOLE"],
         review={"POTHOLE": ("CONFIRMED", None, "Confirmed as detected.")},
         job=dict(title="DEMO - Pothole repair, Akurdi Station Road seg 1", target="COMPLETED", contractor="contractor_a"),
         repair=dict(after="unchanged", human=("CONFIRMED", None, "No repair is visible in the evidence."),
                     then="IN_PROGRESS")),
    dict(key="D", road="R2", seg=2, frac=0.55, photo="India_000056.jpg", days_ago=84, promote=["CRACK"],
         review={"CRACK": ("CONFIRMED", "MEDIUM", "Longitudinal crack.")},
         job=dict(title="DEMO - Crack sealing, Akurdi Station Road seg 2", target="COMPLETED", user="engineer"),
         repair=dict(after="repaired", human=None, then="VERIFICATION_PENDING")),
    dict(key="E", road="R3", seg=1, frac=0.30, photo="India_006684.jpg", days_ago=77, promote=["CRACK"],
         review={"CRACK": ("CONFIRMED", None, "Confirmed as detected.")},
         job=dict(title="DEMO - Crack sealing, Akurdi Internal Road seg 1", target="COMPLETED", contractor="akurdi_unit"),
         repair=dict(after="unchanged", human=("UNRESOLVED", None, "Evidence does not show a repair; new photos requested."))),
    dict(key="F", road="R3", seg=2, frac=0.60, photo="India_003735.jpg", days_ago=70, promote=["CRACK"],
         review={"CRACK": ("CONFIRMED", "MEDIUM", "Crack along the lane edge.")},
         job=dict(title="DEMO - Crack sealing, Akurdi Internal Road seg 2", target="COMPLETED", contractor="akurdi_unit"),
         repair=dict(after="mismatch", mismatch_photo="India_001940.jpg", human=None, then="VERIFICATION_PENDING")),
    dict(key="G", road="R5", seg=1, frac=0.45, photo="India_005719.jpg", days_ago=105, promote=["POTHOLE"],
         review={"POTHOLE": ("CONFIRMED", "HIGH", "Wide pothole on a high-traffic road.")},
         job=dict(title="DEMO - Pothole repair, Pune Demo Connector seg 1", target="COMPLETED", contractor="pune_roadworks"),
         repair=dict(after="repaired", human=("CONFIRMED", None, "Repair accepted.")),
         recurrence=dict(photo="India_003819.jpg", type="POTHOLE", severity=None, review=None)),
    dict(key="H", road="R4", seg=1, frac=0.35, photo="India_001624.jpg", days_ago=63, promote=["CRACK"],
         review={"CRACK": ("CONFIRMED", "MEDIUM", "Transverse crack.")},
         job=dict(title="DEMO - Crack sealing, Akurdi College Road seg 1", target="COMPLETED", contractor="contractor_a"),
         repair=dict(after="repaired",
                     human=("REJECTED", "SUBSTANDARD",
                            "Reviewer disagrees with the automated result: sealant does not cover the full crack length."))),
    dict(key="I", road="R4", seg=2, frac=0.50, photo="India_002306.jpg", days_ago=119, promote=["CRACK"],
         review={"CRACK": ("CONFIRMED", "LOW", "Hairline crack, low priority.")},
         job=dict(title="DEMO - Crack sealing, Akurdi College Road seg 2", target="COMPLETED", user="engineer"),
         repair=dict(after="repaired", human=("CONFIRMED", None, "Repair accepted.")),
         followup_clean="India_003786.jpg"),
    dict(key="J", road="R1", seg=3, frac=0.50, photo="India_003590.jpg", days_ago=21, promote=["POTHOLE", "CRACK"],
         review={"POTHOLE": ("CONFIRMED", "CRITICAL", "Multiple potholes; hazard to two-wheelers."),
                 "CRACK": ("CONFIRMED", "HIGH", "Cracking around the potholes.")},
         job=dict(title="DEMO - Urgent pothole repair, Akurdi Main Road seg 3", target="IN_PROGRESS", contractor="pune_roadworks"),
         regroup=True),
    dict(key="K", road="R5", seg=2, frac=0.40, photo="India_003026.jpg", days_ago=14, promote=["POTHOLE", "CRACK"],
         review={"POTHOLE": ("CONFIRMED", "HIGH", "Potholes forming along a crack."),
                 "CRACK": ("CONFIRMED", None, "Confirmed as detected.")},
         job=dict(title="DEMO - Pothole and crack repair, Pune Demo Connector seg 2", target="ASSIGNED", contractor="akurdi_unit")),
    dict(key="L", road="R5", seg=1, frac=0.80, photo="India_002814.jpg", days_ago=9, promote=["POTHOLE"],
         review={"POTHOLE": ("CONFIRMED", "MEDIUM", "Shallow pothole.")},
         job=dict(title="DEMO - Pothole repair, Pune Demo Connector seg 1 (east)", target="OPEN")),
    dict(key="M", road="R2", seg=1, frac=0.80, photo="India_004955.jpg", days_ago=35, promote=["POTHOLE"],
         review={"POTHOLE": ("CONFIRMED", "HIGH", "Cluster of potholes.")},
         job=dict(title="DEMO - Pothole cluster repair, Akurdi Station Road seg 1", target="COMPLETED", user="engineer")),
    dict(key="N", road="R3", seg=1, frac=0.75, photo="India_001154.jpg", days_ago=49, promote=["CRACK"],
         review={"CRACK": ("CONFIRMED", "LOW", "Minor crack.")},
         job=dict(title="DEMO - Crack sealing, Akurdi Internal Road seg 1 (east)", target="CANCELLED",
                  cancel_reason="DEMO: cancelled, covered by a planned resurfacing of this segment.")),
    dict(key="O", road="R4", seg=1, frac=0.75, photo="India_005443.jpg", days_ago=5, promote=["CRACK"], review={}),
    dict(key="P", road="R1", seg=2, frac=0.75, photo="India_006208.jpg", days_ago=3, promote=["POTHOLE", "CRACK"], review={}),
    dict(key="Q", road="R2", seg=2, frac=0.20, photo="India_002081.jpg", days_ago=28, promote=["CRACK"],
         review={"CRACK": ("REJECTED", None, "DEMO reviewer decision: marking, not a crack (false positive).")}),
    dict(key="R", road="R5", seg=2, frac=0.80, photo="India_000328.jpg", days_ago=42, promote=["CRACK"],
         review={"CRACK": ("REJECTED", None, "DEMO reviewer decision: shadow edge, not damage (false positive).")}),
    dict(key="S", road="R3", seg=2, frac=0.25, photo="India_004382.jpg", days_ago=56, promote=["CRACK"],
         review={"CRACK": ("CONFIRMED", "MEDIUM", "Crack network; not yet scheduled.")}),
]

# Clean-road inspections (the deployed model reports no damage in these photos).
CLEAN_INSPECTIONS = [
    dict(key="Z1", road="R1", seg=1, frac=0.80, photo="India_000004.jpg", days_ago=126),
    dict(key="Z2", road="R3", seg=2, frac=0.85, photo="India_000752.jpg", days_ago=60),
    dict(key="Z3", road="R4", seg=2, frac=0.15, photo="India_001718.jpg", days_ago=30),
    dict(key="Z4", road="R5", seg=2, frac=0.10, photo="India_002758.jpg", days_ago=7),
]

# A damage record entered by a person on a clean inspection (source MANUAL, no AI involved).
MANUAL_DAMAGE = dict(inspection="Z3", type="POTHOLE", severity="LOW",
                     notes="DEMO / SYNTHETIC human-reported defect: small depression noted by the inspector; not AI-detected.")

REPORTS = [
    ("EXECUTIVE_ROAD_CONDITION", "PDF"),
    ("ROAD_HEALTH", "CSV"),
    ("DAMAGE_SUMMARY", "CSV"),
    ("MAINTENANCE_LOG", "CSV"),
    ("INSPECTION_SUMMARY", "JSON"),
]


def all_photos() -> list[str]:
    names = set(CLEAN)
    for s in SITES:
        names.add(s["photo"])
        rep = s.get("repair") or {}
        if rep.get("mismatch_photo"):
            names.add(rep["mismatch_photo"])
        if s.get("recurrence"):
            names.add(s["recurrence"]["photo"])
        if s.get("followup_clean"):
            names.add(s["followup_clean"])
    for c in CLEAN_INSPECTIONS:
        names.add(c["photo"])
    return sorted(names)


def point_on(road_key: str, seg: int, frac: float) -> tuple[float, float]:
    pts = ROADS[road_key]["points"]
    (la0, lo0), (la1, lo1) = pts[seg - 1], pts[seg]
    return round(la0 + (la1 - la0) * frac, 7), round(lo0 + (lo1 - lo0) * frac, 7)
