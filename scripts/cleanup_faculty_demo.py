"""
Remove the RoadSense FACULTY DEMO dataset, and only that.

Deletes every row that belongs to the dedicated demo organization (code FACULTY-DEMO), the
demo users (…@faculty-demo.roadsense.example), the demo contractor organizations
(codes FDEMO-C-*) and the files the demo uploaded. No other organization's data is touched.
(If a job of another organization was assigned to a demo contractor, only that assignment
is cleared.)

    python scripts/cleanup_faculty_demo.py            # shows what would be removed, asks first
    python scripts/cleanup_faculty_demo.py --yes      # no question
    python scripts/cleanup_faculty_demo.py --dry-run  # only show

Requires the Docker stack to be running. Downloaded photos (scripts/demo/photos) are kept.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "demo"))
import demo_plan as plan

CREDS_FILE = REPO / "scripts" / "demo" / "faculty_demo.local.env"
SUMMARY_FILE = REPO / "scripts" / "demo" / "last_seed_summary.json"

ORG = f"(select id from organizations where code = '{plan.ORG_CODE}')"
CONTRACTORS = "(select id from organizations where code like 'FDEMO-C-%' and organization_type = 'CONTRACTOR')"
USERS = f"(select id from users where email like '%@{plan.EMAIL_DOMAIN}')"

COUNT_SQL = f"""
select 'organization', count(*) from organizations where code = '{plan.ORG_CODE}'
union all select 'contractor organizations', count(*) from organizations where id in {CONTRACTORS}
union all select 'users', count(*) from users where id in {USERS}
union all select 'roads', count(*) from roads where organization_id = {ORG}
union all select 'road segments', count(*) from road_segments where organization_id = {ORG}
union all select 'inspections', count(*) from inspections where organization_id = {ORG}
union all select 'AI detections', count(*) from ai_detections where organization_id = {ORG}
union all select 'damage records', count(*) from damage_records where organization_id = {ORG}
union all select 'maintenance jobs', count(*) from maintenance_jobs where organization_id = {ORG}
union all select 'repair evidence', count(*) from repair_evidence where organization_id = {ORG}
union all select 'repair verifications', count(*) from repair_verifications where organization_id = {ORG}
union all select 'recurrence records', count(*) from recurrence_records where organization_id = {ORG}
union all select 'health snapshots', count(*) from road_health_snapshots where organization_id = {ORG}
union all select 'reports', count(*) from generated_reports where organization_id = {ORG}
union all select 'audit log entries', count(*) from audit_logs where organization_id = {ORG};
"""

FILES_SQL = f"""
select storage_bucket || '/' || storage_path from inspection_media where organization_id = {ORG}
union all select storage_bucket || '/' || storage_path from repair_evidence where organization_id = {ORG};
"""

# Deletes the demo tenant's rows from every table that has an organization_id column. Tables
# are retried until their foreign-key dependants are gone, so no table order is hard-coded.
DELETE_SQL = f"""
do $$
declare
    org uuid := {ORG};
    pending text[];
    blocked text[];
    t text;
    col record;
    demo_users uuid[] := array(select id from users where email like '%@{plan.EMAIL_DOMAIN}');
begin
    if org is null then
        raise notice 'demo organization not found; removing demo users/contractors only';
    else
        select array_agg(table_name::text) into pending from information_schema.columns
         where table_schema = 'public' and column_name = 'organization_id' and table_name <> 'organization_memberships';
        while pending is not null and array_length(pending, 1) > 0 loop
            blocked := '{{}}';
            foreach t in array pending loop
                begin
                    execute format('delete from %I where organization_id = $1', t) using org;
                exception when foreign_key_violation then
                    blocked := blocked || t;
                end;
            end loop;
            if array_length(blocked, 1) = array_length(pending, 1) then
                raise exception 'cannot delete demo rows from: %', blocked;
            end if;
            pending := blocked;
        end loop;
    end if;

    -- Assignments of other organizations' jobs to a demo contractor are cleared, not deleted.
    update maintenance_jobs set assigned_to_organization_id = null where assigned_to_organization_id in {CONTRACTORS};

    -- Rows that only reference the demo users (sessions, tokens and the like).
    for col in
        select kcu.table_name, kcu.column_name
          from information_schema.table_constraints tc
          join information_schema.key_column_usage kcu on kcu.constraint_name = tc.constraint_name
          join information_schema.constraint_column_usage ccu on ccu.constraint_name = tc.constraint_name
         where tc.constraint_type = 'FOREIGN KEY' and ccu.table_name = 'users' and tc.table_schema = 'public'
    loop
        begin
            execute format('delete from %I where %I = any($1)', col.table_name, col.column_name) using demo_users;
        exception when foreign_key_violation then
            raise exception 'demo users are still referenced by %.%', col.table_name, col.column_name;
        end;
    end loop;

    delete from organization_memberships where organization_id = org;
    delete from users where id = any(demo_users);
    delete from organizations where id in {CONTRACTORS};
    delete from organizations where id = org;
end $$;
"""


def psql(sql: str) -> str:
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "sh", "-c",
         'psql -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input=sql, capture_output=True, text=True, cwd=REPO, check=False,
    )
    if proc.returncode != 0:
        sys.exit("database command failed:\n" + proc.stderr[-800:])
    return proc.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="delete without asking")
    parser.add_argument("--dry-run", action="store_true", help="only show what would be removed")
    args = parser.parse_args()

    counts = [line.split("|") for line in psql(COUNT_SQL).splitlines() if "|" in line]
    print(f"DEMO dataset ({plan.ORG_CODE}) currently holds:")
    for name, n in counts:
        print(f"  {name:<26} {n}")
    if all(n == "0" for _, n in counts):
        print("Nothing to remove.")
        return
    if args.dry_run:
        return
    if not args.yes and input("Delete all of the above? Type yes: ").strip().lower() != "yes":
        print("Cancelled.")
        return

    files = [f for f in psql(FILES_SQL).splitlines() if f.strip()]
    files += [f for f in psql(f"select storage_bucket || '/' || storage_path from generated_reports "
                              f"where organization_id = {ORG} and storage_path is not null;").splitlines() if f.strip()]
    psql(DELETE_SQL)

    # Uploaded files live under the api container's local storage root.
    targets = [f"/data/media/{f}" for f in files]
    for i in range(0, len(targets), 40):
        script = "; ".join(f'rm -f "{t}"; rmdir "$(dirname "{t}")" 2>/dev/null' for t in targets[i:i + 40]) + "; true"
        subprocess.run(["docker", "compose", "exec", "-T", "-u", "root", "api", "sh", "-c", script], cwd=REPO, check=False)

    for path in (CREDS_FILE, SUMMARY_FILE):
        path.unlink(missing_ok=True)

    left = [line.split("|") for line in psql(COUNT_SQL).splitlines() if "|" in line]
    remaining = {name: n for name, n in left if n != "0"}
    if remaining:
        sys.exit(f"Some demo rows remain: {remaining}")
    print(f"Removed the demo dataset and {len(targets)} stored file(s). Other organizations were not touched.")


if __name__ == "__main__":
    main()
