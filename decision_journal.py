import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
ENTRY_ID = 5332809
LATEST = Path("data/latest.json")
REC_HISTORY = Path("data/recommendation_history.json")
OUT = Path("data/decision_history.json")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-decision-journal/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def same_route(rec, transfer):
    rec_out_id = rec.get("out_player_id")
    rec_in_id = rec.get("in_player_id")
    tx_out_id = transfer.get("element_out")
    tx_in_id = transfer.get("element_in")
    if rec_in_id is not None and tx_in_id is not None and int(rec_in_id) != int(tx_in_id):
        return False
    if rec_out_id is not None and tx_out_id is not None and int(rec_out_id) != int(tx_out_id):
        return False
    rec_out = str(rec.get("out") or "").strip().casefold()
    rec_in = str(rec.get("in") or "").strip().casefold()
    tx_out = str(transfer.get("out_name") or "").strip().casefold()
    tx_in = str(transfer.get("in_name") or "").strip().casefold()
    return bool(rec_out and rec_in and rec_out == tx_out and rec_in == tx_in)


def lens_context(rec, lens):
    return {
        "type": lens,
        "label": "Lower variance" if lens == "lower_variance" else "Leverage",
        "model_uplift": rec.get("gain"),
        "target_rival_ownership_pct": rec.get("target_rival_ownership_pct"),
        "next3": rec.get("next3") or [],
        "rationale": rec.get("rationale") or [],
    }


def recommendation_context(transfer, rec_history):
    event = int(transfer.get("event") or 0)
    tx_time = parse_dt(transfer.get("time"))
    matches = []
    for snap in rec_history.get("snapshots", []):
        if int(snap.get("next_gw") or 0) != event:
            continue
        captured = parse_dt(snap.get("captured_at_utc"))
        if tx_time and captured and captured > tx_time:
            continue
        lenses = []
        for lens, field in (("lower_variance", "lower_variance"), ("variety", "variety")):
            exact = next((r for r in snap.get(field, []) if same_route(r, transfer)), None)
            if exact:
                lenses.append(lens_context(exact, lens))
        if lenses:
            matches.append((captured or datetime.min.replace(tzinfo=timezone.utc), snap, lenses))
    if not matches:
        return None
    _, snap, lenses = sorted(matches, key=lambda x: x[0])[-1]
    return {
        "matched": True,
        "match_type": "exact_route",
        "snapshot_at_utc": snap.get("captured_at_utc"),
        "strategy": snap.get("strategy"),
        "team_rank_at_snapshot": snap.get("team_rank"),
        "bank_at_snapshot": snap.get("bank"),
        "lenses": lenses,
    }


def main():
    latest = json.loads(LATEST.read_text())
    rec_history = json.loads(REC_HISTORY.read_text()) if REC_HISTORY.exists() else {"snapshots": []}
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
        transfer = {
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
        }
        transfer["recommendation_context"] = recommendation_context(transfer, rec_history)
        by_event[int(t.get("event") or 0)].append(transfer)

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
        "version": 4,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "entry_id": ENTRY_ID,
        "current_gw": current_gw,
        "weeks": weeks,
        "decisions": flat,
        "recommendation_evidence": "Exact pre-transfer route matches only; no rationale is invented for unmatched decisions.",
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    matched = sum(1 for t in flat if t.get("recommendation_context"))
    print(json.dumps({"status": "SUCCESS", "weeks": len(weeks), "transfers": len(flat), "matched_recommendations": matched}))


if __name__ == "__main__":
    main()
