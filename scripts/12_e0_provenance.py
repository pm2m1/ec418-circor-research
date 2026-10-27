"""E0: verify the PhysioNet CirCor v1.0.3 download against the files used in Phase 1.

Checks (inputs are checksum lists committed in references/data_provenance/, so no raw data is needed
in git):
  1. download integrity: every file listed in PhysioNet's own SHA256SUMS.txt hashes as listed;
  2. every .wav/.hea/.tsv used in Phase 1 (recording_files_sha256.txt) is byte-identical in the download;
  3. full diff of the Phase-1 copy's SHA256SUMS (circor_copy_SHA256SUMS.txt) vs PhysioNet's SHA256SUMS.txt;
  4. patient .txt files that differ: identical once '#Outcome' lines are removed? murmur label and
     Additional ID equal to the Phase-1 audit (results/tables/patients_audit.csv)?
  5. counts: patients, recordings, murmur classes.
Writes results/logs/e0_provenance.json and results/tables/e0_sha256_differences.csv.

  6. optional COPY_TXT_DIR (the Phase-1 copy's 942 patient .txt, e.g. fetched from github.com/chihoon1/Murmur
     @56b9846 and verified against circor_copy_SHA256SUMS.txt): line-by-line comparison after normalising
     line endings (CRLF -> LF, final newline) and dropping '#Outcome' -> results/tables/e0_patient_txt_content_diffs.csv

usage: python scripts/12_e0_provenance.py PHYSIONET_ROOT [COPY_TXT_DIR]
"""
import hashlib
import json
import os
import sys

import pandas as pd

from ec418.data.circor import load_patients, recording_table

ROOT = sys.argv[1]
COPY_TXT = sys.argv[2] if len(sys.argv) > 2 else None
TRAIN = os.path.join(ROOT, "training_data")
REF = "references/data_provenance"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sums(path):
    out = {}
    for line in open(path):
        if line.strip():
            h, name = line.rstrip("\n").split(maxsplit=1)
            out[name.lstrip("*").strip()] = h
    return out


phys = read_sums(os.path.join(ROOT, "SHA256SUMS.txt"))
copy = read_sums(f"{REF}/circor_copy_SHA256SUMS.txt")
used = read_sums(f"{REF}/recording_files_sha256.txt")

# 1. download integrity against PhysioNet's own list
actual = {}
for name in phys:
    p = os.path.join(ROOT, name)
    actual[name] = sha256(p) if os.path.exists(p) else None
dl_missing = sorted(n for n, h in actual.items() if h is None)
dl_bad = sorted(n for n, h in actual.items() if h is not None and h != phys[n])
on_disk = sorted(os.path.relpath(os.path.join(d, f), ROOT) for d, _, fs in os.walk(ROOT) for f in fs)
dl_unlisted = sorted(set(on_disk) - set(phys) - {"SHA256SUMS.txt"})

# 2. Phase-1 recording files vs download
rec_rows = []
for name, h in used.items():
    p = os.path.join(TRAIN, name)
    got = sha256(p) if os.path.exists(p) else None
    rec_rows.append(dict(file=name, phase1=h, physionet=got, identical=(got == h)))
rec = pd.DataFrame(rec_rows)
phys_rec_files = {n.split("/", 1)[1] for n in phys if n.startswith("training_data/") and n.rsplit(".", 1)[-1] in ("wav", "hea", "tsv")}
rec_extra_in_physionet = sorted(phys_rec_files - set(used))

# 3. copy SHA256SUMS vs PhysioNet SHA256SUMS
diff = []
for name in sorted(set(copy) | set(phys)):
    a, b = copy.get(name), phys.get(name)
    if a != b:
        kind = "only_in_copy" if b is None else "only_in_physionet" if a is None else "hash_differs"
        diff.append(dict(file=name, kind=kind, copy_sha256=a, physionet_sha256=b))
D = pd.DataFrame(diff, columns=["file", "kind", "copy_sha256", "physionet_sha256"])

# 4. patient .txt files: what differs?
txt_rows = []
for name in D.file:
    if not (name.startswith("training_data/") and name.endswith(".txt") and name.split("/")[1][:-4].isdigit()):
        continue
    p = os.path.join(ROOT, name)
    lines = open(p, "rb").read().splitlines(keepends=True)
    extra = [l.decode().strip() for l in lines if l.startswith(b"#Outcome")]
    stripped = b"".join(l for l in lines if not l.startswith(b"#Outcome"))
    txt_rows.append(dict(file=name, removed_lines="|".join(extra),
                         identical_after_removing_outcome=(hashlib.sha256(stripped).hexdigest() == copy.get(name))))
T = pd.DataFrame(txt_rows, columns=["file", "removed_lines", "identical_after_removing_outcome"])
D = D.merge(T, on="file", how="left")
D.to_csv("results/tables/e0_sha256_differences.csv", index=False)

# murmur labels and Additional ID vs Phase-1 audit
pats = load_patients(TRAIN)
audit = pd.read_csv("results/tables/patients_audit.csv")
now = pd.DataFrame([dict(patient_id=p.patient_id, murmur=p.murmur, additional_id=p.additional_id, outcome=p.outcome)
                    for p in pats.values()])
J = audit[["patient_id", "murmur", "additional_id"]].merge(now, on="patient_id", how="outer", suffixes=("_v1", "_phys"),
                                                           indicator=True)
same_add = (J.additional_id_v1.fillna(-1).astype(float) == J.additional_id_phys.fillna(-1).astype(float))
rt = recording_table(pats)

# 6. normalised content comparison of patient headers (copy vs PhysioNet)
txt_cmp = None
if COPY_TXT:
    def norm(path):
        return [l for l in open(path, "rb").read().decode().replace("\r\n", "\n").split("\n")
                if l and not l.startswith("#Outcome")]
    crow, n_verified, n_crlf = [], 0, 0
    for pid in sorted(pats):
        name = f"training_data/{pid}.txt"
        cp = os.path.join(COPY_TXT, f"{pid}.txt")
        n_verified += sha256(cp) == copy.get(name)
        n_crlf += b"\r\n" in open(cp, "rb").read()
        a, b = norm(cp), norm(os.path.join(TRAIN, f"{pid}.txt"))
        if a != b:
            for i in range(max(len(a), len(b))):
                la, lb = (a[i] if i < len(a) else None), (b[i] if i < len(b) else None)
                if la != lb:
                    crow.append(dict(patient_id=pid, line=i + 1, copy=la, physionet=lb))
    TC = pd.DataFrame(crow, columns=["patient_id", "line", "copy", "physionet"])
    TC.to_csv("results/tables/e0_patient_txt_content_diffs.csv", index=False)
    txt_cmp = dict(copy_txt_dir=COPY_TXT, copy_txt_files=len(pats), copy_txt_sha256_verified=int(n_verified),
                   copy_txt_with_crlf=int(n_crlf),
                   patients_with_content_difference_after_normalisation=sorted(int(x) for x in TC.patient_id.unique()),
                   differing_lines=TC.to_dict("records"))

summary = dict(
    physionet_root=ROOT,
    download=dict(files_listed_in_physionet_sha256sums=len(phys), missing=dl_missing, hash_mismatch=dl_bad,
                  unlisted_files_on_disk=dl_unlisted),
    phase1_recording_files=dict(n=len(rec), identical=int(rec.identical.sum()),
                                not_identical=rec.loc[~rec.identical, "file"].tolist(),
                                wav_hea_tsv_in_physionet_not_used_in_phase1=rec_extra_in_physionet),
    copy_vs_physionet_sha256sums=dict(n_copy=len(copy), n_physionet=len(phys), n_differences=len(D),
                                      by_kind=D.kind.value_counts().to_dict(),
                                      patient_txt_differences=int(len(T)),
                                      patient_txt_identical_after_removing_outcome=int(T.identical_after_removing_outcome.sum()),
                                      non_patient_txt_differences=D.loc[D.identical_after_removing_outcome.isna(), "file"].tolist()),
    labels_vs_phase1=dict(patients_v1=int((J._merge != "right_only").sum()), patients_physionet=int((J._merge != "left_only").sum()),
                          only_in_one=int((J._merge != "both").sum()),
                          murmur_mismatch=int((J.murmur_v1 != J.murmur_phys).sum()),
                          additional_id_mismatch=int((~same_add).sum())),
    patient_txt_content_vs_copy=txt_cmp,
    counts=dict(patients=len(pats), recordings=len(rt), murmur=now.murmur.value_counts().to_dict(),
                outcome=now.outcome.value_counts(dropna=False).to_dict()),
)
os.makedirs("results/logs", exist_ok=True)
json.dump(summary, open("results/logs/e0_provenance.json", "w"), indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
