#!/usr/bin/env python3
import json
from collections import defaultdict

INPUT_FILE  = "2023-11-05_oasst2_all.messages.jsonl"
OUTPUT_FILE = "humor_en_with_context.jsonl"
HUMOR_MIN   = 0.75

def best_child(children, want_opposite_role=None):
    def score(msg):
        rr = 1 if msg.get("review_result") else 0
        rc = msg.get("review_count") or 0
        rank = msg.get("rank", 999)
        return (rr, rc, -int(rank if isinstance(rank, int) else 999))

    pool = children
    if want_opposite_role is not None:
        opp = [m for m in children if m.get("role") == want_opposite_role]
        if opp:
            pool = opp
    if not pool:
        return None
    return sorted(pool, key=score, reverse=True)[0]

def is_en_humorous(msg, threshold=HUMOR_MIN):
    if msg.get("lang") != "en":
        return False
    labels = msg.get("labels") or {}
    humor = labels.get("humor") or {}
    val = humor.get("value")
    return isinstance(val, (int, float)) and val >= threshold

def main():
    messages = []
    by_id = {}
    children = defaultdict(list)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            messages.append(m)
            mid = m.get("message_id")
            if mid:
                by_id[mid] = m

    for m in messages:
        pid = m.get("parent_id")
        if pid and pid in by_id:
            children[pid].append(m)

    include_ids = set()
    matches = []

    for m in messages:
        if is_en_humorous(m):
            matches.append(m)
            mid = m.get("message_id")
            if mid:
                include_ids.add(mid)

            # Always include parent if exists
            pid = m.get("parent_id")
            if pid and pid in by_id:
                include_ids.add(pid)

            # Always include one best child
            role = m.get("role")
            opp_role = "assistant" if role == "user" else "user" if role == "assistant" else None
            nxt = best_child(children.get(mid, []), want_opposite_role=opp_role)
            if nxt and nxt.get("message_id"):
                include_ids.add(nxt["message_id"])
                # 🔑 NEW: also include the parent (i.e. m) if child is humorous
                if is_en_humorous(nxt):
                    pid2 = nxt.get("parent_id")
                    if pid2 and pid2 in by_id:
                        include_ids.add(pid2)

    written = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for m in messages:
            if m.get("message_id") in include_ids:
                out.write(json.dumps(m, ensure_ascii=False) + "\n")
                written += 1

    print(f"✅ Found {len(matches)} EN messages with humor >= {HUMOR_MIN}.")
    print(f"🧩 Wrote {written} lines (matches + parents/children) to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

