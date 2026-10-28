"""Pull recent accepted LeetCode submissions and mark sheet problems solved.

Only submissions made on/after config.start_date count, so problems you
solved on LeetCode before starting this sheet are NOT auto-marked.

- Unsolved problem + AC        -> marked solved (rating "ok", flagged unrated
                                  so the dashboard asks you to rate it).
- Solved problem that is *due* -> logged as a revision (rating "ok").
- Anything else                -> ignored (extra practice).

LeetCode's public API only returns your ~20 most recent accepted submissions,
so the GitHub Action runs this every few hours.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime

import tracker

QUERY = """query($u: String!, $l: Int!) {
  recentAcSubmissionList(username: $u, limit: $l) { titleSlug timestamp }
}"""


def fetch(username: str) -> list[dict]:
    req = urllib.request.Request(
        "https://leetcode.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"u": username, "l": 20}}).encode(),
        headers={"Content-Type": "application/json", "Referer": "https://leetcode.com",
                 "User-Agent": "Mozilla/5.0 (striver-sde-tracker)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]["recentAcSubmissionList"] or []


def main() -> int:
    problems = tracker.load_problems()
    progress = tracker.load_progress()
    cfg = progress["config"]
    username = (cfg.get("leetcode_username") or "").strip()
    if not username:
        print("No leetcode_username in data/progress.json config; skipping sync.")
        return 0

    # One LeetCode slug can back several sheet rows (e.g. Inorder + Morris Inorder);
    # each new AC fills the next unsolved row in sheet order.
    by_slug: dict[str, list[int]] = {}
    for p in problems["problems"]:
        if p["lc"]:
            by_slug.setdefault(p["lc"]["slug"], []).append(p["id"])

    zone = tracker.tz(progress)
    start = cfg["start_date"]
    sync = progress.setdefault("sync", {})
    last_ts = int(sync.get("last_ts", 0))
    subs = sorted(fetch(username), key=lambda s: int(s["timestamp"]))
    changed = []

    for s in subs:
        ts = int(s["timestamp"])
        on = datetime.fromtimestamp(ts, zone).date()
        if ts <= last_ts or on.isoformat() < start or s["titleSlug"] not in by_slug:
            continue
        ids = by_slug[s["titleSlug"]]
        entries = progress["problems"]
        unsolved = [i for i in ids if not entries.get(str(i), {}).get("solved")]
        if unsolved:
            pid = unsolved[0]
            tracker.record_solve(entries.setdefault(str(pid), {}), on, "ok", "lc", rated=False)
            changed.append(f"solved #{pid} {s['titleSlug']}")
        else:
            for pid in ids:
                e = entries[str(pid)]
                touched = max([e["solved"]] + [r["d"] for r in e.get("reviews", [])])
                if e.get("due") and e["due"] <= on.isoformat() and touched < on.isoformat():
                    tracker.record_review(e, on, "ok", "lc")
                    changed.append(f"reviewed #{pid} {s['titleSlug']}")
                    break
        last_ts = max(last_ts, ts)

    # Only write when something moved, so the Action doesn't make empty commits.
    if last_ts != int(sync.get("last_ts", 0)):
        sync.update(last_ts=last_ts, last_change=tracker.now_iso())
        tracker.save_progress(progress)
    print("\n".join(changed) or "No new sheet problems in recent submissions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
