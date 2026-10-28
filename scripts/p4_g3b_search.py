"""G3b literature audit, step 1b: run the locked searches (docs/G3B_AUDIT_PROTOCOL.md §1) and save every raw hit.

Engines: OpenAlex (boolean title/abstract search + citation checks), Semantic Scholar (one query per term, backoff on
HTTP 429), PubMed (E-utilities), arXiv (API). Google Scholar is exported manually by the team
(references/g3b/scholar_manual.csv) and merged by scripts/p4_g3b_screen_prep.py.
Writes references/g3b/search_raw.csv (source, query, date, title, doi, url, year, venue, authors, abstract) and
references/g3b/search_log.json (per-engine counts and the exact query strings).
usage: .venv/bin/python scripts/p4_g3b_search.py
"""
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd

OUT = "references/g3b"
TODAY = dt.date.today().isoformat()
TERMS = ['"CirCor"', '"PhysioNet 2022"', '"PhysioNet Challenge 2022"', '"George B. Moody PhysioNet Challenge 2022"']
BOOL = "(" + " OR ".join(TERMS) + ") AND murmur"
UA = {"User-Agent": "EC418-G3b-audit/1.0 (mailto:mishraparth787@gmail.com)"}
CITED = {"Oliveira2022_JBHI": "W3191193899", "Reyna2023_PLOSDH": "W4386615065", "Reyna2022_medRxiv": "W4292183371",
         "Reyna2022_CinC": "W4323027640"}
rows, log = [], {}


def get(url, tries=6, wait=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(wait * (i + 1)); continue
            raise


def inv_abstract(ix):
    if not ix:
        return ""
    pos = sorted((p, w) for w, ps in ix.items() for p in ps)
    return " ".join(w for _, w in pos)


def openalex(filter_str, label):
    n, cursor = 0, "*"
    while cursor:
        url = ("https://api.openalex.org/works?per-page=200&cursor=" + urllib.parse.quote(cursor) + "&filter=" +
               urllib.parse.quote(filter_str, safe=":,|") + "&mailto=mishraparth787@gmail.com")
        d = json.loads(get(url))
        for w in d["results"]:
            loc = (w.get("primary_location") or {}).get("source") or {}
            rows.append(dict(source="OpenAlex", query=label, date=TODAY, title=w.get("display_name") or "",
                             doi=(w.get("doi") or "").replace("https://doi.org/", ""), url=w.get("id"),
                             year=w.get("publication_year"), venue=loc.get("display_name") or "",
                             authors="; ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:6]),
                             abstract=inv_abstract(w.get("abstract_inverted_index"))))
            n += 1
        cursor = d["meta"].get("next_cursor")
    log[label] = n


# OpenAlex: boolean search over title + abstract
oa_q = BOOL.replace('"George B. Moody PhysioNet Challenge 2022"', '"Moody PhysioNet Challenge 2022"')
openalex(f"title_and_abstract.search:{oa_q},publication_year:2022-2026", f"OpenAlex title_and_abstract.search: {oa_q}; years 2022-2026")
# OpenAlex citation checks (murmur in title/abstract)
for name, wid in CITED.items():
    openalex(f"cites:{wid},title_and_abstract.search:murmur,publication_year:2022-2026", f"OpenAlex cites:{name} ({wid}) AND murmur; years 2022-2026")

# Semantic Scholar: one query per term (no boolean OR in its search)
for t in TERMS:
    q = f"{t.strip(chr(34))} murmur"
    n, off = 0, 0
    while off < 1000:
        url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(q) +
               f"&year=2022-2026&offset={off}&limit=100&fields=title,year,venue,externalIds,url,authors,abstract")
        try:
            d = json.loads(get(url, tries=4, wait=15))    # unauthenticated S2 pool; a failure is logged, not hidden
        except urllib.error.HTTPError as e:
            log[f"S2 search: {q} (FAILED at offset {off}: HTTP {e.code})"] = n
            break
        for p in d.get("data", []):
            rows.append(dict(source="SemanticScholar", query=f"S2 search: {q}; years 2022-2026", date=TODAY, title=p.get("title") or "",
                             doi=(p.get("externalIds") or {}).get("DOI") or "", url=p.get("url"), year=p.get("year"),
                             venue=p.get("venue") or "", authors="; ".join(a["name"] for a in (p.get("authors") or [])[:6]),
                             abstract=p.get("abstract") or ""))
            n += 1
        if "next" not in d:
            break
        off = d["next"]; time.sleep(1.5)
    log[f"S2 search: {q}"] = n
    time.sleep(3)

# PubMed
pq = '(CirCor OR "PhysioNet 2022" OR "PhysioNet Challenge 2022" OR "George B. Moody PhysioNet Challenge 2022") AND murmur'
ids = json.loads(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax=1000&retmode=json&datetype=pdat"
                     "&mindate=2022&maxdate=2026&term=" + urllib.parse.quote(pq)))["esearchresult"]["idlist"]
for i in range(0, len(ids), 100):
    x = ET.fromstring(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=" + ",".join(ids[i:i + 100])))
    for a in x.findall(".//PubmedArticle"):
        art = a.find(".//Article")
        doi = next((e.text for e in a.findall(".//ArticleId") if e.get("IdType") == "doi"), "") or ""
        pmid = a.findtext(".//PMID")
        rows.append(dict(source="PubMed", query=f"PubMed: {pq}; pdat 2022-2026", date=TODAY,
                         title="".join(art.find("ArticleTitle").itertext()) if art is not None else "", doi=doi,
                         url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", year=a.findtext(".//PubDate/Year") or a.findtext(".//ArticleDate/Year"),
                         venue=a.findtext(".//Journal/Title") or "",
                         authors="; ".join(f"{au.findtext('LastName')} {au.findtext('Initials')}" for au in a.findall(".//Author")[:6]),
                         abstract=" ".join("".join(t.itertext()) for t in a.findall(".//AbstractText"))))
    time.sleep(0.5)
log[f"PubMed: {pq}"] = len(ids)

# arXiv
aq = '(all:CirCor OR all:"PhysioNet 2022" OR all:"PhysioNet Challenge 2022" OR all:"George B. Moody PhysioNet Challenge 2022") AND all:murmur'
x = ET.fromstring(get("https://export.arxiv.org/api/query?max_results=500&search_query=" + urllib.parse.quote(aq)))
ns = {"a": "http://www.w3.org/2005/Atom"}
n = 0
for e in x.findall("a:entry", ns):
    yr = int(e.findtext("a:published", namespaces=ns)[:4])
    if 2022 <= yr <= 2026:
        rows.append(dict(source="arXiv", query=f"arXiv: {aq}; published 2022-2026", date=TODAY,
                         title=" ".join(e.findtext("a:title", namespaces=ns).split()), doi=e.findtext("{http://arxiv.org/schemas/atom}doi") or "",
                         url=e.findtext("a:id", namespaces=ns), year=yr, venue="arXiv",
                         authors="; ".join(au.findtext("a:name", namespaces=ns) for au in e.findall("a:author", ns)[:6]),
                         abstract=" ".join(e.findtext("a:summary", namespaces=ns).split())))
        n += 1
log[f"arXiv: {aq}"] = n

os.makedirs(OUT, exist_ok=True)
R = pd.DataFrame(rows)
R.to_csv(f"{OUT}/search_raw.csv", index=False)
json.dump(dict(date=TODAY, counts=log, total=len(R), google_scholar="manual export by the team -> references/g3b/scholar_manual.csv"),
          open(f"{OUT}/search_log.json", "w"), indent=2)
print(json.dumps(log, indent=2)); print("total raw hits:", len(R))
