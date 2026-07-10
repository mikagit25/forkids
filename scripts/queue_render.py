#!/usr/bin/env python3
"""
Dynamic render queue manager.

Reads/writes config/render_queue.yaml.
The sequential runner drains this queue at the end of each run.

Usage:
  python3 scripts/queue_render.py --list
  python3 scripts/queue_render.py --add "python3 scripts/generate_dance_long.py --themes animals" \
      --log logs/dance_long_3d.log --desc "dance animals 3D"
  python3 scripts/queue_render.py --run-all      # used by run_renders_sequential.sh
  python3 scripts/queue_render.py --has-pending  # exit 0 if pending jobs exist
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT       = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "config" / "render_queue.yaml"


def _load() -> dict:
    if not QUEUE_FILE.exists():
        return {"jobs": []}
    with open(QUEUE_FILE) as f:
        data = yaml.safe_load(f) or {}
    if "jobs" not in data:
        data["jobs"] = []
    return data


def _save(data: dict) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _make_id(cmd: str) -> str:
    slug = cmd.replace("python3 scripts/", "").replace(".py", "").replace(" ", "_")
    slug = "".join(c if c.isalnum() or c == "_" else "" for c in slug)[:50]
    return f"{slug}_{datetime.now().strftime('%Y%m%d')}"


def cmd_list(data: dict) -> None:
    jobs = data.get("jobs", [])
    if not jobs:
        print("Queue is empty.")
        return
    pending = [j for j in jobs if j.get("status") == "pending"]
    done    = [j for j in jobs if j.get("status") == "done"]
    failed  = [j for j in jobs if j.get("status") == "failed"]
    print(f"Render queue — {len(pending)} pending, {len(done)} done, {len(failed)} failed\n")
    for j in jobs:
        status = j.get("status", "?")
        icon   = {"pending": "⏳", "done": "✅", "failed": "❌", "running": "🔄"}.get(status, "?")
        print(f"  {icon} [{j.get('added','')}] {j.get('id','')}")
        print(f"       {j.get('desc', j.get('cmd',''))}")
        if status == "done":
            print(f"       finished: {j.get('finished','')}")
        if status == "failed":
            print(f"       error: {j.get('error','')}")


def cmd_add(data: dict, cmd: str, log: str, desc: str) -> None:
    job_id = _make_id(cmd)
    for j in data["jobs"]:
        if j.get("id") == job_id:
            print(f"Job already in queue: {job_id}")
            return
    job = {
        "id":     job_id,
        "cmd":    cmd,
        "log":    log or "logs/render_queue.log",
        "desc":   desc or cmd,
        "added":  datetime.now().strftime("%Y-%m-%d"),
        "status": "pending",
    }
    data["jobs"].append(job)
    _save(data)
    print(f"Added: {job_id}")


def cmd_run_all(data: dict) -> int:
    """Run all pending jobs sequentially. Returns number of failures."""
    pending = [j for j in data["jobs"] if j.get("status") == "pending"]
    if not pending:
        print("No pending jobs in render queue.")
        return 0

    print(f"Processing {len(pending)} pending render job(s)...")
    failures = 0

    for job in pending:
        job_id = job.get("id", "?")
        desc   = job.get("desc", job.get("cmd", ""))
        cmd    = job.get("cmd", "")
        log    = ROOT / job.get("log", "logs/render_queue.log")

        print(f"\n▶ {job_id}")
        print(f"  {desc}")
        print(f"  cmd: {cmd}")

        # Mark running
        job["status"] = "running"
        job["started"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _save(data)

        log.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(log, "a") as lf:
                lf.write(f"\n=== {job_id} start {datetime.now()} ===\n")
                result = subprocess.run(
                    cmd, shell=True, cwd=str(ROOT),
                    stdout=lf, stderr=subprocess.STDOUT,
                )
                lf.write(f"=== {job_id} end rc={result.returncode} {datetime.now()} ===\n")

            if result.returncode == 0:
                job["status"] = "done"
                job["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                print(f"  ✅ done")
            else:
                job["status"] = "failed"
                job["error"] = f"exit code {result.returncode}"
                job["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                print(f"  ❌ failed (rc={result.returncode}), see {log}")
                failures += 1
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            print(f"  ❌ exception: {e}")
            failures += 1

        _save(data)

    return failures


def cmd_has_pending(data: dict) -> bool:
    return any(j.get("status") == "pending" for j in data.get("jobs", []))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render queue manager")
    sub = parser.add_subparsers(dest="action")

    sub.add_parser("list", help="Show queue status")
    sub.add_parser("has-pending", help="Exit 0 if pending jobs exist")
    sub.add_parser("run-all", help="Run all pending jobs (used by sequential runner)")

    p_add = sub.add_parser("add", help="Add a job to the queue")
    p_add.add_argument("cmd", help="Shell command to run")
    p_add.add_argument("--log",  default="logs/render_queue.log", help="Log file path")
    p_add.add_argument("--desc", default="", help="Human-readable description")

    # Also support --list --add etc as flags for convenience
    parser.add_argument("--list",        action="store_true")
    parser.add_argument("--has-pending", action="store_true", dest="has_pending_flag")
    parser.add_argument("--run-all",     action="store_true", dest="run_all_flag")
    parser.add_argument("--add",         metavar="CMD",       dest="add_cmd")
    parser.add_argument("--log",         default="logs/render_queue.log")
    parser.add_argument("--desc",        default="")

    args = parser.parse_args()
    data = _load()

    if args.action == "list" or args.list:
        cmd_list(data)
    elif args.action == "has-pending" or args.has_pending_flag:
        sys.exit(0 if cmd_has_pending(data) else 1)
    elif args.action == "run-all" or args.run_all_flag:
        failures = cmd_run_all(data)
        sys.exit(failures)
    elif args.action == "add":
        cmd_add(data, args.cmd, args.log, args.desc)
    elif args.add_cmd:
        cmd_add(data, args.add_cmd, args.log, args.desc)
    else:
        cmd_list(data)


if __name__ == "__main__":
    main()
