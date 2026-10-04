"""
Seed the RoadSense FACULTY DEMO dataset (DEMO / SYNTHETIC) through the running platform.

It creates a dedicated demo organization and drives the real API and AI worker through the
whole lifecycle: roads -> segments -> inspections -> AI detection -> human review -> road
health -> rule-based estimates -> maintenance -> repair evidence -> repair verification ->
human review -> recurrence -> reports. See docs/FACULTY_DEMO_GUIDE.md.

Nothing is written to the database directly except the demo organization, its users and the
demo contractor organizations (the platform has no API for those; the project's own
`app.bootstrap` is used). Detections, confidences, severity, health, estimates, priorities,
verification results and recurrence matches are produced by the platform, never by this script.

Safe to run again: every step first looks for what already exists and skips it.

    python scripts/seed_faculty_demo.py
    python scripts/seed_faculty_demo.py --api http://localhost:8000/api/v1

Requires the Docker stack to be running (docker compose up -d) and Python with httpx,
opencv-python and numpy (the repository's .venv has them).
"""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

REPO = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO / "scripts" / "demo"
sys.path.insert(0, str(DEMO_DIR))

import demo_plan as plan
import repair_derivatives as derive

PHOTOS = DEMO_DIR / "photos" / "pool"
CREDS_FILE = DEMO_DIR / "faculty_demo.local.env"
SUMMARY_FILE = DEMO_DIR / "last_seed_summary.json"

# Runs inside the api container: demo organization, demo users, demo contractor organizations.
TENANT_SCRIPT = r'''
import asyncio, json, os, uuid
from sqlalchemy import select
from app.bootstrap import bootstrap_admin
from app.core.database import AsyncSessionLocal, async_engine
from app.models.identity import Organization

cfg = json.loads(os.environ["FDEMO_CONFIG"])
password = os.environ["FDEMO_PASSWORD"]

async def main():
    out = {"users": {}, "contractors": {}}
    try:
        async with AsyncSessionLocal() as db:
            for key, (email, name) in cfg["users"].items():
                r = await bootstrap_admin(db, cfg["org_code"], cfg["org_name"], "MUNICIPAL", email, password, name)
                out["organization_id"] = str(r.organization_id)
                out["users"][key] = {"id": str(r.user_id), "created": r.created_user}
            for key, (code, name) in cfg["contractors"].items():
                org = (await db.execute(select(Organization).where(Organization.code == code))).scalar_one_or_none()
                if org is None:
                    org = Organization(id=uuid.uuid4(), name=name, code=code, organization_type="CONTRACTOR", is_active=True)
                    db.add(org)
                    await db.commit()
                out["contractors"][key] = str(org.id)
    finally:
        await async_engine.dispose()
    print("FDEMO_RESULT " + json.dumps(out))

asyncio.run(main())
'''


def log(msg: str) -> None:
    print(msg, flush=True)


class SeedError(RuntimeError):
    pass


class Api:
    """API client for one demo user."""

    def __init__(self, base: str, email: str, password: str):
        self.base, self.email, self.password = base.rstrip("/"), email, password
        self.http = httpx.Client(timeout=120)
        self.headers: dict[str, str] = {}
        self.user_id = ""
        self.login()

    def login(self) -> None:
        r = self.http.post(f"{self.base}/auth/login", json={"email": self.email, "password": self.password})
        if r.status_code != 200:
            raise SeedError(f"login failed for {self.email}: HTTP {r.status_code}")
        token = r.json()["data"]["access_token"]
        me = self.http.get(f"{self.base}/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["data"]
        org = me["organizations"][0]  # demo users belong to the demo organization only
        self.user_id = me["id"]
        self.headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org["organization_id"]}

    def send(self, method: str, url: str, **kw) -> httpx.Response:
        """One request; waits and retries when the API's rate limit (HTTP 429) is hit."""
        for _ in range(12):
            r = self.http.request(method, url, **kw)
            if r.status_code != 429:
                return r
            time.sleep(10)
        return r

    def call(self, method: str, path: str, ok: tuple[int, ...] = (200, 201, 202), **kw):
        r = self.send(method, f"{self.base}{path}", headers=self.headers, **kw)
        if r.status_code == 401:
            self.login()
            r = self.send(method, f"{self.base}{path}", headers=self.headers, **kw)
        if r.status_code not in ok:
            raise SeedError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:400]}")
        return r.json().get("data") if r.content else None

    def get(self, path: str, **params):
        return self.call("GET", path, params={k: v for k, v in params.items() if v is not None})

    def post(self, path: str, body: dict | None = None, ok: tuple[int, ...] = (200, 201, 202)):
        return self.call("POST", path, ok=ok, json=body if body is not None else {})

    def pages(self, path: str, **params) -> list[dict]:
        items, page = [], 1
        while True:
            r = self.send("GET", f"{self.base}{path}", headers=self.headers, params={**params, "page": page, "page_size": 100})
            if r.status_code != 200:
                raise SeedError(f"GET {path} -> HTTP {r.status_code}: {r.text[:300]}")
            data = r.json().get("data") or []
            items += data
            if len(data) < 100:
                return items
            page += 1

    def upload(self, signed_url: str, data: bytes, headers: dict[str, str]) -> None:
        # The server builds signed URLs from PUBLIC_API_BASE_URL, which may name a host this
        # machine cannot reach. Local-storage URLs are the API itself; the signature does not
        # cover the host, so they are sent to the API address this script already uses.
        if "/storage/local/" in signed_url:
            api, parts = urlsplit(self.base), urlsplit(signed_url)
            signed_url = f"{api.scheme}://{api.netloc}{parts.path}?{parts.query}"
        r = self.send("PUT", signed_url, content=data, headers=headers)
        if r.status_code not in (200, 201, 204):
            raise SeedError(f"upload failed: HTTP {r.status_code}: {r.text[:200]}")


def ensure_tenant() -> tuple[str, dict]:
    """Create (or reuse) the demo organization, users and contractors. Returns (password, ids)."""
    if CREDS_FILE.exists():
        password = dict(
            line.split("=", 1) for line in CREDS_FILE.read_text(encoding="utf-8").splitlines() if "=" in line
        )["FACULTY_DEMO_PASSWORD"].strip()
    else:
        password = secrets.token_urlsafe(18)
    config = {
        "org_code": plan.ORG_CODE,
        "org_name": plan.ORG_NAME,
        "users": {k: (f"{local}@{plan.EMAIL_DOMAIN}", name) for k, (local, name) in plan.USERS.items()},
        "contractors": plan.CONTRACTORS,
    }
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "-e", f"FDEMO_PASSWORD={password}", "-e", f"FDEMO_CONFIG={json.dumps(config)}",
         "api", "python", "-"],
        input=TENANT_SCRIPT, capture_output=True, text=True, cwd=REPO, check=False,
    )
    line = next((x for x in proc.stdout.splitlines() if x.startswith("FDEMO_RESULT ")), None)
    if proc.returncode != 0 or line is None:
        raise SeedError("could not create the demo organization:\n" + (proc.stderr or proc.stdout)[-800:])
    ids = json.loads(line.split(" ", 1)[1])
    if not CREDS_FILE.exists():
        if not all(u["created"] for u in ids["users"].values()):
            raise SeedError(
                f"The demo users already exist but {CREDS_FILE.name} is missing, so their password is unknown. "
                "Run scripts/cleanup_faculty_demo.py and seed again."
            )
        CREDS_FILE.write_text(
            "# RoadSense faculty demo login (DEMO accounts, local only, git-ignored)\n"
            + "".join(f"FACULTY_DEMO_{k.upper()}_EMAIL={local}@{plan.EMAIL_DOMAIN}\n" for k, (local, _) in plan.USERS.items())
            + f"FACULTY_DEMO_PASSWORD={password}\n",
            encoding="utf-8",
        )
    return password, ids


class Seeder:
    def __init__(self, api_base: str):
        self.api_base = api_base
        password, self.ids = ensure_tenant()
        log(f"demo organization {plan.ORG_CODE}: {self.ids['organization_id']}")
        self.as_ = {k: Api(api_base, f"{local}@{plan.EMAIL_DOMAIN}", password) for k, (local, _) in plan.USERS.items()}
        self.sup, self.insp, self.rev, self.eng = (self.as_[k] for k in ("supervisor", "inspector", "reviewer", "engineer"))
        self.roads: dict[str, dict] = {}
        self.segments: dict[tuple[str, int], dict] = {}
        self.inspections: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.damage_types: dict[str, str] = {}
        self.results: dict[str, dict] = {}
        self.warnings: list[str] = []
        self.now = datetime.now(timezone.utc)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        log(f"  WARNING: {msg}")

    # ------------------------------------------------------------------ roads
    def seed_roads(self) -> None:
        log("roads and segments")
        existing = {r.get("road_code"): r for r in self.sup.pages("/roads")}
        for key, spec in plan.ROADS.items():
            road = existing.get(spec["code"])
            line = [[lon, lat] for lat, lon in spec["points"]]
            if road is None:
                body = {
                    "name": spec["name"], "road_code": spec["code"], "road_type": spec["road_type"],
                    "administrative_area": spec["area"],
                    "description": f"{plan.DEMO_NOTE} Geometry drawn for the demo; it does not trace a surveyed road.",
                    "geometry": {"type": "LineString", "coordinates": line},
                }
                if spec["traffic"]:
                    body.update(traffic_volume_class=spec["traffic"], traffic_aadt=spec["aadt"],
                                traffic_data_source=plan.TRAFFIC_SOURCE)
                road = self.sup.post("/roads", body)
                log(f"  created {spec['name']}")
            self.roads[key] = road
            segs = {s["segment_number"]: s for s in self.sup.get(f"/roads/{road['id']}/segments")}
            for n in range(1, len(spec["points"])):
                seg = segs.get(n)
                if seg is None:
                    (la0, lo0), (la1, lo1) = spec["points"][n - 1], spec["points"][n]
                    seg = self.sup.post(f"/roads/{road['id']}/segments", {
                        "segment_number": n, "name": f"DEMO segment {n}",
                        "geometry": {"type": "LineString", "coordinates": [[lo0, la0], [lo1, la1]]},
                    })
                self.segments[(key, n)] = seg

    # ------------------------------------------------------------ inspections
    def load_existing(self) -> None:
        for i in self.insp.pages("/inspections"):
            notes = i.get("notes") or ""
            if notes.startswith(f"[{plan.MARK}:"):
                self.inspections[notes[1:notes.index("]")]] = i
        for j in self.eng.pages("/maintenance-jobs"):
            self.jobs[j["title"]] = j
        self.damage_types = {t["code"]: t["id"] for t in self.sup.get("/damage-types")}

    def inspection(self, key: str, road: str, seg: int, lat: float, lon: float, photo: str, days_ago: float) -> tuple[dict, list[dict]]:
        """Create, upload, submit and AI-process one inspection (each step only if not done yet)."""
        marker = f"{plan.MARK}:{key}"       # stable identifier, kept at the start of the notes
        insp = self.inspections.get(marker)
        location = {"latitude": lat, "longitude": lon, "accuracy_m": 5.0}
        if insp is None:
            insp = self.insp.post("/inspections", {
                "road_id": self.roads[road]["id"],
                "road_segment_id": self.segments[(road, seg)]["id"],
                "captured_at": (self.now - timedelta(days=days_ago)).isoformat(),
                "location": location,
                "notes": f"[{plan.MARK}:{key}] {plan.DEMO_NOTE} Demo coordinates and demo capture date. {plan.PHOTO_NOTE}",
            })
            self.inspections[marker] = insp
        iid = insp["id"]
        data = (PHOTOS / photo).read_bytes()
        if not self.insp.get(f"/inspections/{iid}/media"):
            up = self.insp.post(f"/inspections/{iid}/media/upload-url",
                                {"filename": photo, "content_type": "image/jpeg", "size_bytes": len(data)})
            self.insp.upload(up["upload_url"], data, {"Content-Type": "image/jpeg"})
            self.insp.post(f"/inspections/{iid}/media/complete", {
                "storage_path": up["storage_path"], "storage_bucket": up["storage_bucket"], "media_type": "IMAGE",
                "mime_type": "image/jpeg", "size_bytes": len(data), "original_filename": photo, "location": location,
            })
        insp = self.insp.get(f"/inspections/{iid}")
        if insp["status"] in ("DRAFT", "UPLOADING"):
            self.insp.post(f"/inspections/{iid}/submit")
            insp = self.insp.get(f"/inspections/{iid}")
        if insp["status"] not in ("ANALYZED", "PROCESSED", "COMPLETED"):
            job_id = self.insp.post(f"/inspections/{iid}/process")["job_id"]
            job = self.wait_job(job_id)
            if job["status"] != "COMPLETED":
                raise SeedError(f"AI processing of inspection {key} ended as {job['status']}: {job.get('error_message')}")
        dets = self.insp.get(f"/inspections/{iid}/detections") or []
        bad = [d for d in dets if d.get("detection_method") not in (None, "TRAINED_MODEL")]
        if bad:
            raise SeedError(f"inspection {key}: detections were not produced by the trained model ({bad[0].get('detection_method')})")
        log(f"  inspection {key:<4} {photo}: {len(dets)} detection(s) "
            + ", ".join(f"{d['damage_type']} {d['confidence']:.2f}" for d in sorted(dets, key=lambda d: -d['confidence'])))
        return insp, dets

    def wait_job(self, job_id: str, timeout_s: int = 600) -> dict:
        deadline = time.time() + timeout_s
        while True:
            job = self.insp.get(f"/jobs/{job_id}")
            if job["status"] in ("COMPLETED", "FAILED", "DEAD_LETTER") or time.time() > deadline:
                return job
            time.sleep(2)

    # ---------------------------------------------------------------- damage
    def promote(self, dets: list[dict], damage_type: str) -> dict | None:
        best = max((d for d in dets if d["damage_type"] == damage_type), key=lambda d: d["confidence"], default=None)
        if best is None:
            return None
        return self.rev.post(f"/damages/from-detection/{best['id']}")

    def review(self, rec: dict, decision: str, severity: str | None, note: str) -> dict:
        if rec["status"] != "PENDING_REVIEW":
            return rec
        body = {"decision": decision, "notes": f"{note} ({plan.DEMO_NOTE.rstrip('.')} review decision.)"}
        if severity:
            body["severity"] = severity
        self.rev.post(f"/damages/{rec['id']}/review", body)
        return self.rev.get(f"/damages/{rec['id']}")

    # ----------------------------------------------------------- maintenance
    def job(self, site: dict, damage_ids: list[str]) -> dict:
        spec = site["job"]
        job = self.jobs.get(spec["title"])
        if job is None:
            job = self.eng.post("/maintenance-jobs", {
                "title": spec["title"],
                "description": f"[{plan.MARK}:{site['key']}] {plan.DEMO_NOTE} Maintenance job for the demo dataset.",
                "road_id": self.roads[site["road"]]["id"],
                "road_segment_id": self.segments[(site["road"], site["seg"])]["id"],
                "damage_record_ids": damage_ids,
                "due_at": (self.now + timedelta(days=14)).isoformat(),
            })
            self.jobs[spec["title"]] = job
        return self.advance(job, spec)

    def advance(self, job: dict, spec: dict) -> dict:
        """Walk the job through the real state machine up to its target status."""
        target = spec["target"]
        order = ["OPEN", "ASSIGNED", "IN_PROGRESS", "COMPLETED"]
        job = self.eng.get(f"/maintenance-jobs/{job['id']}")
        if target == "CANCELLED":
            if job["status"] == "OPEN":
                self.eng.post(f"/maintenance-jobs/{job['id']}/status", {"status": "CANCELLED", "reason": spec["cancel_reason"]})
            return self.eng.get(f"/maintenance-jobs/{job['id']}")
        if job["status"] not in order or self.eng.get(f"/maintenance-jobs/{job['id']}/repair-evidence"):
            return job  # repair evidence exists: the job is in (or past) verification, leave its state alone
        while order.index(job["status"]) < order.index(target):
            nxt = order[order.index(job["status"]) + 1]
            if nxt == "ASSIGNED":
                body = ({"assigned_to_organization_id": self.ids["contractors"][spec["contractor"]]}
                        if spec.get("contractor") else {"assigned_to_user_id": self.as_[spec.get("user", "engineer")].user_id})
                self.eng.post(f"/maintenance-jobs/{job['id']}/assign", body)
                job = self.eng.get(f"/maintenance-jobs/{job['id']}")
                if job["status"] == "OPEN":
                    self.eng.post(f"/maintenance-jobs/{job['id']}/status", {"status": "ASSIGNED", "reason": "DEMO: assigned"})
            else:
                reason = {"IN_PROGRESS": "DEMO: crew on site", "COMPLETED": "DEMO: work reported complete"}[nxt]
                self.eng.post(f"/maintenance-jobs/{job['id']}/status", {"status": nxt, "reason": reason})
            job = self.eng.get(f"/maintenance-jobs/{job['id']}")
        return job

    # ---------------------------------------------------------------- repair
    def evidence(self, job_id: str, kind: str, data: bytes, filename: str, lat: float, lon: float, note: str) -> None:
        if any(e["evidence_type"] == kind for e in self.eng.get(f"/maintenance-jobs/{job_id}/repair-evidence") or []):
            return
        up = self.eng.post(f"/maintenance-jobs/{job_id}/repair-evidence/upload-url", {
            "filename": filename, "content_type": "image/jpeg", "size_bytes": len(data), "evidence_type": kind})
        self.eng.upload(up["upload_url"], data, up.get("upload_headers") or {"Content-Type": "image/jpeg"})
        self.eng.post(f"/maintenance-jobs/{job_id}/repair-evidence/complete", {
            "storage_path": up["storage_path"], "storage_bucket": up["storage_bucket"], "evidence_type": kind,
            "media_type": "IMAGE", "mime_type": "image/jpeg", "file_size_bytes": len(data),
            "latitude": lat, "longitude": lon, "notes": note})

    def repair(self, site: dict, job: dict, dets: list[dict], lat: float, lon: float) -> dict:
        spec, key, job_id = site["repair"], site["key"], job["id"]
        before = (PHOTOS / site["photo"]).read_bytes()
        boxes = [(d["bbox"]["x_min"], d["bbox"]["y_min"], d["bbox"]["x_max"], d["bbox"]["y_max"]) for d in dets]
        seed = sum(ord(c) for c in key)
        kind = spec["after"]
        if kind == "repaired":
            after, what = derive.repaired(before, boxes, seed), "damage regions patched"
        elif kind == "partial":
            after, what = derive.partial(before, boxes, seed), "damage regions only partly patched"
        elif kind == "unchanged":
            after, what = derive.unchanged(before, seed), "no repair applied (second photo of the same scene)"
        else:
            after, what = (PHOTOS / spec["mismatch_photo"]).read_bytes(), "a photo of a DIFFERENT place (wrong evidence)"
        if spec.get("before_evidence"):
            self.evidence(job_id, "BEFORE_REPAIR", before, f"before_{site['photo']}", lat, lon,
                          f"{plan.DEMO_NOTE} BEFORE evidence. {plan.PHOTO_NOTE}")
        self.evidence(job_id, "AFTER_REPAIR", after, f"after_{kind}_{site['photo']}", lat, lon,
                      f"{plan.DEMO_NOTE} Constructed AFTER image, not a photograph of a real repair: {what}.")

        vers = self.rev.get(f"/maintenance-jobs/{job_id}/verifications") or []
        auto = next((v for v in vers if v.get("verification_type") == "AUTOMATED_IMAGE_ANALYSIS"), None)
        if auto is None:
            auto = self.eng.post(f"/maintenance-jobs/{job_id}/repair-verifications", {})
        deadline = time.time() + 600
        while auto["verification_status"] not in ("COMPLETED", "FAILED") and time.time() < deadline:
            time.sleep(2)
            vers = self.rev.get(f"/maintenance-jobs/{job_id}/verifications") or []
            auto = next(v for v in vers if v["id"] == auto["id"])
        if auto["verification_status"] != "COMPLETED":
            raise SeedError(f"repair verification for site {key} ended as {auto['verification_status']}: {auto.get('error_message')}")
        log(f"  verification {key}: AFTER={kind:<9} -> {auto['result']} ({(auto.get('findings') or {}).get('reason_code')})")

        human = next((v for v in vers if v.get("reviewed_verification_id") == auto["id"]), None)
        if human is None and spec.get("human"):
            decision, final, note = spec["human"]
            body = {"decision": decision, "notes": f"{note} ({plan.DEMO_NOTE.rstrip('.')} reviewer decision.)"}
            if final:
                body["final_result"] = final
            human = self.rev.post(f"/maintenance-jobs/{job_id}/repair-verifications/{auto['id']}/review", body)
        job = self.eng.get(f"/maintenance-jobs/{job_id}")
        if spec.get("then") and job["status"] != spec["then"]:
            allowed = {"COMPLETED": ["VERIFICATION_PENDING", "IN_PROGRESS"], "REJECTED": ["IN_PROGRESS"]}.get(job["status"], [])
            if spec["then"] in allowed:
                reason = {"VERIFICATION_PENDING": "DEMO: awaiting human review of the automated verification",
                          "IN_PROGRESS": "DEMO: rework ordered after rejected repair"}[spec["then"]]
                self.eng.post(f"/maintenance-jobs/{job_id}/status", {"status": spec["then"], "reason": reason})
                job = self.eng.get(f"/maintenance-jobs/{job_id}")
        return {
            "after_image": kind, "automated_result": auto["result"],
            "reason_code": (auto.get("findings") or {}).get("reason_code"),
            "model": f"{auto.get('model_name')} {auto.get('model_version')}", "algorithm": auto.get("algorithm_version"),
            "human_decision": (human or {}).get("review_decision"), "final_result": (human or {}).get("result"),
            "job_status": job["status"],
        }

    # ------------------------------------------------------------------ sites
    def seed_sites(self) -> None:
        log("inspections, AI detection, review, maintenance, repair verification")
        for site in plan.SITES:
            key = site["key"]
            lat, lon = plan.point_on(site["road"], site["seg"], site["frac"])
            res = self.results.setdefault(key, {"photo": site["photo"], "road": plan.ROADS[site["road"]]["name"], "segment": site["seg"]})
            _, dets = self.inspection(key, site["road"], site["seg"], lat, lon, site["photo"], site["days_ago"])
            res["detections"] = [{"type": d["damage_type"], "confidence": d["confidence"]} for d in dets]
            records = {}
            for dtype in site["promote"]:
                rec = self.promote(dets, dtype)
                if rec is None:
                    self.warn(f"site {key}: the model reported no {dtype} in {site['photo']}; nothing promoted for it")
                    continue
                if dtype in site.get("review", {}):
                    rec = self.review(rec, *site["review"][dtype])
                records[dtype] = rec
            if site.get("regroup"):
                # ~2 m east: inside the platform's GPS grouping radius, so the sightings merge.
                _, dets2 = self.inspection(key + "-2", site["road"], site["seg"], lat, lon + 0.00002, site["photo"],
                                           max(site["days_ago"] - 6, 1))
                for dtype in records:
                    self.promote(dets2, dtype)
                records = {t: self.rev.get(f"/damages/{r['id']}") for t, r in records.items()}
            res["damages"] = {t: {"id": r["id"], "status": r["status"], "severity": r["severity"],
                                  "observations": r.get("observation_count")} for t, r in records.items()}
            confirmed = [r["id"] for r in records.values() if r["status"] not in ("PENDING_REVIEW", "REJECTED", "DETECTED")]
            if site.get("job") and (confirmed or site["job"]["title"] in self.jobs):
                job = self.job(site, confirmed)
                res["job"] = {"title": job["title"], "status": job["status"], "priority": job.get("priority_level"),
                              "priority_score": job.get("priority_score")}
                if site.get("repair") and job["status"] != "CANCELLED":
                    res["repair"] = self.repair(site, job, dets, lat, lon)
                    res["job"]["status"] = res["repair"]["job_status"]
            elif site.get("job"):
                self.warn(f"site {key}: no confirmed damage, so no maintenance job was created")

    def seed_followups(self) -> None:
        """Later inspections at repaired sites: recurrences and a clean follow-up."""
        log("follow-up inspections (recurrence monitoring)")
        for site in plan.SITES:
            key = site["key"]
            lat, lon = plan.point_on(site["road"], site["seg"], site["frac"])
            res = self.results[key]
            rep = res.get("repair") or {}
            if site.get("recurrence"):
                spec = site["recurrence"]
                if rep.get("final_result") != "SUCCESSFUL":
                    self.warn(f"site {key}: repair was not finally SUCCESSFUL, so no recurrence inspection was made")
                    continue
                _, dets = self.inspection(key + "-R", site["road"], site["seg"], lat, lon + 0.00001, spec["photo"], 0)
                rec = self.promote(dets, spec["type"])
                if rec is None:
                    self.warn(f"site {key}: the model reported no {spec['type']} in the follow-up photo")
                    continue
                rec = self.review(rec, "CONFIRMED", spec.get("severity"), "Damage is back at a repaired location.")
                res["recurrence_damage"] = {"id": rec["id"], "status": rec["status"], "severity": rec["severity"]}
            if site.get("followup_clean"):
                _, dets = self.inspection(key + "-F", site["road"], site["seg"], lat, lon, site["followup_clean"], 0)
                res["followup_detections"] = len(dets)
        for c in plan.CLEAN_INSPECTIONS:
            lat, lon = plan.point_on(c["road"], c["seg"], c["frac"])
            insp, dets = self.inspection(c["key"], c["road"], c["seg"], lat, lon, c["photo"], c["days_ago"])
            self.results[c["key"]] = {"photo": c["photo"], "detections": len(dets), "inspection_id": insp["id"]}
        m = plan.MANUAL_DAMAGE
        insp_id = self.results[m["inspection"]]["inspection_id"]
        if not any(d.get("inspection_id") == insp_id and d.get("source_type") == "MANUAL" for d in self.rev.pages("/damages")):
            c = next(x for x in plan.CLEAN_INSPECTIONS if x["key"] == m["inspection"])
            lat, lon = plan.point_on(c["road"], c["seg"], c["frac"])
            self.insp.post("/damages", {
                "inspection_id": insp_id, "damage_type_id": self.damage_types[m["type"]], "severity": m["severity"],
                "location": {"latitude": lat, "longitude": lon}, "road_id": self.roads[c["road"]]["id"],
                "road_segment_id": self.segments[(c["road"], c["seg"])]["id"], "notes": m["notes"]})

    def seed_recurrence_reviews(self) -> None:
        log("recurrence records")
        recs = self.rev.pages("/recurrence")
        by_new = {r.get("new_damage_id"): r for r in recs}
        for site in plan.SITES:
            spec, res = site.get("recurrence"), self.results[site["key"]]
            if not spec or "recurrence_damage" not in res:
                continue
            rec = by_new.get(res["recurrence_damage"]["id"])
            if rec is None:
                self.warn(f"site {site['key']}: the platform created no recurrence record for the follow-up damage")
                continue
            if spec.get("review") and rec.get("status") == "POTENTIAL":
                status, note = spec["review"]
                rec = self.rev.post(f"/recurrence/{rec['id']}/review",
                                    {"status": status, "notes": f"{note} ({plan.DEMO_NOTE.rstrip('.')} reviewer decision.)"})
            res["recurrence"] = {k: rec.get(k) for k in ("id", "status", "escalation_level", "spatial_distance_meters",
                                                         "temporal_distance_days", "escalation_reasons")}
            if spec.get("job_title"):
                # The returned damage gets its own job, so its priority (with the recurrence factor) is visible.
                job = self.jobs.get(spec["job_title"]) or self.eng.post("/maintenance-jobs", {
                    "title": spec["job_title"],
                    "description": f"[{plan.MARK}:{site['key']}-R] {plan.DEMO_NOTE} Re-repair after a recurrence.",
                    "road_id": self.roads[site["road"]]["id"],
                    "road_segment_id": self.segments[(site["road"], site["seg"])]["id"],
                    "damage_record_ids": [res["recurrence_damage"]["id"]],
                })
                self.jobs[spec["job_title"]] = job
                res["recurrence_job"] = {"title": job["title"], "status": job["status"], "priority": job.get("priority_level"),
                                         "priority_score": job.get("priority_score"),
                                         "components": (job.get("priority_factors") or {}).get("components")}
            log(f"  recurrence at site {site['key']}: status {rec.get('status')}, escalation {rec.get('escalation_level')}")

    # ------------------------------------------------- health / estimates / reports
    def seed_intelligence(self) -> None:
        log("road health and rule-based deterioration estimates")
        health, estimates = {}, {}
        for (rkey, n), seg in self.segments.items():
            # The platform recalculates health itself whenever damage changes; a snapshot is requested
            # here only for a segment that has none, and an estimate only when it is older than the
            # health it is based on. A re-run with no changes therefore adds nothing.
            h = self.optional(f"/road-segments/{seg['id']}/health")
            if not h or h.get("health_score") is None:
                h = self.sup.post(f"/road-segments/{seg['id']}/calculate-health")
            health[f"{rkey}-S{n}"] = {"score": h.get("health_score"), "status": h.get("health_status")}
            latest = self.optional(f"/road-segments/{seg['id']}/predictions")
            if not latest or (latest.get("generated_at") or "") < (h.get("calculated_at") or ""):
                latest = self.sup.post(f"/road-segments/{seg['id']}/predictions", {"prediction_horizon_days": 90})
            estimates[f"{rkey}-S{n}"] = {
                "risk": latest.get("predicted_risk"), "band": (latest.get("features") or {}).get("risk_band"),
                "method": latest.get("estimation_method") or latest.get("model_name"), "status": latest.get("status")}
        for rkey, road in self.roads.items():
            h = self.optional(f"/roads/{road['id']}/health")
            newest = max((s.get("score") is not None for k, s in health.items() if k.startswith(rkey + "-")), default=False)
            if not h or h.get("health_score") is None or not newest:
                h = self.sup.post(f"/roads/{road['id']}/calculate-health")
            health[rkey] = {"score": h.get("health_score"), "status": h.get("health_status")}
        self.results["_health"], self.results["_estimates"] = health, estimates

    def optional(self, path: str) -> dict | None:
        r = self.sup.send("GET", f"{self.sup.base}{path}", headers=self.sup.headers)
        return (r.json().get("data") or None) if r.status_code == 200 else None

    def seed_reports(self) -> None:
        log("reports")
        existing = {(r["report_type"], str((r.get("parameters") or {}).get("format", "JSON")).upper()): r
                    for r in self.sup.pages("/reports") if r.get("status") in ("COMPLETED", "READY", "GENERATED")}
        out = []
        for rtype, fmt in plan.REPORTS:
            rep = existing.get((rtype, fmt))
            if rep is None:
                created = self.sup.post("/reports", {"report_type": rtype, "parameters": {"format": fmt}})
                rid = created.get("report_id") or created.get("id")
                for _ in range(60):
                    rep = self.sup.get(f"/reports/{rid}")
                    if rep["status"] not in ("PENDING", "QUEUED", "PROCESSING", "GENERATING"):
                        break
                    time.sleep(1)
            out.append({"type": rtype, "format": fmt, "status": rep["status"], "id": rep["id"]})
            log(f"  {rtype} ({fmt}): {rep['status']}")
        self.results["_reports"] = out

    def summary(self) -> dict:
        dash = self.sup.get("/dashboard/summary")
        damages = self.rev.pages("/damages")
        jobs = self.eng.pages("/maintenance-jobs")
        inspections = self.insp.pages("/inspections")
        recs = self.rev.pages("/recurrence")

        def count(items, field):
            out: dict[str, int] = {}
            for i in items:
                out[str(i.get(field))] = out.get(str(i.get(field)), 0) + 1
            return dict(sorted(out.items()))

        return {
            "seeded_at": datetime.now(timezone.utc).isoformat(),
            "organization": {"code": plan.ORG_CODE, "name": plan.ORG_NAME, "id": self.ids["organization_id"]},
            "counts": {
                "roads": len(self.roads), "segments": len(self.segments), "inspections": len(inspections),
                "damage_records": len(damages), "maintenance_jobs": len(jobs), "recurrences": len(recs),
            },
            "inspections_by_status": count(inspections, "status"),
            "damage_by_status": count(damages, "status"), "damage_by_severity": count(damages, "severity"),
            "damage_by_type": count(damages, "damage_type_code"), "damage_by_source": count(damages, "source_type"),
            "jobs_by_status": count(jobs, "status"), "jobs_by_priority": count(jobs, "priority_level"),
            "recurrence_by_status": count(recs, "status"),
            "dashboard_summary": dash, "sites": self.results, "warnings": self.warnings,
        }

    def run(self) -> dict:
        self.seed_roads()
        self.load_existing()
        self.seed_sites()
        self.seed_followups()
        self.seed_recurrence_reviews()
        self.seed_intelligence()
        self.seed_reports()
        return self.summary()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000/api/v1", help="API base URL of the running stack")
    args = parser.parse_args()

    missing = [n for n in plan.all_photos() if not (PHOTOS / n).exists()]
    if missing:
        log(f"downloading {len(missing)} demo photo(s) (RDD2022 India test images)...")
        subprocess.run([sys.executable, str(DEMO_DIR / "fetch_demo_photos.py")], check=True)

    try:
        summary = Seeder(args.api).run()
    except SeedError as exc:
        sys.exit(f"\nSEED FAILED: {exc}\nFix the cause and run the script again; finished steps are skipped.")

    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    c = summary["counts"]
    log("\n===== FACULTY DEMO DATASET (DEMO / SYNTHETIC) =====")
    log(f"organization : {plan.ORG_NAME}")
    log(f"roads {c['roads']} | segments {c['segments']} | inspections {c['inspections']} | damage records {c['damage_records']} "
        f"| maintenance jobs {c['maintenance_jobs']} | recurrences {c['recurrences']}")
    log(f"damage by status   : {summary['damage_by_status']}")
    log(f"damage by severity : {summary['damage_by_severity']}")
    log(f"jobs by status     : {summary['jobs_by_status']}")
    for key, r in summary["sites"].items():
        if isinstance(r, dict) and r.get("repair"):
            x = r["repair"]
            log(f"repair {key}: AFTER={x['after_image']:<9} automated={x['automated_result']:<11} "
                f"human={x['human_decision'] or 'awaiting':<10} final={x['final_result'] or '-':<11} job={x['job_status']}")
    if summary["warnings"]:
        log("warnings:")
        for w in summary["warnings"]:
            log(f"  - {w}")
    log(f"\nlogin details : {CREDS_FILE.relative_to(REPO)} (local, git-ignored)")
    log(f"full summary  : {SUMMARY_FILE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
