import html
import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_ID = 582464
MY_ENTRY_ID = 5332809
BASE = "https://fantasy.premierleague.com/api"
SCOUT_URLS = [
    "https://www.fantasyfootballscout.co.uk/category/chip-strategy/",
    "https://www.fantasyfootballscout.co.uk/tag/blank-gameweeks/",
    "https://www.fantasyfootballscout.co.uk/category/scout-reports/scouting-the-doubles/",
]
SCOUT_MIN_DATE = (2026, 7, 1)
CHIPS = ["wildcard", "freehit", "3xc", "bboost"]
CHIP_LABELS = {"wildcard": "Wildcard", "freehit": "Free Hit", "3xc": "Triple Captain", "bboost": "Bench Boost"}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-strategy-watch/1.1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def get_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 fpl-strategy-watch/1.1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def current_gw(events):
    cur = next((e for e in events if e.get("is_current")), None)
    if cur:
        return cur["id"]
    nxt = next((e for e in events if e.get("is_next")), None)
    if nxt:
        return max(1, nxt["id"] - 1)
    done = [e["id"] for e in events if e.get("finished")]
    return max(done) if done else 1


def standings_all():
    rows, page = [], 1
    while True:
        data = get_json(f"{BASE}/leagues-classic/{LEAGUE_ID}/standings/?page_standings={page}")
        s = data.get("standings", {})
        rows.extend(s.get("results", []))
        if not s.get("has_next"):
            return rows
        page += 1


def chip_inventory(chips, gw):
    half = 1 if gw <= 19 else 2
    lo, hi = (1, 19) if half == 1 else (20, 38)
    used_this_half = [c for c in chips if lo <= (c.get("event") or 0) <= hi]
    used_names = [c.get("name") for c in used_this_half]
    remaining = [c for c in CHIPS if c not in used_names]
    return {
        "half": half,
        "window": f"GW{lo}-GW{hi}",
        "used_this_half": [{"chip": CHIP_LABELS.get(c.get("name"), c.get("name")), "gw": c.get("event")} for c in used_this_half],
        "remaining_this_half": [CHIP_LABELS[x] for x in remaining],
        "used_count": len(used_this_half),
        "remaining_count": len(remaining),
    }


def fixture_schedule(fixtures, teams, gw):
    per_gw = defaultdict(Counter)
    unassigned = []
    for f in fixtures:
        event = f.get("event")
        h, a = f.get("team_h"), f.get("team_a")
        if event is None:
            unassigned.append({"home": teams.get(h, str(h)), "away": teams.get(a, str(a)), "kickoff_time": f.get("kickoff_time")})
            continue
        per_gw[event][h] += 1
        per_gw[event][a] += 1

    upcoming = []
    for event in range(max(1, gw + 1), 39):
        counts = per_gw[event]
        blanks = [teams[t] for t in teams if counts[t] == 0]
        doubles = [teams[t] for t in teams if counts[t] > 1]
        if blanks or doubles:
            upcoming.append({"gw": event, "blank_teams": sorted(blanks), "double_teams": sorted(doubles), "status": "confirmed_from_fpl_fixture_assignment"})
    return upcoming, unassigned


def url_date(href):
    m = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", href)
    return tuple(map(int, m.groups())) if m else None


def scout_watch():
    keywords = re.compile(r"blank|double|postpon|reschedul|cup|chip strategy|wildcard|bench boost|triple captain|free hit", re.I)
    items, errors, seen = [], [], set()
    for source in SCOUT_URLS:
        try:
            text = get_text(source)
            for href, title in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
                clean = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title))).strip()
                d = url_date(href)
                if not href.startswith("http") or not d or d < SCOUT_MIN_DATE:
                    continue
                if len(clean) < 15 or not keywords.search(clean):
                    continue
                key = href
                if key in seen:
                    continue
                seen.add(key)
                items.append({"title": clean[:220], "url": href, "published": f"{d[0]:04d}-{d[1]:02d}-{d[2]:02d}", "source": source})
        except Exception as exc:
            errors.append({"source": source, "error": str(exc)[:200]})
    items.sort(key=lambda x: x["published"], reverse=True)
    return {"items": items[:20], "errors": errors, "source_count": len(SCOUT_URLS), "current_season_only": True, "status": "ok" if items else "no_items"}


def chip_adjusted_context(gw, managers):
    path = Path("data/latest.json")
    if not path.exists():
        return []
    latest = json.loads(path.read_text(encoding="utf-8"))
    teams = [{**latest.get("me", {}), "picks": latest.get("squad", [])}] + latest.get("rivals", [])
    by_id = {x.get("entry_id"): x for x in teams}
    output = []
    for m in managers:
        used_now = next((x for x in m.get("chip_history", []) if x.get("gw") == gw), None)
        if not used_now:
            continue
        live = by_id.get(m["entry_id"], {})
        chip = used_now["chip"]
        gain = None
        note = "Chip used this Gameweek; raw points are not directly comparable with a no-chip team."
        if chip == "Bench Boost":
            gain = live.get("points_on_bench")
            note = "Bench Boost points inflate the raw Gameweek score; avoid chasing squad structure based only on this week."
        elif chip == "Triple Captain":
            captain = next((p for p in live.get("picks", []) if p.get("captain")), None)
            if captain:
                gain = captain.get("live_points")
            note = "Triple Captain adds one extra captain score above normal captaincy; treat that portion as chip-driven rather than structural edge."
        elif chip == "Wildcard":
            note = "Wildcard is a structural reset. Watch the new squad for durable template shifts rather than reacting to one-week points."
        elif chip == "Free Hit":
            note = "Free Hit is temporary. Do not copy this squad structure into permanent transfers."
        output.append({
            "entry_id": m["entry_id"], "manager": m["manager"], "team_name": m["team_name"], "chip": chip,
            "gw_points": live.get("gw_points"), "estimated_chip_gain": gain,
            "estimated_no_chip_points": (live.get("gw_points") - gain) if gain is not None and live.get("gw_points") is not None else None,
            "note": note,
        })
    return output


def main():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    gw = current_gw(bootstrap.get("events", []))
    teams = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
    standings = standings_all()

    managers = []
    for row in standings:
        entry_id = row["entry"]
        hist = get_json(f"{BASE}/entry/{entry_id}/history/")
        chips = hist.get("chips", []) or []
        managers.append({
            "entry_id": entry_id, "manager": row.get("player_name"), "team_name": row.get("entry_name"), "rank": row.get("rank"),
            "total_points": row.get("total"),
            "chip_history": [{"chip": CHIP_LABELS.get(c.get("name"), c.get("name")), "gw": c.get("event")} for c in chips],
            "inventory": chip_inventory(chips, gw),
        })

    me = next(x for x in managers if x["entry_id"] == MY_ENTRY_ID)
    target_rivals = sorted([x for x in managers if x["entry_id"] != MY_ENTRY_ID and (x.get("total_points") or 0) > (me.get("total_points") or 0)], key=lambda x: (x.get("total_points") or 0) - (me.get("total_points") or 0))[:3]

    my_remaining = set(me["inventory"]["remaining_this_half"])
    for m in managers:
        rem = set(m["inventory"]["remaining_this_half"])
        m["chip_edge_vs_me"] = {"my_extra_chips": sorted(my_remaining - rem), "their_extra_chips": sorted(rem - my_remaining), "net_remaining_delta": len(my_remaining) - len(rem)}

    fixtures = get_json(f"{BASE}/fixtures/")
    schedule_events, unassigned = fixture_schedule(fixtures, teams, gw)

    strategic_notes = []
    for r in target_rivals:
        edge = next(m for m in managers if m["entry_id"] == r["entry_id"])["chip_edge_vs_me"]
        if edge["my_extra_chips"]:
            strategic_notes.append({"manager": r["manager"], "team_name": r["team_name"], "note": f"You retain {', '.join(edge['my_extra_chips'])} that this rival has already spent in the current half. Preserve flexibility rather than copying short-term moves blindly."})
        if edge["their_extra_chips"]:
            strategic_notes.append({"manager": r["manager"], "team_name": r["team_name"], "note": f"This rival retains {', '.join(edge['their_extra_chips'])} that you have already spent. Expect a future chip-driven swing and favour squad flexibility."})

    result = {
        "status": "SUCCESS", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "current_gw": gw,
        "chip_rules": {"two_sets": True, "first_half": "GW1-GW19", "second_half": "GW20-GW38", "chips_per_half": ["Wildcard", "Free Hit", "Triple Captain", "Bench Boost"]},
        "me": me, "target_rivals": target_rivals, "managers": managers,
        "current_gw_chip_context": chip_adjusted_context(gw, managers),
        "confirmed_blank_double_events": schedule_events, "unassigned_fixtures": unassigned,
        "scout_watch": scout_watch(), "strategic_notes": strategic_notes,
    }

    out = Path("data/strategy.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "SUCCESS", "gw": gw, "managers": len(managers), "schedule_events": len(schedule_events), "unassigned": len(unassigned), "scout_items": len(result["scout_watch"]["items"]), "chip_context": len(result["current_gw_chip_context"])}))


if __name__ == "__main__":
    main()
