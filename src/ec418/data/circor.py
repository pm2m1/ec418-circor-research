"""CirCor DigiScope / PhysioNet 2022 training-set loader.

Labels are read from the per-patient ``<id>.txt`` headers (checksum-verified against the
shipped SHA256SUMS), not from ``training_data.csv`` (whose checksum does NOT match in the
copy we obtained). Label semantics follow the dataset documentation:

* Murmur: Present / Absent / Unknown  (patient-level, single annotator)
* Outcome: Normal / Abnormal (NOT present in the copy we obtained -> loaded if available)

Canonical subject grouping: ``Additional ID`` links two patient IDs that belong to the same
child screened in both campaigns (CC2014 / CC2015). We take the connected components of the
link graph (union-find) as biological subjects. All splits group on ``subject_id``.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TSV_LABELS = {0: "unannotated", 1: "S1", 2: "systole", 3: "S2", 4: "diastole"}
LOCATIONS = ("AV", "PV", "TV", "MV", "Phc")


@dataclass
class Recording:
    rec_id: str          # e.g. "13918_AV" or "13918_AV_2"
    patient_id: int
    location: str
    wav: str
    hea: str
    tsv: str | None


@dataclass
class Patient:
    patient_id: int
    murmur: str
    outcome: str | None
    campaign: str | None
    additional_id: int | None
    age: str | None
    sex: str | None
    murmur_locations: list[str] = field(default_factory=list)
    systolic_grading: str | None = None
    systolic_pitch: str | None = None
    systolic_timing: str | None = None
    diastolic_timing: str | None = None
    recordings: list[Recording] = field(default_factory=list)


def _nan_to_none(v: str | None):
    if v is None:
        return None
    v = v.strip()
    return None if v.lower() in ("nan", "", "none") else v


def parse_patient_txt(path: str, data_dir: str) -> Patient:
    with open(path) as f:
        lines = [l.rstrip("\n") for l in f]
    first = lines[0].split()
    pid, n_rec, fs = int(first[0]), int(first[1]), int(first[2])
    meta = {}
    recs = []
    for l in lines[1:]:
        if l.startswith("#"):
            k, _, v = l[1:].partition(":")
            meta[k.strip()] = v.strip()
        elif l.strip():
            parts = l.split()
            loc, hea, wav = parts[0], parts[1], parts[2]
            tsv = parts[3] if len(parts) > 3 else None
            rec_id = os.path.splitext(wav)[0]
            recs.append(Recording(rec_id, pid, loc, os.path.join(data_dir, wav), os.path.join(data_dir, hea),
                                  os.path.join(data_dir, tsv) if tsv else None))
    assert len(recs) == n_rec, f"{path}: header says {n_rec} recordings, found {len(recs)}"
    assert fs == 4000, f"{path}: unexpected fs {fs}"
    add = _nan_to_none(meta.get("Additional ID"))
    mloc = _nan_to_none(meta.get("Murmur locations"))
    return Patient(
        patient_id=pid,
        murmur=meta["Murmur"],
        outcome=_nan_to_none(meta.get("Outcome")),
        campaign=_nan_to_none(meta.get("Campaign")),
        additional_id=int(float(add)) if add else None,
        age=_nan_to_none(meta.get("Age")),
        sex=_nan_to_none(meta.get("Sex")),
        murmur_locations=mloc.split("+") if mloc else [],
        systolic_grading=_nan_to_none(meta.get("Systolic murmur grading")),
        systolic_pitch=_nan_to_none(meta.get("Systolic murmur pitch")),
        systolic_timing=_nan_to_none(meta.get("Systolic murmur timing")),
        diastolic_timing=_nan_to_none(meta.get("Diastolic murmur timing")),
        recordings=recs,
    )


def load_patients(data_dir: str) -> dict[int, Patient]:
    pats = {}
    for p in sorted(glob.glob(os.path.join(data_dir, "*.txt"))):
        stem = os.path.basename(p)[:-4]
        if not stem.isdigit():
            continue  # skip LICENSE.txt, SHA256SUMS.txt, stray 2530_AV.txt dumps
        pt = parse_patient_txt(p, data_dir)
        pats[pt.patient_id] = pt
    return pats


class _UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def canonical_subjects(patients: dict[int, Patient]) -> dict[int, int]:
    """Map patient_id -> canonical subject id (smallest patient id in the linked component).

    Links pointing to IDs absent from ``patients`` are still unioned (they cannot leak, but
    they are reported by :func:`linkage_report`)."""
    uf = _UnionFind()
    for pid, p in patients.items():
        uf.find(pid)
        if p.additional_id is not None:
            uf.union(pid, p.additional_id)
    return {pid: uf.find(pid) for pid in patients}


def linkage_report(patients: dict[int, Patient]) -> dict:
    subj = canonical_subjects(patients)
    comps = pd.Series(subj).value_counts()
    linked = [p for p in patients.values() if p.additional_id is not None]
    dangling = [p.patient_id for p in linked if p.additional_id not in patients]
    asym = [p.patient_id for p in linked if p.additional_id in patients
            and patients[p.additional_id].additional_id != p.patient_id]
    label_conflicts = []
    for s, members in pd.Series(subj).groupby(pd.Series(subj)).groups.items():
        labs = {patients[m].murmur for m in members}
        if len(labs) > 1:
            label_conflicts.append((sorted(int(m) for m in members), sorted(labs)))
    return dict(n_patients=len(patients), n_subjects=int(comps.size),
                component_sizes=comps.value_counts().sort_index().to_dict(),
                n_patients_with_additional_id=len(linked), dangling_links=dangling,
                asymmetric_links=asym, label_conflicts=label_conflicts)


def patient_table(patients: dict[int, Patient]) -> pd.DataFrame:
    subj = canonical_subjects(patients)
    rows = []
    for pid, p in patients.items():
        rows.append(dict(patient_id=pid, subject_id=subj[pid], murmur=p.murmur, outcome=p.outcome,
                         campaign=p.campaign, additional_id=p.additional_id, age=p.age, sex=p.sex,
                         n_recordings=len(p.recordings), locations="+".join(r.location for r in p.recordings),
                         murmur_locations="+".join(p.murmur_locations), systolic_grading=p.systolic_grading,
                         systolic_pitch=p.systolic_pitch, systolic_timing=p.systolic_timing,
                         diastolic_timing=p.diastolic_timing))
    return pd.DataFrame(rows).sort_values("patient_id").reset_index(drop=True)


def recording_table(patients: dict[int, Patient]) -> pd.DataFrame:
    subj = canonical_subjects(patients)
    rows = []
    for pid, p in patients.items():
        for r in p.recordings:
            rows.append(dict(rec_id=r.rec_id, patient_id=pid, subject_id=subj[pid], location=r.location,
                             murmur=p.murmur, murmur_at_location=(r.location in p.murmur_locations),
                             wav=r.wav, tsv=r.tsv))
    return pd.DataFrame(rows).sort_values("rec_id").reset_index(drop=True)


def load_segmentation(tsv_path: str) -> np.ndarray:
    """Return an (n, 3) float array [start_s, end_s, label] with labels in TSV_LABELS."""
    if not isinstance(tsv_path, str) or not os.path.exists(tsv_path):
        return np.zeros((0, 3))
    arr = np.loadtxt(tsv_path, ndmin=2)
    if arr.size == 0:
        return np.zeros((0, 3))
    return arr[:, :3]
