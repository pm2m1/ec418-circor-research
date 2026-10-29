# WEKA_SETUP — how WEKA is used in this study

**Version.** WEKA 3.9.7 (SHA-256 of `tools/weka.jar`: `e60fffff…8cc3`), with `mtj.jar`, `arpack_combined.jar` and `core.jar`. These four files are **not tracked** in the current Git repository. Install/verify them in a fresh clone using `python scripts/install_weka_jars.py` (see [`tools/WEKA_DEPENDENCIES.md`](../tools/WEKA_DEPENDENCIES.md)). They were previously tracked and remain in older Git commits. Java: OpenJDK 21 on macOS; Phase 1 used Ubuntu.

## Classifiers (fixed before any model was trained; `src/ec418/weka/arff.py`, `CLASSIFIERS`)
| Name | WEKA class | Options (exact strings) |
|---|---|---|
| RF (primary) | `weka.classifiers.trees.RandomForest` | `-I 300 -K 0 -S 1 -num-slots 1` |
| SMO (secondary) | `weka.classifiers.functions.SMO` | `-C 1.0 -L 0.001 -P 1.0E-12 -N 0 -M -V 5 -W 1 -K "weka.classifiers.functions.supportVector.PolyKernel -E 1.0 -C 250007"` |
| MLP (Phase 1 only) | `weka.classifiers.functions.MultilayerPerceptron` | `-L 0.1 -M 0.2 -N 300 -V 0 -S 1 -E 20 -H a` |
| Logistic (Phase 1 only) | `weka.classifiers.functions.Logistic` | `-R 1.0 -M -1` |

RF: 300 trees, default number of features per split (`-K 0` = log2(m)+1), seed 1, single thread (`-num-slots 1`) so results do
not depend on thread scheduling. SMO: linear PolyKernel (exponent 1), no normalisation (`-N 0`), logistic calibration of the
outputs (`-M`), with the calibration fitted by 5-fold internal CV on the *training* data (`-V 5`, seed `-W 1`). None of these
options were tuned.

## Why WEKA's own cross-validation is not used
WEKA's Explorer/`-x` cross-validation splits **rows**. In CirCor, one child has 1–6 recordings, and linked visits
(`Additional ID`) put the same child in the data twice. Row-wise CV would therefore place recordings or visits of the same
child in both training and test, which is subject leakage. All evaluation folds are built in Python instead:
`StratifiedGroupKFold` on the canonical subject (the connected component of the `Additional ID` links), 5 repeats × 5 outer
folds (`configs/folds_patient_level.csv`, sha256 `c4aa74c7…2339`), plus 3 inner folds inside each outer training set that are
used only for decision thresholds. WEKA only ever sees one train ARFF and one test ARFF per job. Patient and subject IDs
are never written as attributes (`write_arff` refuses identifier-like column names; IDs go to a separate `.ids.csv` file
with the same row order).

## How the pipeline calls WEKA
1. `scripts/06_run_patient_level_weka.py TAG SETS CLFS NJVM` builds the patient feature matrix (median and max over each
   patient's recordings). For every set × repeat × outer fold it writes the outer train/test ARFF and the 3 inner train/test
   pairs, under `experiments/<TAG>/arff/` (gitignored). The class `{Absent,Present}` is the last attribute.
2. It writes job lists (`experiments/<TAG>/jobs_<j>.tsv`: name, train ARFF, test ARFF, output CSV, classifier class,
   options) and starts `NJVM` Java processes of `WekaBatchRunner` (`src/ec418/weka/WekaBatchRunner.java`, compiled into
   `tools/build/`).
3. `WekaBatchRunner` runs many jobs in one JVM. For each job it reads both ARFFs, checks that the headers are equal and
   that the class is `{Absent,Present}`, builds the classifier with `AbstractClassifier.forName(class, options)`, and writes
   `row,p_present,pred,actual`. `p_present` is `distributionForInstance(...)[Present]`, printed with `%.10f`.
4. Python reads the predictions back, checks the row and label alignment against the `.ids.csv` files, derives the
   thresholds from the inner out-of-fold scores (specificity ≥ 0.80, maximum weighted accuracy) and saves
   `results/predictions/<TAG>_predictions.csv`.

## Showing WEKA directly
`weka_demo/` holds one pipeline fold (A_stft, repeat 0, outer fold 0): the pipeline's own ARFFs, `run_cli.sh` (plain WEKA CLI,
the same RF options) and `check_cli_vs_pipeline.py`. The CLI probabilities equal the saved pipeline prediction **exactly**
(175/175 test patients; `weka_demo/check_result.json`). `weka_demo/EXPLORER_STEPS.md` describes the same run in the WEKA
Explorer GUI.
