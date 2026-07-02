#!/usr/bin/env python3
"""Orchestrate scraping and rebuild data files."""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS = [
    ("scripts/scrape_lnt.py", "data/lnt_raw.json"),
    ("scripts/scrape_ttm.py", "data/ttm_raw.json"),
    ("scripts/scrape_ticketmelon.py", "data/ticketmelon_raw.json"),
    ("scripts/scrape_eventpop.py", "data/eventpop_raw.json"),
    ("scripts/scrape_allevents.py", "data/allevents_raw.json"),
]


def run():
    print("=" * 60)
    print(f"Live/BKK Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    health = {}
    for script, out in SCRIPTS:
        print(f"\n-> {script}")
        r = subprocess.run([sys.executable, script, out], capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            print(f"ERROR: {r.stderr}")
            health[script] = {"status": "error", "error": r.stderr[:200]}
        else:
            # Count events in output file
            try:
                import json
                with open(out) as f:
                    data = json.load(f)
                count = data.get("count", 0)
                health[script] = {"status": "ok", "events": count}
            except:
                health[script] = {"status": "ok", "events": "?"}

    print("\n-> scripts/merge.py")
    r = subprocess.run([sys.executable, "scripts/merge.py"], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr}")
        health["merge"] = {"status": "error"}
        return 1
    health["merge"] = {"status": "ok"}

    # Write health report
    health_report = {
        "runAt": datetime.now().isoformat(),
        "sources": health,
    }
    with open("data/health.json", "w", encoding="utf-8") as f:
        json.dump(health_report, f, ensure_ascii=False, indent=2)

    print("\nDone!")
    print(f"Health report: data/health.json")
    return 0


if __name__ == "__main__":
    sys.exit(run())
