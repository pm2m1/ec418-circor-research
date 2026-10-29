"""G3b: one retry of the two Semantic Scholar queries that returned HTTP 429 in scripts/p4_g3b_search.py.

Author decision 2026-10-29: polite backoff (>= 5 s between calls, at most 3 tries per call). Hits are appended to
references/g3b/search_raw.csv (source SemanticScholar, query marked "retry"). If a query is still blocked, the gap is recorded
in references/g3b/search_log.json and later in prisma.md as a limitation (covered by OpenAlex + citation checks).
usage: .venv/bin/python scripts/p4_g3b_s2_retry.py
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

OUT = "references/g3b"
CONTACT = os.environ.get("EC418_CONTACT_EMAIL", "")  # optional polite-pool contact for the APIs; never hard-coded
UA = {"User-Agent": "EC418-G3b-audit/1.0" + (f" (mailto:{CONTACT})" if CONTACT else "")}
QUERIES = ["CirCor murmur", "PhysioNet 2022 murmur"]
today = dt.date.today().isoformat()
rows, status = [], {}
last = 0.0


def call(url):
    global last
    for attempt in range(1, 4):
        time.sleep(max(0.0, 5.0 - (time.time() - last)))
        last = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read()), attempt
        except urllib.error.HTTPError as e:
            if attempt == 3:
                raise
            time.sleep(5 * attempt)


for q in QUERIES:
    n, off = 0, 0
    try:
        while off < 1000:
            d, att = call("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(q) +
                          f"&year=2022-2026&offset={off}&limit=100&fields=title,year,venue,externalIds,url,authors,abstract")
            for p in d.get("data", []):
                rows.append(dict(source="SemanticScholar", query=f"S2 search (retry {today}): {q}; years 2022-2026", date=today,
                                 title=p.get("title") or "", doi=(p.get("externalIds") or {}).get("DOI") or "", url=p.get("url"),
                                 year=p.get("year"), venue=p.get("venue") or "",
                                 authors="; ".join(a["name"] for a in (p.get("authors") or [])[:6]), abstract=p.get("abstract") or ""))
                n += 1
            if "next" not in d:
                break
            off = d["next"]
        status[q] = dict(ok=True, hits=n)
    except urllib.error.HTTPError as e:
        status[q] = dict(ok=False, hits=n, error=f"HTTP {e.code} after 3 tries at offset {off}")
    print(q, status[q])

R = pd.read_csv(f"{OUT}/search_raw.csv")
pd.concat([R, pd.DataFrame(rows)], ignore_index=True).to_csv(f"{OUT}/search_raw.csv", index=False)
log = json.load(open(f"{OUT}/search_log.json"))
log["semantic_scholar_retry"] = dict(date=today, rule=">= 5 s between calls, max 3 tries per call", results=status)
log["total"] = len(R) + len(rows)
json.dump(log, open(f"{OUT}/search_log.json", "w"), indent=2)
print("appended", len(rows), "rows; search_raw total", len(R) + len(rows))
