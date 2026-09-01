import csv
import io
import json
import math
import re
import urllib.request
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
FIXTURE_ODDS_URL = "https://www.football-data.co.uk/matches/resources/fixtures.csv"
OUT = Path("data/market_strength.json")


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-market-strength/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-market-strength/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def n(v):
    try:
        x = float(v)
        return x if math.isfinite(x) and x > 1.0 else None
    except Exception:
        return None


def norm_team(name):
    s = str(name or "").lower()
    s = s.replace("manchester", "man").replace("nottingham", "nottm")
    s = s.replace("wolverhampton wanderers", "wolves")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    stop = {"fc", "afc", "football", "club"}
    return " ".join(x for x in s.split() if x not in stop).strip()


def match_team(raw_name, current_names):
    target = norm_team(raw_name)
    if not target:
        return None, 0.0
    exact = {norm_team(x): x for x in current_names}
    if target in exact:
        return exact[target], 1.0
    best_name = None
    best_score = 0.0
    for name in current_names:
        candidate = norm_team(name)
        score = SequenceMatcher(None, target, candidate).ratio()
        target_tokens = set(target.split())
        candidate_tokens = set(candidate.split())
        if target_tokens and candidate_tokens:
            overlap = len(target_tokens & candidate_tokens) / max(len(target_tokens), len(candidate_tokens))
            score = max(score, overlap)
        if score > best_score:
            best_score = score
            best_name = name
    return (best_name, best_score) if best_score >= 0.64 else (None, best_score)


def first_odds(row, keys):
    for key in keys:
        value = n(row.get(key))
        if value is not None:
            return value, key
    return None, None


def fair_probs(home, draw, away):
    if not all((home, draw, away)):
        return None
    raw = [1.0 / home, 1.0 / draw, 1.0 / away]
    total = sum(raw)
    if total <= 0:
        return None
    return tuple(x / total for x in raw)


def two_way_prob(over, under):
    if not over or not under:
        return None
    ro, ru = 1.0 / over, 1.0 / under
    total = ro + ru
    return ro / total if total > 0 else None


def main():
    bootstrap = fetch_json(f"{BASE}/bootstrap-static/")
    current_teams = [t.get("name") for t in bootstrap.get("teams", []) if t.get("name")]

    raw = fetch_text(FIXTURE_ODDS_URL)
    rows = list(csv.DictReader(io.StringIO(raw)))
    fixtures = []
    unmatched = []

    for row in rows:
        div = str(row.get("Div") or "").strip().upper()
        if div and div != "E0":
            continue
        raw_home = row.get("HomeTeam") or row.get("Home")
        raw_away = row.get("AwayTeam") or row.get("Away")
        if not raw_home or not raw_away:
            continue

        home_team, home_match = match_team(raw_home, current_teams)
        away_team, away_match = match_team(raw_away, current_teams)
        if not home_team or not away_team:
            unmatched.append({
                "home": raw_home,
                "away": raw_away,
                "home_match_score": round(home_match, 3),
                "away_match_score": round(away_match, 3),
            })
            continue

        home_odds, home_source = first_odds(row, ["AvgH", "B365H", "PSH", "MaxH"])
        draw_odds, draw_source = first_odds(row, ["AvgD", "B365D", "PSD", "MaxD"])
        away_odds, away_source = first_odds(row, ["AvgA", "B365A", "PSA", "MaxA"])
        probs = fair_probs(home_odds, draw_odds, away_odds)
        if not probs:
            continue
        ph, pd, pa = probs

        over_odds, over_source = first_odds(row, ["Avg>2.5", "B365>2.5", "P>2.5", "Max>2.5"])
        under_odds, under_source = first_odds(row, ["Avg<2.5", "B365<2.5", "P<2.5", "Max<2.5"])
        p_over25 = two_way_prob(over_odds, under_odds)

        # Independent market signal only. It should calibrate, not dictate, FPL projections.
        home_strength = max(0.90, min(1.10, 1.0 + (ph - pa) * 0.16 + ((p_over25 or 0.5) - 0.5) * 0.06))
        away_strength = max(0.90, min(1.10, 1.0 + (pa - ph) * 0.16 + ((p_over25 or 0.5) - 0.5) * 0.06))

        fixtures.append({
            "date": row.get("Date"),
            "time": row.get("Time"),
            "home_team": home_team,
            "away_team": away_team,
            "raw_home_team": raw_home,
            "raw_away_team": raw_away,
            "team_match_confidence": round(min(home_match, away_match), 3),
            "home_win_prob": round(ph, 4),
            "draw_prob": round(pd, 4),
            "away_win_prob": round(pa, 4),
            "over_2_5_prob": round(p_over25, 4) if p_over25 is not None else None,
            "home_market_strength_modifier": round(home_strength, 4),
            "away_market_strength_modifier": round(away_strength, 4),
            "odds_source_columns": {
                "home": home_source,
                "draw": draw_source,
                "away": away_source,
                "over_2_5": over_source,
                "under_2_5": under_source,
            },
        })

    output = {
        "status": "SUCCESS" if fixtures else "NO_CURRENT_EPL_ODDS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Football-Data.co.uk free latest fixtures CSV",
        "source_url": FIXTURE_ODDS_URL,
        "method": "Overround-normalised 1X2 probabilities with optional over-2.5 context. Bounded modifier is an independent calibration signal, not a standalone player projection.",
        "fixture_count": len(fixtures),
        "unmatched_count": len(unmatched),
        "unmatched": unmatched[:20],
        "fixtures": fixtures,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": output["status"], "fixtures": len(fixtures), "unmatched": len(unmatched)}))


if __name__ == "__main__":
    main()
