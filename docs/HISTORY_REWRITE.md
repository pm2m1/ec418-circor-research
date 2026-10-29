# HISTORY_REWRITE — commit metadata normalised to the sole author (2026-10-29)

**Commit metadata normalised to the sole author; file contents unchanged, proven by identical tree hashes.**

On 2026-10-29 the author (Parth Mishra, repository owner) rewrote the git history of this repository once, as an explicit
exception to project rule 2 (recorded in `docs/PROJECT_RULES.md`). Only commit/tag metadata changed:

* author, committer and tagger of every commit and annotated tag set to `Parth Mishra <205018893+pm2m1@users.noreply.github.com>`
  (author and commit dates, and tag dates, unchanged);
* message lines starting with `Co-Authored-By:`, `Claude-Session:` or `🤖 Generated with` removed;
* the subject of the 2026-10-27 "Mac setup" commit (old `6b64b85`) reworded to "Mac setup: project rules file, environment
  record, README wording", and its body's "CLAUDE.md records" to "The project rules file records".

No file was added, removed or changed (no path filtering). Tool: `git filter-repo` 2.47.0 with `--preserve-commit-hashes`
(old hashes cited inside commit messages were left as written) and `--replace-refs delete-no-add`, run on a fresh mirror clone.

## Verification before the force-push (all passed)
* 61 commits mapped old → new; **0 tree-hash mismatches** (each old commit's tree equals its new commit's tree);
  parents map one to one; author/commit dates identical; messages differ only by the changes listed above.
* All 8 annotated tags exist, are still annotated, point to the mapped commits, and keep their dates.
* No commit or tag contains an AI trailer or identity (`Co-Authored-By`, `Claude-Session`, `Generated with`,
  `noreply@anthropic.com`); every author, committer and tagger is Parth Mishra.
* After the push, the remote branches and tags equal the verified rewrite; the working copy was reset to it.

## Resolving old hashes
Documents, protocols, logs and commit messages written before the rewrite cite **old** hashes (e.g. the pre-registration
timeline in `docs/RESULTS_SUMMARY.md`, `docs/PROTOCOL_V3_PREREG.md`, `results/logs/p3_mac_provenance.txt`). They are left
unchanged, and the locked protocol texts must not be edited. Every old hash (full or abbreviated) resolves through
`results/history_hash_map.csv` (`old_hash,new_hash,tree_hash`, one row per commit, in date order). The tree hash proves
that the old and the new commit contain exactly the same files. Hashes of the separate cloud-sandbox history
(e.g. `7acc9fc`, `54de9b3`, tag `protocol-v3-prereg`) are not part of this repository and are not affected.

## Branches
| branch | old tip | new tip |
|---|---|---|
| `main` | `cae9708` | `50cc63f` |
| `phase3-g2` | `855c681` | `eb2cb0c` |
| `phase4-writeup` | `390ea43` | `5624534` |

## Tags (annotated)
| tag | old tag object | old commit | new tag object | new commit |
|---|---|---|---|---|
| `diag-prereg` | `31b9559` | `4009275` | `e5098a1` | `2e84732` |
| `e1b-prereg` | `d57f4e7` | `7f07b74` | `4a14e70` | `46c53a7` |
| `e4-prereg` | `92f0ed2` | `64e0e91` | `2ce8305` | `a1e902a` |
| `phase3-results` | `e14d234` | `855c681` | `f0ff747` | `eb2cb0c` |
| `protocol-v2-lock` | `87b2931` | `e9a1b98` | `d784070` | `6e5c61c` |
| `results-final` | `28bab89` | `cae9708` | `1aeff44` | `50cc63f` |
| `s1-prereg` | `5321960` | `a2bddb5` | `ef9ca98` | `66a9704` |
| `v1.0-pilot` | `dca083a` | `24b0011` | `747a1bb` | `5ec326c` |

A full backup of the pre-rewrite history was kept outside the repository (git bundle, never pushed).
