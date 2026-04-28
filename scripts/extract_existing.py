#!/usr/bin/env python3
"""Extract existing concert data from index.html into JSON."""
import json
import sys
from datetime import datetime
from pathlib import Path

import json5


def extract(html_text: str) -> list[dict]:
    start = html_text.find('const CONCERTS = [')
    if start < 0:
        raise ValueError("CONCERTS array not found")

    bracket_depth = 0
    in_string = False
    string_char = None
    escape = False
    end = None
    for i, c in enumerate(html_text[start:], start):
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
            continue
        if c in ('"', "'"):
            if not in_string:
                in_string = True
                string_char = c
            elif c == string_char:
                in_string = False
                string_char = None
            continue
        if not in_string:
            if c == '[':
                bracket_depth += 1
            elif c == ']':
                bracket_depth -= 1
                if bracket_depth == 0:
                    end = i + 1
                    break

    array_text = html_text[start:end]
    array_text = array_text[len('const CONCERTS = '):]
    concerts = json5.loads(array_text)

    # Normalize source from linkLabel
    for c in concerts:
        label = c.get('linkLabel', '')
        if 'Ticketmelon' in label:
            c['source'] = 'ticketmelon'
        elif 'Thai Ticket Major' in label:
            c['source'] = 'thaiticketmajor'
        elif 'Eventpop' in label:
            c['source'] = 'eventpop'
        elif 'Live Nation' in label:
            c['source'] = 'livenationtero'
        else:
            c['source'] = 'other'

    return concerts


def run():
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("index.html")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/existing_raw.json")

    html_text = in_path.read_text(encoding="utf-8")
    concerts = extract(html_text)

    output = {
        "source": "existing",
        "count": len(concerts),
        "events": concerts,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    sources = {}
    for c in concerts:
        src = c.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1

    print(f"Extracted {len(concerts)} events -> {out_path}")
    print(f"  By source: {sources}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
