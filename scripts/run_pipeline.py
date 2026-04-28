#!/usr/bin/env python3
"""Orchestrate scraping and rebuild data files."""
import subprocess
import sys

SCRIPTS = [
    ("scripts/scrape_lnt.py", "data/lnt_raw.json"),
    ("scripts/scrape_ttm.py", "data/ttm_raw.json"),
]

def run():
    print("=" * 50)
    print("Live/BKK Pipeline")
    print("=" * 50)

    for script, out in SCRIPTS:
        print(f"\n-> {script}")
        r = subprocess.run([sys.executable, script, out], capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            print(f"ERROR: {r.stderr}")

    print("\n-> scripts/merge.py")
    r = subprocess.run([sys.executable, "scripts/merge.py"])
    if r.returncode != 0:
        print("ERROR: Merge failed")
        return 1

    print("\nDone!")
    return 0

if __name__ == "__main__":
    sys.exit(run())
