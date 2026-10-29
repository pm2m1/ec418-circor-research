# Reproducing one pipeline fold in the WEKA Explorer GUI

Fold: **A_stft** (cycle-aligned STFT band features, expert labels), **repeat 0, outer fold 0** of the frozen subject-grouped
folds. 699 training patients and 175 test patients; 68 features + `class {Absent,Present}`. The ARFFs here are the pipeline's
own files, unchanged. The CLI run of the same fold (`run_cli.sh`) reproduces the pipeline prediction exactly
(`check_result.json`).

## Start WEKA 3.9.7
From the repo root: `java -cp "tools/weka.jar:tools/mtj.jar:tools/arpack_combined.jar:tools/core.jar" weka.gui.GUIChooser`
(needs Java 17+; on the Mac `export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"` first). Click **Explorer**.

## Steps
1. **Preprocess tab → Open file…** → `weka_demo/A_stft_r0_f0_outer_train.arff`. Check: Relation `A_stft_train`, Instances
   **699**, Attributes **69**; the class attribute `class` shows Absent / Present counts.
   📸 **Screenshot 1: the Preprocess tab** (with `class` selected in the attribute list, so the class bar chart is visible).
2. **Classify tab → Choose** → `trees` → **RandomForest**. Click the classifier name to open its options and set them
   to the pipeline values: `numIterations` = **300**, `numFeatures` = **0**, `seed` = **1**, `numExecutionSlots` = **1**.
   Leave everything else at its default. The command line next to *Choose* must read
   `RandomForest -P 100 -I 300 -num-slots 1 -K 0 -M 1.0 -V 0.001 -S 1`; `-P`, `-M` and `-V` are WEKA defaults that the pipeline
   also uses.
   📸 **Screenshot 2: the classifier options dialog** (with the four values above visible).
3. **Test options → Supplied test set → Set…** → `weka_demo/A_stft_r0_f0_outer_test.arff` (175 instances). Do **not**
   use *Cross-validation*: it would split rows and mix recordings of the same child (see `docs/WEKA_SETUP.md`).
4. **More options… → Output predictions → Choose** → `CSV` (set `outputDistribution` = True). Then OK.
5. Check that the class is `(Nom) class`, then press **Start**.
6. The result buffer shows the evaluation on the test set.
   📸 **Screenshot 3: the result buffer, scrolled to the "Error on test data" summary and the Confusion Matrix.**

## Expected result (from the CLI run, `cli_output.txt`; WEKA's default decision = the higher probability, i.e. 0.5 here)
```
Correctly Classified Instances         148               84.5714 %
Total Number of Instances              175

   a   b   <-- classified as
 131   8 |   a = Absent
  19  17 |   b = Present
```
TN = 131, FP = 8, FN = 19, TP = 17 (no test patient has P(Present) exactly 0.5). The per-instance distribution in the
Explorer's prediction output should equal `cli_predictions.csv`. If the numbers differ, check the four RF options first.

Put the screenshots in `weka_demo/screenshots/` as `1_preprocess.png`, `2_rf_options.png`, `3_result_buffer.png`; the slides
have placeholders with these names.

Note: the study's reported metrics use a threshold chosen on inner training folds (specificity ≥ 0.80), not 0.5. This demo uses
0.5 only because it is WEKA's default display.
