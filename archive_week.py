import argparse
import hashlib
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
RAW_REPO = "https://raw.githubusercontent.com/tlaw77/fpl"
DATA = Path("data")
HISTORY = DATA / "history"

ARCHIVE_FILES = {
    "dashboard_snapshot.json": "latest.json",
    "strategy.json": "strategy.json",
    "market.json": "market.json",
    "squad_intelligence.json": "squad_intelligence.json",
    "chip_window.json": "chip_window.json",
    "schedule_load.json": "schedule_load.json",
    "player_pool.json": "player_pool.json",
    "scout_consensus.json": "scout_consensus.json",
    "decision_history.json": "decision_history.json",
    "recommendation_history.json": "recommendation_history.json",
    "budget_state.json": "budget_state.json",
    "simulation.json": "simulation.json",
    "path_simulation.json": "path_simulation.json",
    "adaptive_rival_simulation.json": "adaptive_rival_simulation.json",
    "chip_path_simulation.json": "chip_path_simulation.json",
    "full_squad_chip_optimizer.json": "full_squad_chip_optimizer.json",
    "decision_synthesis.json": "decision_synthesis.json",
    "simulation_stability.json": "simulation_stability.json",
    "chip_activation_gate.json": "chip_activation_gate.json",
}

# One-time recovery refs for gameweeks that had already rolled before durable
# archival was introduced. These refs are immutable historical ETL commits.
BACKFILL_REFS = {
    1: "73e217cb2a010e4706ae570c64e8005039f0a6b4",
}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-history-archive/1.2"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-history-archive/1.2"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def detect_api_gw():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    events = bootstrap.get("events", [])
    current = next((e for e in events if e.get("is_current")), None)
    if current:
        return int(current["id"])
    nxt = next((e for e in events if e.get("is_next")), None)
    if nxt:
        return max(1, int(nxt["id"]) - 1)
    finished = [int(e["id"]) for e in events if e.get("finished")]
    return max(finished) if finished else 1


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_manifest(gw, target, copied, reason, source_ref=None):
    manifest = {
        "version": 1,
        "gw": gw,
        "finalized": True,
        "archive_reason": reason,
        "source_ref": source_ref,
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(copied)
        ],
    }
    write_json(target / "manifest.json", manifest)
    return manifest


def archive_gw(gw, reason, force=False):
    target = HISTORY / f"gw{gw}"
    manifest_path = target / "manifest.json"
    if manifest_path.exists() and not force:
        return {"status": "SKIPPED", "gw": gw, "reason": "already_finalized", "path": str(target)}

    target.mkdir(parents=True, exist_ok=True)
    copied = []
    raw_gw = DATA / f"gw{gw}.json"
    if raw_gw.exists():
        dest = target / "league_snapshot.json"
        shutil.copy2(raw_gw, dest)
        copied.append(dest)

    for dest_name, source_name in ARCHIVE_FILES.items():
        src = DATA / source_name
        if not src.exists():
            continue
        dest = target / dest_name
        shutil.copy2(src, dest)
        copied.append(dest)

    write_manifest(gw, target, copied, reason)
    update_index()
    return {"status": "ARCHIVED", "gw": gw, "files": len(copied), "path": str(target)}


def archive_from_ref(gw, ref, force=False):
    target = HISTORY / f"gw{gw}"
    manifest_path = target / "manifest.json"
    if manifest_path.exists() and not force:
        return {"status": "SKIPPED", "gw": gw, "reason": "already_finalized", "path": str(target)}

    target.mkdir(parents=True, exist_ok=True)
    copied = []
    sources = {"league_snapshot.json": f"gw{gw}.json", **ARCHIVE_FILES}
    optional_historical = {
        "schedule_load.json", "budget_state.json", "simulation.json", "path_simulation.json",
        "adaptive_rival_simulation.json", "chip_path_simulation.json", "full_squad_chip_optimizer.json",
        "decision_synthesis.json", "simulation_stability.json", "chip_activation_gate.json",
    }
    for dest_name, source_name in sources.items():
        try:
            body = get_bytes(f"{RAW_REPO}/{ref}/data/{source_name}")
        except Exception as exc:
            # Older historical refs legitimately pre-date later decision-support layers.
            if dest_name in optional_historical:
                continue
            raise RuntimeError(f"Cannot backfill GW{gw}: {source_name} unavailable at {ref}: {exc}") from exc
        dest = target / dest_name
        dest.write_bytes(body)
        copied.append(dest)

    league = json.loads((target / "league_snapshot.json").read_text(encoding="utf-8"))
    dashboard = json.loads((target / "dashboard_snapshot.json").read_text(encoding="utf-8"))
    if int(league.get("current_gw") or 0) != gw or int(dashboard.get("current_gw") or 0) != gw:
        raise RuntimeError(f"Backfill ref {ref} does not represent GW{gw}")

    write_manifest(gw, target, copied, "historical_ref_backfill", source_ref=ref)
    update_index()
    return {"status": "BACKFILLED", "gw": gw, "files": len(copied), "path": str(target), "source_ref": ref}


def backfill_missing_before(current_gw):
    results = []
    for gw in range(1, max(1, int(current_gw))):
        if (HISTORY / f"gw{gw}" / "manifest.json").exists():
            continue
        ref = BACKFILL_REFS.get(gw)
        if not ref:
            results.append({"status": "MISSING", "gw": gw, "reason": "no_backfill_ref"})
            continue
        results.append(archive_from_ref(gw, ref))
    return results


def update_index(current_live_gw=None):
    HISTORY.mkdir(parents=True, exist_ok=True)
    weeks = []
    for d in sorted(HISTORY.glob("gw*"), key=lambda p: int(p.name[2:]) if p.name[2:].isdigit() else 999):
        manifest = d / "manifest.json"
        if not manifest.exists():
            continue
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        weeks.append({
            "gw": m.get("gw"),
            "archived_at_utc": m.get("archived_at_utc"),
            "files": len(m.get("files", [])),
            "source_ref": m.get("source_ref"),
        })
    payload = {
        "version": 1,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_live_gw": current_live_gw,
        "finalized_gameweeks": weeks,
    }
    write_json(HISTORY / "index.json", payload)


def finalize_if_advanced(force=False):
    latest_path = DATA / "latest.json"
    if not latest_path.exists():
        return {"status": "SKIPPED", "reason": "latest_missing"}
    stored = json.loads(latest_path.read_text(encoding="utf-8"))
    stored_gw = int(stored.get("current_gw") or 0)
    api_gw = detect_api_gw()

    backfills = backfill_missing_before(stored_gw)
    if stored_gw and api_gw > stored_gw:
        result = archive_gw(stored_gw, f"api_advanced_to_gw{api_gw}", force=force)
        update_index(current_live_gw=api_gw)
        result["api_gw"] = api_gw
        result["backfills"] = backfills
        return result
    update_index(current_live_gw=api_gw)
    return {"status": "SKIPPED", "reason": "no_gameweek_advance", "stored_gw": stored_gw, "api_gw": api_gw, "backfills": backfills}


def main():
    parser = argparse.ArgumentParser(description="Finalize durable FPL gameweek history before live files roll forward.")
    parser.add_argument("--gw", type=int, help="Archive a specific gameweek from the current data files.")
    parser.add_argument("--ref", help="Backfill --gw from an immutable Git ref instead of current files.")
    parser.add_argument("--force", action="store_true", help="Replace an existing finalized archive.")
    args = parser.parse_args()

    if args.gw and args.ref:
        result = archive_from_ref(args.gw, args.ref, force=args.force)
    elif args.gw:
        result = archive_gw(args.gw, "manual", force=args.force)
    else:
        result = finalize_if_advanced(force=args.force)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
