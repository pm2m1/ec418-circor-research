"""Level-1 reproducibility check: verify stored results, frozen folds and protocol locks without the raw data.

Read-only; writes nothing. Cross-platform (hashlib, no shasum/sha256sum needed). Checks:
  1. results/v1_freeze/MANIFEST_v1.sha256 and results/final_freeze/MANIFEST_final.sha256 (every listed file);
  2. configs/folds_patient_level.csv against configs/folds_patient_level.sha256;
  3. each protocol lock file against the file content at the commit where it was locked. Protocol documents carry
     amendments appended after the lock, so the current files are not expected to match; the v3 pre-registration
     text must be an exact byte prefix of the current docs/PROTOCOL_V3_PREREG.md;
  4. results/history_hash_map.csv: every mapped new commit exists and has the recorded tree.
Exit code 1 on any failure.
usage: .venv/bin/python scripts/p5_verify_integrity.py
"""
import csv
import hashlib
import subprocess
import sys

fails = []


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, check=True).stdout


for man in ["results/v1_freeze/MANIFEST_v1.sha256", "results/final_freeze/MANIFEST_final.sha256"]:
    n = bad = 0
    for line in open(man):
        if not line.strip():
            continue
        h, p = line.rstrip("\n").split(None, 1)
        p = p.lstrip("*")
        n += 1
        try:
            if sha(open(p, "rb").read()) != h:
                bad += 1
                fails.append(f"{man}: {p} changed")
        except FileNotFoundError:
            bad += 1
            fails.append(f"{man}: {p} missing")
    print(f"{man}: {n - bad}/{n} OK")

folds = open("configs/folds_patient_level.sha256").read().split()[0]
ok = sha(open("configs/folds_patient_level.csv", "rb").read()) == folds
print(f"configs/folds_patient_level.csv: {'OK' if ok else 'CHANGED'} ({folds[:12]}…)")
if not ok:
    fails.append("folds changed")

root = git("rev-list", "--max-parents=0", "HEAD").decode().split()[0]
LOCKS = [("configs/protocol_lock.sha256", root, "v1 lock (root commit)"), ("configs/protocol_v2_lock.sha256", "protocol-v2-lock", ""),
         ("configs/protocol_v2_e1b.sha256", "e1b-prereg", ""), ("configs/protocol_v2_diag.sha256", "diag-prereg", ""),
         ("configs/protocol_v2_e4.sha256", "e4-prereg", ""), ("configs/protocol_v2_s1.sha256", "s1-prereg", "")]
for lock, ref, note in LOCKS:
    for line in open(lock):
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            h, p = parts
            ok = sha(git("show", f"{ref}:{p}")) == h
            print(f"{lock}: {p} @ {ref if not note else note}: {'OK' if ok else 'MISMATCH'}")
            if not ok:
                fails.append(f"{lock}: {p} @ {ref}")
v3 = {p: h for h, p in (l.split() for l in open("configs/protocol_v3_lock.sha256") if len(l.split()) == 2 and len(l.split()[0]) == 64)}
ok = sha(open("configs/protocol_v3.json", "rb").read()) == v3["configs/protocol_v3.json"]
print(f"configs/protocol_v3_lock.sha256: configs/protocol_v3.json (current): {'OK' if ok else 'MISMATCH'}")
doc = open("docs/PROTOCOL_V3_PREREG.md", "rb").read()
cut = [i for i in range(1, len(doc) + 1) if doc[i - 1:i] == b"\n" and sha(doc[:i]) == v3["docs/PROTOCOL_V3_PREREG.md"]]
print(f"configs/protocol_v3_lock.sha256: docs/PROTOCOL_V3_PREREG.md locked text is a byte prefix: {'OK' if cut else 'NO'}"
      + (f" (first {cut[0]} bytes; the rest are amendments)" if cut else ""))
if not ok or not cut:
    fails.append("v3 lock")

rows = list(csv.DictReader(open("results/history_hash_map.csv")))
bad = 0
for r in rows:
    try:
        if git("rev-parse", r["new_hash"] + "^{tree}").decode().strip() != r["tree_hash"]:
            bad += 1
    except subprocess.CalledProcessError:
        bad += 1
print(f"results/history_hash_map.csv: {len(rows) - bad}/{len(rows)} new commits exist with the recorded tree")
if bad:
    fails.append("history map")

print("\nALL INTEGRITY CHECKS PASSED" if not fails else "\nFAILED:\n" + "\n".join(fails))
sys.exit(1 if fails else 0)
