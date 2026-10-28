"""Shared logic for the tracker: progress I/O, spaced repetition and stats.

The dashboard (index.html) implements the same rules in JavaScript; keep
INTERVALS / next_step in sync with `SRS` there if you change them.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_PATH = ROOT / "data" / "problems.json"
PROGRESS_PATH = ROOT / "data" / "progress.json"

# Review after 1, 3, 7, 21, 45 days. Past the last step a problem is "mastered".
INTERVALS = [1, 3, 7, 21, 45]
RATINGS = ("easy", "ok", "hard")  # easy = solo & fast, ok = solo with struggle, hard = needed help


def load_problems() -> dict:
    return json.loads(PROBLEMS_PATH.read_text(encoding="utf-8"))


def load_progress() -> dict:
    return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.write_text(json.dumps(progress, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def tz(progress: dict) -> ZoneInfo:
    return ZoneInfo(progress["config"].get("timezone") or "UTC")


def today(progress: dict) -> date:
    return datetime.now(tz(progress)).date()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def next_step(step: int, rating: str) -> int:
    """Step after a solve/review. A first solve starts from step -1."""
    if rating == "hard":
        return 0
    return step + (2 if rating == "easy" else 1)


def due_date(on: date, step: int) -> str | None:
    if step >= len(INTERVALS):
        return None  # mastered
    return (on + timedelta(days=INTERVALS[step])).isoformat()


def record_solve(entry: dict, on: date, rating: str, src: str, rated: bool = True) -> dict:
    step = next_step(-1, rating)
    entry.update(solved=on.isoformat(), src=src, rating=rating, rated=rated,
                 step=step, due=due_date(on, step), updated=now_iso())
    entry.setdefault("reviews", [])
    entry.setdefault("notes", "")
    return entry


def record_review(entry: dict, on: date, rating: str, src: str) -> dict:
    step = next_step(entry.get("step", 0), rating)
    entry.setdefault("reviews", []).append({"d": on.isoformat(), "r": rating, "src": src})
    entry.update(step=step, due=due_date(on, step), updated=now_iso())
    return entry


# ---------------------------------------------------------------- stats ----

def activity(progress: dict) -> dict[str, int]:
    """date -> number of solves + reviews that day."""
    days: dict[str, int] = {}
    for e in progress["problems"].values():
        if e.get("solved"):
            days[e["solved"]] = days.get(e["solved"], 0) + 1
        for r in e.get("reviews", []):
            days[r["d"]] = days.get(r["d"], 0) + 1
    return days


def streaks(days: dict[str, int], ref: date) -> tuple[int, int]:
    """(current, best). Current streak survives until the end of today."""
    active = {date.fromisoformat(d) for d, n in days.items() if n}
    best = run = 0
    prev = None
    for d in sorted(active):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    cur = 0
    d = ref if ref in active else ref - timedelta(days=1)
    while d in active:
        cur += 1
        d -= timedelta(days=1)
    return cur, best


def summary(problems: dict, progress: dict) -> dict:
    ref = today(progress)
    cfg = progress["config"]
    plist = problems["problems"]
    prog = progress["problems"]
    solved = [p for p in plist if prog.get(str(p["id"]), {}).get("solved")]
    total = len(plist)
    days = activity(progress)
    cur, best = streaks(days, ref)
    due = [p for p in solved if (d := prog[str(p["id"])].get("due")) and d <= ref.isoformat()]
    mastered = [p for p in solved if prog[str(p["id"])].get("step", 0) >= len(INTERVALS)]

    start = date.fromisoformat(cfg["start_date"])
    target = date.fromisoformat(cfg["target_date"])
    remaining = total - len(solved)
    days_left = max((target - ref).days + 1, 1)
    elapsed = max((ref - start).days + 1, 1)
    plan_total = max((target - start).days + 1, 1)
    expected = min(total, round(total * elapsed / plan_total))
    pace = len(solved) / elapsed
    projected = (ref + timedelta(days=round(remaining / pace))).isoformat() if pace and remaining else (
        ref.isoformat() if not remaining else None)

    by_topic = []
    for t in problems["topics"]:
        tp = [p for p in plist if p["topic"] == t]
        by_topic.append((t, sum(1 for p in tp if p in solved), len(tp)))

    return dict(total=total, solved=len(solved), remaining=remaining, streak=cur, best=best,
                due=len(due), mastered=len(mastered), expected=expected,
                need_per_day=remaining / days_left, pace=pace, projected=projected,
                days_left=days_left, by_topic=by_topic, days=days, today=ref)
