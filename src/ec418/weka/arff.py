"""Deterministic ARFF export and WEKA invocation helpers.

* Class attribute is ALWAYS last and declared as {Absent,Present} in that order, in every file,
  so train/test headers are byte-identical (checked by the Java runner too).
* Patient / subject IDs are NEVER written as attributes; a sidecar ``*.ids.csv`` keeps the row
  -> patient mapping.
* Missing values (NaN) are written as '?' (WEKA's native missing marker).
"""
from __future__ import annotations

import os
import re
import subprocess

import numpy as np
import pandas as pd

CLASS_VALUES = ("Absent", "Present")
_ID_LIKE = re.compile(r"(patient|subject|record|rec_)_?id", re.I)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
WEKA_LIB = os.path.join(ROOT, "tools")
RUNNER_SRC = os.path.join(ROOT, "src", "ec418", "weka", "WekaBatchRunner.java")
RUNNER_BUILD = os.path.join(ROOT, "tools", "build")


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def write_arff(path: str, X: pd.DataFrame, y: np.ndarray | None, relation: str, feature_order: list[str]):
    bad = [c for c in feature_order if _ID_LIKE.search(c)]
    if bad:
        raise ValueError(f"identifier-like columns must not be predictors: {bad}")
    X = X[feature_order]
    lines = [f"@relation {_safe(relation)}", ""]
    for c in feature_order:
        lines.append(f"@attribute {_safe(c)} numeric")
    lines.append("@attribute class {" + ",".join(CLASS_VALUES) + "}")
    lines += ["", "@data"]
    vals = X.to_numpy(dtype=float)
    for i in range(vals.shape[0]):
        row = ["?" if not np.isfinite(v) else repr(float(v)) for v in vals[i]]
        lab = "?" if y is None else CLASS_VALUES[int(y[i])]
        lines.append(",".join(row + [lab]))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def read_arff_header(path: str) -> list[str]:
    hdr = []
    with open(path) as f:
        for line in f:
            if line.strip().lower() == "@data":
                break
            if line.lower().startswith("@attribute"):
                hdr.append(line.strip())
    return hdr


def classpath() -> str:
    jars = [os.path.join(WEKA_LIB, j) for j in ("weka.jar", "mtj.jar", "arpack_combined.jar", "core.jar")]
    return ":".join(jars + [RUNNER_BUILD])


def build_runner() -> None:
    os.makedirs(RUNNER_BUILD, exist_ok=True)
    cls = os.path.join(RUNNER_BUILD, "WekaBatchRunner.class")
    if os.path.exists(cls) and os.path.getmtime(cls) >= os.path.getmtime(RUNNER_SRC):
        return
    subprocess.run(["javac", "-cp", classpath(), "-d", RUNNER_BUILD, RUNNER_SRC], check=True)


def run_jobs(jobs_tsv: str, log_path: str, heap="3g") -> str:
    build_runner()
    cmd = ["java", f"-Xmx{heap}", "-cp", classpath(), "WekaBatchRunner", jobs_tsv]
    with open(log_path, "w") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
    return log_path


# Fixed, pre-registered classifier specifications (no tuning on test data).
CLASSIFIERS = {
    "RF": ("weka.classifiers.trees.RandomForest", "-I 300 -K 0 -S 1 -num-slots 1"),
    "SMO": ("weka.classifiers.functions.SMO",
            "-C 1.0 -L 0.001 -P 1.0E-12 -N 0 -M -V 5 -W 1 -K \"weka.classifiers.functions.supportVector.PolyKernel -E 1.0 -C 250007\""),
    "MLP": ("weka.classifiers.functions.MultilayerPerceptron", "-L 0.1 -M 0.2 -N 300 -V 0 -S 1 -E 20 -H a"),
    "LR": ("weka.classifiers.functions.Logistic", "-R 1.0 -M -1"),
}
