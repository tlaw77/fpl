import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
ENTRY_ID = 5332809
LATEST = Path("data/latest.json")
OUT = Path("data/decision_history.json")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-decision-journal/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main():
    latest = json.loads(LATEST.read_text())
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    transfers = get_json(f"{BASE}/entry/{ENTRY_ID}/transfers/")
    players = {p["id"]: p["web_name"] for p in bootstrap["elements"]}
    current_gw = int(latest.get("current_gw") or 0)

    by_event = defaultdict(list)
    seen = set()
    for t in sorted(transfers, key=lambda x: (x.get("event") or 0, x.get("time") or "")):
        key = (t.get("event"), t.get("element_out"), t.get("element_in"), t.get("time"))
        if key in seen:
            continue
        seen.add(key)
        by_event[int(t.get("event") or 0)].append({
            "event": t.get("event"),
            "time": t.get("time"),
            "element_out": t.get("element_out"),
            "out_name": players.get(t.get("element_out")),
            "element_in": t.get("element_in"),
            "in_name": players.get(t.get("element_in")),
            "out_cost": t.get("element_out_cost") / 10 if t.get("element_out_cost") is not None else None,
            "in_cost": t.get("element_in_cost") / 10 if t.get("element_in_cost") is not None else None,
            "source": "official_transfer_history",
            "status": "confirmed",
        })

    weeks = []
    for gw in range(1, current_gw + 1):
        try:
            picks = get_json(f"{BASE}/entry/{ENTRY_ID}/event/{gw}/picks/")
        except Exception:
            picks = {}
        rows = picks.get("picks") or []
        captain = next((p for p in rows if p.get("is_captain")), None)
        vice = next((p for p in rows if p.get("is_vice_captain")), None)
        weeks.append({
            "event": gw,
            "captain_id": captain.get("element") if captain else None,
            "captain_name": players.get(captain.get("element")) if captain else None,
            "vice_id": vice.get("element") if vice else None,
            "vice_name": players.get(vice.get("element")) if vice else None,
            "active_chip": picks.get("active_chip"),
            "transfers": by_event.get(gw, []),
            "source": "official_fpl_history",
        })

    # Preserve transfer-only events not yet represented in picks history.
    represented = {w["event"] for w in weeks}
    for gw in sorted(k for k in by_event if k and k not in represented):
        weeks.append({
            "event": gw,
            "captain_id": None,
            "captain_name": None,
            "vice_id": None,
            "vice_name": None,
            "active_chip": None,
            "transfers": by_event[gw],
            "source": "official_transfer_history",
        })

    weeks.sort(key=lambda x: x["event"])
    flat = [t for w in weeks for t in w.get("transfers", [])]
    out = {
        "version": 3,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "entry_id": ENTRY_ID,
        "current_gw": current_gw,
        "weeks": weeks,
        "decisions": flat,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "SUCCESS", "weeks": len(weeks), "transfers": len(flat)}))


if __name__ == "__main__":
    main()
