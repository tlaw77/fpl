import json
from pathlib import Path

SHIELD_EO = 75.0
NEUTRAL_EO = 40.0


def classify(*, in_my_team, eo_pct, own_pct, my_multiplier):
    if in_my_team:
        if (my_multiplier or 0) <= 0:
            return "bench_differential"
        if eo_pct >= SHIELD_EO:
            return "shield"
        if eo_pct >= NEUTRAL_EO:
            return "neutral"
        if (my_multiplier or 0) >= 2:
            return "aggressive_leverage"
        return "leverage"
    if eo_pct >= SHIELD_EO:
        return "major_danger"
    if eo_pct >= NEUTRAL_EO:
        return "danger"
    if own_pct >= 25:
        return "risk"
    return "differential_against"


def normalize(path: Path):
    data = json.loads(path.read_text())
    changed = 0
    for x in data.get("player_exposure", []):
        new = classify(
            in_my_team=bool(x.get("in_my_team")),
            eo_pct=float(x.get("effective_ownership_pct") or 0),
            own_pct=float(x.get("ownership_pct") or 0),
            my_multiplier=float(x.get("my_multiplier") or 0),
        )
        if x.get("classification") != new:
            x["classification"] = new
            changed += 1
    data["exposure_semantics"] = {
        "version": 2,
        "shield_eo_min": SHIELD_EO,
        "neutral_eo_min": NEUTRAL_EO,
        "leverage_requires_active": True,
        "direct_rival_leverage_is_separate": True,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return changed


def main():
    latest = Path("data/latest.json")
    data = json.loads(latest.read_text())
    gw = data.get("current_gw")
    changed = normalize(latest)
    gw_path = Path(f"data/gw{gw}.json") if gw else None
    if gw_path and gw_path.exists():
        normalize(gw_path)
    print(json.dumps({"status": "SUCCESS", "changed": changed, "version": 2}))


if __name__ == "__main__":
    main()
