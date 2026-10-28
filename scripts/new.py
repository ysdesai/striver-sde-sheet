"""Scaffold a Python solution file for a sheet problem.

    python scripts/new.py 37          # by sheet number
    python scripts/new.py two-sum     # by slug (takeuforward or LeetCode)
"""
from __future__ import annotations

import sys

import tracker
from build_readme import solution_path

TEMPLATE = '''"""
#{id} {title}  ({topic})

Practice : {practice}
Video    : {video}
Article  : {article}

Approach
--------
Brute force:
Better:
Optimal:

Complexity: time O(?), space O(?)
Key insight:
Mistakes I made:
"""
from typing import List, Optional


class Solution:
    pass


if __name__ == "__main__":
    s = Solution()
'''


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    arg = sys.argv[1]
    plist = tracker.load_problems()["problems"]
    match = [p for p in plist if str(p["id"]) == arg or p["slug"] == arg or (p["lc"] and p["lc"]["slug"] == arg)]
    if not match:
        print(f"No problem matches {arg!r}")
        return 1
    p = match[0]
    path = tracker.ROOT / solution_path(p)
    if path.exists():
        print(f"Already exists: {path.relative_to(tracker.ROOT)}")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    practice = f"https://leetcode.com/problems/{p['lc']['slug']}/" if p["lc"] else p["tuf"]
    path.write_text(TEMPLATE.format(id=p["id"], title=p["title"], topic=p["topic"], practice=practice,
                                    video=p["video"] or "-", article=p["article"] or "-"), encoding="utf-8")
    print(f"Created {path.relative_to(tracker.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
