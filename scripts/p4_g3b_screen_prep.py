"""G3b literature audit, step 1c: merge the manual Google Scholar export into the raw hits and deduplicate (protocol §1-2).

1. Google Scholar ranks 1-100 (references/g3b/scholar_manual.csv; ranks 101-140 are kept but NOT screened, per the locked
   "first 100") carry no URL/DOI (not visible in the screenshots). Each record is resolved by title match: OpenAlex
   title.search, then Crossref query.bibliographic as fallback. A match needs normalised-title similarity >= 0.90 (or, for a
   title truncated by Scholar with "…", the full title starting with the shown prefix) and |year difference| <= 1 when Scholar
   shows a year. Matches are marked "resolved by title match (OpenAlex|Crossref, sim=...)"; the rest are kept unresolved.
   Result: references/g3b/scholar_resolved.csv; the rows are appended once to references/g3b/search_raw.csv (source
   GoogleScholar), and the method is recorded in references/g3b/search_log.json.
2. Deduplication: by DOI (case-insensitive), then by normalised title. When a work exists as preprint and journal/proceedings
   version, the journal/proceedings version is kept and the preprint is linked (`linked_versions`). Preprint = DOI prefix
   10.48550 (arXiv), 10.1101 (medRxiv/bioRxiv), 10.2139 (SSRN), 10.21203 (Research Square), 10.36227 (TechRxiv), 10.5281
   (Zenodo), 10.20944 (Preprints.org), or an arXiv/medRxiv venue.
   Result: references/g3b/dedup.csv (one row per unique work, with every source that found it).
usage: .venv/bin/python scripts/p4_g3b_screen_prep.py
"""
import datetime as dt
import difflib
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

OUT = "references/g3b"
CONTACT = os.environ.get("EC418_CONTACT_EMAIL", "")  # optional polite-pool contact for the APIs; never hard-coded
UA = {"User-Agent": "EC418-G3b-audit/1.0" + (f" (mailto:{CONTACT})" if CONTACT else "")}
PREPRINT_DOI = ("10.48550/", "10.1101/", "10.2139/", "10.21203/", "10.36227/", "10.5281/", "10.20944/")
SCHOLAR_METHOD = dict(
    method="manual Google Scholar export as 14 screenshots (no HTML, no Publish or Perish)",
    query='("CirCor" OR "PhysioNet 2022" OR "PhysioNet Challenge 2022" OR "George B. Moody PhysioNet Challenge 2022") AND murmur',
    date="2026-10-29", range="custom range 2022-2026", order="relevance", per_page=20,
    pages_captured=7, approx_total_hits="about 474",
    transcription="ranks 1-100 transcribed from the screenshots by Claude (cloud workspace) into scholar_manual.csv; "
                  "checked against the PNGs, 0 errors (scholar_transcription_check.md)",
    screened="ranks 1-100 (locked protocol: first 100); ranks 101-140 kept in scholar_manual_extra_rank101-140.csv, NOT screened",
    resolution="DOI/URL resolved by title match via OpenAlex, Crossref fallback (scripts/p4_g3b_screen_prep.py)")


def norm(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def get(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and int(e.headers.get("retry-after") or 0) > 300:
                raise  # daily budget exhausted (OpenAlex): do not wait, fall back to Crossref
            if i == tries - 1:
                raise
            time.sleep(15 * (i + 1))
        except (urllib.error.URLError, TimeoutError):
            if i == tries - 1:
                raise
            time.sleep(15 * (i + 1))


def match(shown, cand, year, cyear):
    a, b = norm(shown.rstrip("…").rstrip(".")), norm(cand)
    trunc = str(shown).rstrip().endswith("…")
    sim = difflib.SequenceMatcher(None, a, b).ratio()
    ok = (b.startswith(a) and len(a) >= 25) if trunc else sim >= 0.90
    if ok and pd.notna(year) and cyear is not None and abs(int(year) - int(cyear)) > 1:
        ok = False
    return ok, (1.0 if trunc and ok else sim)


OPENALEX_DOWN = []  # ranks for which OpenAlex returned 429 (daily budget exhausted) -> Crossref only


def tiebreak(row, sim, cyear, cvenue):
    """Several versions can share one title (preprint, proceedings, journal): prefer the one whose venue starts with the
    venue Scholar shows and whose year equals Scholar's year, then the higher title similarity."""
    v = norm(str(row.venue).split("…")[0])
    vm = bool(v) and norm(cvenue).startswith(v)
    ym = pd.notna(row.year) and cyear is not None and int(row.year) == int(cyear)
    return (vm, ym, sim)


def resolve(row):
    q = str(row.title).rstrip("…")
    try:
        d = get("https://api.openalex.org/works?per-page=10&filter=title.search:" + urllib.parse.quote(re.sub(r"[,:|]", " ", q)) +
                (f"&mailto={CONTACT}" if CONTACT else ""))
    except urllib.error.HTTPError as e:
        if e.code != 429:
            raise
        OPENALEX_DOWN.append(int(row["rank"]))
        d = {}
    best = None
    for w in d.get("results", []):
        ok, sim = match(row.title, w.get("display_name") or "", row.year, w.get("publication_year"))
        loc = (w.get("primary_location") or {}).get("source") or {}
        tb = tiebreak(row, sim, w.get("publication_year"), loc.get("display_name") or "")
        if ok and (best is None or tb > best[3]):
            best = (sim, "OpenAlex", dict(r_title=w.get("display_name"), doi=(w.get("doi") or "").replace("https://doi.org/", ""),
                                          url=w.get("id"), r_year=w.get("publication_year"), r_venue=loc.get("display_name") or "",
                                          r_authors="; ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:6]),
                                          abstract=inv(w.get("abstract_inverted_index"))), tb)
    if best is None:
        d = get("https://api.crossref.org/works?rows=10&query.bibliographic=" + urllib.parse.quote(q) +
                (f"&mailto={CONTACT}" if CONTACT else ""))
        for w in d.get("message", {}).get("items", []):
            t = (w.get("title") or [""])[0]
            y = ((w.get("issued") or {}).get("date-parts") or [[None]])[0][0]
            ok, sim = match(row.title, t, row.year, y)
            tb = tiebreak(row, sim, y, (w.get("container-title") or [""])[0])
            if ok and (best is None or tb > best[3]):
                best = (sim, "Crossref", dict(r_title=t, doi=w.get("DOI", ""), url="https://doi.org/" + w.get("DOI", ""), r_year=y,
                                              r_venue=(w.get("container-title") or [""])[0],
                                              r_authors="; ".join(f"{a.get('given', '')} {a.get('family', '')}".strip()
                                                                  for a in (w.get("author") or [])[:6]),
                                              abstract=re.sub(r"<[^>]+>", "", w.get("abstract", "") or "")), tb)
    if best is None:
        return dict(resolution="unresolved (no title match in OpenAlex or Crossref)")
    return dict(**best[2], resolution=f"resolved by title match ({best[1]}, sim={best[0]:.3f}"
                                      f"{', venue+year tie-break' if best[3][0] and best[3][1] else ''})")


def inv(ix):
    if not ix:
        return ""
    return " ".join(w for _, w in sorted((p, w) for w, ps in ix.items() for p in ps))


# ---- 1. resolve and merge Google Scholar ranks 1-100 (cached: resolution runs once)
S = pd.read_csv(f"{OUT}/scholar_manual.csv")
assert list(S["rank"]) == list(range(1, 101)), "scholar_manual.csv must hold exactly ranks 1-100"
if not os.path.exists(f"{OUT}/scholar_resolved.csv"):
    part = f"{OUT}/scholar_resolved.partial.jsonl"  # per-record cache so a rate-limit stop resumes without re-querying
    done = {d["rank"]: d for d in map(json.loads, open(part))} if os.path.exists(part) else {}
    for _, r in S.iterrows():
        if r["rank"] in done:
            continue
        done[r["rank"]] = {**{k: (None if pd.isna(v) else v) for k, v in r.to_dict().items()}, **resolve(r)}
        with open(part, "a") as f:
            f.write(json.dumps(done[r["rank"]], default=int) + "\n")
        time.sleep(1.0)
        print(r["rank"], done[r["rank"]]["resolution"])
    pd.DataFrame([done[i] for i in S["rank"]]).to_csv(f"{OUT}/scholar_resolved.csv", index=False)
    os.remove(part)
SR = pd.read_csv(f"{OUT}/scholar_resolved.csv")
R = pd.read_csv(f"{OUT}/search_raw.csv")
if not (R.source == "GoogleScholar").any():
    g = pd.DataFrame(dict(source="GoogleScholar", query=[f"Google Scholar (manual screenshots) rank {x}" for x in SR["rank"]],
                          date="2026-10-29", title=SR.r_title.fillna(SR.title), doi=SR.doi, url=SR.url,
                          year=SR.r_year.fillna(SR.year), venue=SR.r_venue.fillna(SR.venue), authors=SR.r_authors.fillna(SR.authors),
                          abstract=SR.abstract))
    R = pd.concat([R, g], ignore_index=True)
    R.to_csv(f"{OUT}/search_raw.csv", index=False)
    log = json.load(open(f"{OUT}/search_log.json"))
    log["google_scholar"] = dict(**SCHOLAR_METHOD, records_merged=len(g),
                                 resolved=int(SR.resolution.str.startswith("resolved").sum()),
                                 unresolved=int(SR.resolution.str.startswith("unresolved").sum()),
                                 resolver_counts=SR.resolution.str.extract(r"\((OpenAlex|Crossref)")[0].value_counts().to_dict(),
                                 note="OpenAlex free daily budget was exhausted on 2026-10-29 (HTTP 429, retry-after ~23 h) after "
                                      "the main searches; records it could not answer were resolved via Crossref only")
    log["counts"]["Google Scholar (manual screenshots), ranks 1-100"] = len(g)
    log["total"] = len(R)
    json.dump(log, open(f"{OUT}/search_log.json", "w"), indent=2)

# ---- 2. deduplicate
R = pd.read_csv(f"{OUT}/search_raw.csv")
R["doi_n"] = R.doi.fillna("").str.lower().str.strip().str.replace(r"^https?://(dx\.)?doi\.org/", "", regex=True)
R["title_n"] = R.title.map(norm)
R = R[R.title_n != ""].reset_index(drop=True)
# union-find over hits: same DOI or same normalised title
parent = list(range(len(R)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for col in ["doi_n", "title_n"]:
    first = {}
    for i, v in enumerate(R[col]):
        if not v:
            continue
        if v in first:
            parent[find(i)] = find(first[v])
        else:
            first[v] = i
R["grp"] = [find(i) for i in range(len(R))]


def is_preprint(r):
    return r.doi_n.startswith(PREPRINT_DOI) or bool(re.search(r"arxiv|medrxiv|biorxiv|research square|ssrn|techrxiv", str(r.venue), re.I))


out = []
for gid, h in R.groupby("grp", sort=False):
    works = {}
    for _, r in h.iterrows():  # each distinct DOI (or title when no DOI) is a version
        works.setdefault(r.doi_n or r.title_n, []).append(r)
    versions = []
    for key, rs in works.items():
        r0 = max(rs, key=lambda r: len(str(r.abstract)) if pd.notna(r.abstract) else 0)
        versions.append((is_preprint(r0), key, r0, rs))
    versions.sort(key=lambda v: (v[0], v[1] == v[2].title_n))  # journal first, DOI-bearing first
    pre, key, r0, rs = versions[0]
    allrows = [r for v in versions for r in v[3]]
    abstract = max((str(r.abstract) for r in allrows if pd.notna(r.abstract)), key=len, default="")
    out.append(dict(title=r0.title, doi=r0.doi_n, url=r0.url, year=r0.year, venue=r0.venue, authors=r0.authors,
                    preprint_only=bool(pre), linked_versions="; ".join(v[1] for v in versions[1:]),
                    sources="; ".join(sorted(set(r.source for r in allrows))), n_hits=len(allrows),
                    scholar_ranks="; ".join(str(int(re.search(r"rank (\d+)", r.query).group(1))) for r in allrows
                                            if r.source == "GoogleScholar"),
                    abstract=abstract))
D = pd.DataFrame(out).sort_values(["year", "title"]).reset_index(drop=True)
D.insert(0, "record_id", [f"R{i + 1:03d}" for i in range(len(D))])
D.to_csv(f"{OUT}/dedup.csv", index=False)
print(f"search_raw: {len(R)} hits -> dedup.csv: {len(D)} unique works "
      f"({int((D.linked_versions != '').sum())} with a linked preprint/second version)")
print("Scholar:", SR.resolution.str.split(" \\(").str[0].value_counts().to_dict())
