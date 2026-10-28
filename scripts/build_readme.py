"""Regenerate README.md and the SVG cards in assets/ from data/*.json."""
from __future__ import annotations

import re
from datetime import date, timedelta
from html import escape
from urllib.parse import quote

import tracker

THEMES = {
    "light": dict(text="#1f2328", muted="#59636e", track="#e6e8eb", accent="#2a78d6",
                  good="#1a7f37", warn="#9a6700",
                  heat=["#ebedf0", "#b7d3f6", "#6da7ec", "#2a78d6", "#184f95"]),
    "dark": dict(text="#e6edf3", muted="#9198a1", track="#2b3138", accent="#3987e5",
                 good="#3fb950", warn="#d29922",
                 heat=["#21262d", "#104281", "#1c5cab", "#3987e5", "#86b6ef"]),
}
FONT = "font-family='-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif'"


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def solution_path(p: dict) -> str:
    return f"solutions/{p['topicNo']:02d}-{slugify(p['topic'])}/{p['id']:03d}-{slugify(p['slug'])}.py"


def stats_svg(s: dict, theme: str) -> str:
    c = THEMES[theme]
    w, rows = 840, s["by_topic"]
    col_w, row_h, top = 400, 22, 166
    h = top + ((len(rows) + 1) // 2) * row_h + 16
    pct = s["solved"] / s["total"]
    r, cx, cy = 46, 70, 74
    circ = 2 * 3.14159265 * r
    on_track = s["solved"] >= s["expected"]
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {FONT}>",
           f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{c['track']}' stroke-width='10'/>",
           f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{c['accent']}' stroke-width='10' stroke-linecap='round'"
           f" stroke-dasharray='{circ * pct:.1f} {circ:.1f}' transform='rotate(-90 {cx} {cy})'/>",
           f"<text x='{cx}' y='{cy + 2}' text-anchor='middle' font-size='22' font-weight='700' fill='{c['text']}'>{round(pct * 100)}%</text>",
           f"<text x='{cx}' y='{cy + 20}' text-anchor='middle' font-size='11' fill='{c['muted']}'>{s['solved']}/{s['total']}</text>"]
    kpis = [("Current streak", f"{s['streak']}d", f"best {s['best']}d"),
            ("Due for revision", str(s["due"]), f"{s['mastered']} mastered"),
            ("Needed pace", f"{s['need_per_day']:.1f}/day", f"{s['days_left']} days to target"),
            ("Plan status", "On track" if on_track else "Behind",
             f"{s['solved']} done vs {s['expected']} planned")]
    for i, (label, val, sub) in enumerate(kpis):
        x = 160 + i * 170
        color = (c["good"] if on_track else c["warn"]) if label == "Plan status" else c["text"]
        out += [f"<text x='{x}' y='52' font-size='12' fill='{c['muted']}'>{label}</text>",
                f"<text x='{x}' y='82' font-size='26' font-weight='700' fill='{color}'>{escape(val)}</text>",
                f"<text x='{x}' y='102' font-size='11' fill='{c['muted']}'>{escape(sub)}</text>"]
    out.append(f"<text x='16' y='{top - 14}' font-size='13' font-weight='600' fill='{c['text']}'>Progress by topic</text>")
    for i, (t, done, n) in enumerate(rows):
        col, row = divmod(i, (len(rows) + 1) // 2)
        x, y = 16 + col * (col_w + 24), top + row * row_h
        bar_x, bar_w = x + 190, col_w - 240
        out += [f"<text x='{x}' y='{y + 12}' font-size='11.5' fill='{c['text']}'>{escape(t)}</text>",
                f"<rect x='{bar_x}' y='{y + 3}' width='{bar_w}' height='10' rx='4' fill='{c['track']}'/>"]
        if done:
            out.append(f"<rect x='{bar_x}' y='{y + 3}' width='{max(bar_w * done / n, 6):.1f}' height='10' rx='4' fill='{c['accent']}'/>")
        out.append(f"<text x='{x + col_w - 4}' y='{y + 12}' text-anchor='end' font-size='11' fill='{c['muted']}'>{done}/{n}</text>")
    out.append("</svg>")
    return "\n".join(out)


def heatmap_svg(days: dict, ref: date, theme: str, weeks: int = 26) -> str:
    c = THEMES[theme]
    cell, gap, left, top = 12, 3, 30, 22
    start = ref - timedelta(days=ref.weekday() + 1 + (weeks - 1) * 7)  # a Sunday
    w, h = left + weeks * (cell + gap) + 10, top + 7 * (cell + gap) + 26
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {FONT}>"]
    for i, lbl in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f"<text x='0' y='{top + i * (cell + gap) + 10}' font-size='9' fill='{c['muted']}'>{lbl}</text>")
    last_month = None
    for wk in range(weeks):
        for dow in range(7):
            d = start + timedelta(days=wk * 7 + dow)
            if d > ref:
                continue
            if dow == 0 and d.month != last_month:
                out.append(f"<text x='{left + wk * (cell + gap)}' y='12' font-size='9' fill='{c['muted']}'>{d:%b}</text>")
                last_month = d.month
            n = days.get(d.isoformat(), 0)
            lvl = 0 if not n else 1 if n == 1 else 2 if n <= 3 else 3 if n <= 5 else 4
            out.append(f"<rect x='{left + wk * (cell + gap)}' y='{top + dow * (cell + gap)}' width='{cell}' height='{cell}'"
                       f" rx='2' fill='{c['heat'][lvl]}'><title>{d:%a %b %d}: {n} solved/revised</title></rect>")
    ly = h - 10
    out.append(f"<text x='{w - 150}' y='{ly + 1}' font-size='9' fill='{c['muted']}'>Less</text>")
    for i, col in enumerate(c["heat"]):
        out.append(f"<rect x='{w - 124 + i * 15}' y='{ly - 9}' width='11' height='11' rx='2' fill='{col}'/>")
    out.append(f"<text x='{w - 45}' y='{ly + 1}' font-size='9' fill='{c['muted']}'>More</text></svg>")
    return "\n".join(out)


def badge(label: str, msg: str, color: str) -> str:
    q = lambda s: quote(s.replace("-", "--").replace("_", "__"))
    return f"![{label}](https://img.shields.io/badge/{q(label)}-{q(msg)}-{color}?style=flat-square)"


def picture(name: str, alt: str) -> str:
    return (f"<picture><source media=\"(prefers-color-scheme: dark)\" srcset=\"assets/{name}-dark.svg\">"
            f"<img alt=\"{alt}\" src=\"assets/{name}-light.svg\"></picture>")


def main() -> None:
    problems, progress = tracker.load_problems(), tracker.load_progress()
    s = tracker.summary(problems, progress)
    for theme in THEMES:
        (tracker.ROOT / "assets" / f"stats-{theme}.svg").write_text(stats_svg(s, theme), encoding="utf-8")
        (tracker.ROOT / "assets" / f"heatmap-{theme}.svg").write_text(heatmap_svg(s["days"], s["today"], theme), encoding="utf-8")

    cfg, prog = progress["config"], progress["problems"]
    owner, _, repo = (cfg.get("github_repo") or "/").partition("/")
    site = f"https://{owner.lower()}.github.io/{repo}/" if owner else "index.html"
    today = s["today"].isoformat()
    on_track = s["solved"] >= s["expected"]

    lines = [
        "# Striver's SDE Sheet in Python",
        "",
        f"**[Open the live dashboard ->]({site})** - check off problems, rate them, take notes, and see what's due for revision today.",
        "",
        " ".join([
            badge("solved", f"{s['solved']}/{s['total']}", "2a78d6"),
            badge("streak", f"{s['streak']} days", "e36209"),
            badge("due for revision", str(s["due"]), "d4a72c" if s["due"] else "8b949e"),
            badge("mastered", str(s["mastered"]), "1a7f37"),
            badge("plan", "on track" if on_track else "behind", "1a7f37" if on_track else "cf222e"),
            badge("target", cfg["target_date"], "8b949e"),
        ]),
        "",
        picture("stats", "Progress overview"),
        "",
        picture("heatmap", "Activity heatmap"),
        "",
        "<sub>Auto-generated by `scripts/build_readme.py`. Don't edit this file by hand; edit progress from the dashboard.</sub>",
        "",
        "**Legend:** ✅ solved · 🔁 due for revision · ⭐ mastered (cleared all 5 revisions) · "
        "🟦 basic · 🟨 core · 🟥 pro (Striver's levels) · E/M/H LeetCode difficulty · `≈` LeetCode equivalent of a non-LeetCode problem · 💲 LeetCode Premium",
        "",
    ]
    level_icon = {"basic": "🟦", "core": "🟨", "pro": "🟥"}
    for t in problems["topics"]:
        tp = [p for p in problems["problems"] if p["topic"] == t]
        done = sum(1 for p in tp if prog.get(str(p["id"]), {}).get("solved"))
        lines += [f"<details{' open' if 0 < done < len(tp) else ''}><summary><b>{escape(t)}</b> - {done}/{len(tp)}</summary>", "",
                  "| # | Problem | Practice | Learn | Lvl | Status | Next review | Code |",
                  "|---|---|---|---|---|---|---|---|"]
        for p in tp:
            e = prog.get(str(p["id"]), {})
            practice = [f"[TUF]({p['tuf']})"]
            if p["lc"]:
                lc = p["lc"]
                practice.insert(0, f"[{'≈ ' if lc['equivalent'] else ''}LC {lc['num']}](https://leetcode.com/problems/{lc['slug']}/)"
                                   f"{' 💲' if lc['paid'] else ''} {lc['diff'][0]}")
            learn = " · ".join(x for x in [f"[▶ video]({p['video']})" if p["video"] else "",
                                           f"[article]({p['article']})" if p["article"] else ""] if x)
            if not e.get("solved"):
                status, review = "", ""
            elif e.get("step", 0) >= len(tracker.INTERVALS):
                status, review = "⭐", "-"
            elif e.get("due") and e["due"] <= today:
                status, review = "🔁", f"**{e['due']}**"
            else:
                status, review = "✅", e.get("due") or ""
            sol = solution_path(p)
            code = f"[py]({sol})" if (tracker.ROOT / sol).exists() else ""
            lines.append(f"| {p['id']} | {escape(p['title'], quote=False).replace('|', '/')} | {' · '.join(practice)} | {learn} | "
                         f"{level_icon.get(p['level'], '')} | {status} | {review} | {code} |")
        lines += ["", "</details>", ""]

    lines += [
        "## How this repo works",
        "",
        "- **Problem list**: `data/problems.json`, pulled from the [official sheet](" + problems["source"] + ") "
        f"({s['total']} problems in {len(problems['topics'])} topics). Every problem links to LeetCode where one exists and to "
        "takeuforward's own practice page, which accepts Python.",
        "- **Progress**: `data/progress.json`. The dashboard commits to it through the GitHub API.",
        "- **LeetCode auto-sync**: a GitHub Action runs `scripts/sync_leetcode.py` every 4 hours. Accepted submissions made "
        f"on or after **{cfg['start_date']}** mark problems solved. Older solves are ignored on purpose because this is a fresh start. "
        "If a problem is due for revision and you solve it again on LeetCode, that counts as the revision.",
        "- **Spaced repetition**: problems come back for revision after 1 → 3 → 7 → 21 → 45 days. *Easy* skips a step, and "
        "*Needed help* sends the problem back to day 1.",
        "- **Solutions**: run `python scripts/new.py <id>` to scaffold `solutions/<topic>/<id>-<slug>.py`.",
        "",
    ]
    (tracker.ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"README built: {s['solved']}/{s['total']} solved, {s['due']} due, streak {s['streak']}")


if __name__ == "__main__":
    main()
