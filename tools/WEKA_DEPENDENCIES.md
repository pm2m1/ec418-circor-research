# WEKA runtime dependencies (not committed as binaries)

The research uses WEKA **3.9.7** (Java 21 in the recorded environment). To
reproduce the exact Java environment in a fresh clone, run from the repository
root:

```bash
python scripts/install_weka_jars.py
java -cp 'tools/*' weka.core.Version
```

The installer downloads the source distribution of
[`python-weka-wrapper3==0.3.3`](https://pypi.org/project/python-weka-wrapper3/0.3.3/)
from PyPI and verifies the release archive (SHA-256
`5b7208b99116cb882cf24f1d72e3e1380d29f0859bc419872b8a0e0b5e90883f`).
It then extracts the four pinned JARs and verifies their checksums. It does not
install the Python wrapper package or modify research data.

| Locally installed file | SHA-256 |
| --- | --- |
| `tools/weka.jar` | `e60ffffbebbb49d1805a2b77075c869706802af93b8e876a8e0ac9a435698cc3` |
| `tools/mtj.jar` | `641f74e1fe54886183076d0dc9dd8589422148f1fd4f054fe62ee268e875f315` |
| `tools/core.jar` | `5ffaddee0a3f8d09a56064aa05feb95837ddad9d42d9dcc37479c66e869aa139` |
| `tools/arpack_combined.jar` | `8d55d2bc18af3d5dfc8106d79b659cb7c7c76307d6d1021401dcb45f40f40575` |

To check an existing installation without network access:

```bash
python scripts/install_weka_jars.py --verify
```

The four JARs are ignored by Git and are **not included in the current repository
version**. They were distributed in earlier Git history and those copies remain
accessible through historical commits. Their copyrights and licences remain
with their respective owners; see `THIRD_PARTY_NOTICES.md` and the upstream
packages. Removing current Git tracking does not erase historical distributions
or necessarily resolve past redistribution obligations.

Classifier settings and subject-grouped evaluation details are in
[`docs/WEKA_SETUP.md`](../docs/WEKA_SETUP.md).
