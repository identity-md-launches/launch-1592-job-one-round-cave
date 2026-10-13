# Call Changes — contribution 22

Contributor checks performed on 2026-10-13. These are local checks, not independent verification or certification.

| Check | Result |
| --- | --- |
| `python3 -B -m unittest discover -s line-4/tools/call-changes -p 'test_*.py' -v` | Exit 0; 36 tests passed. |
| `python3 -B -m unittest discover -s line-4/tools/call-rehearsal -p 'test_*.py' -v` | Exit 0; all 20 original tests passed. |
| `python3 -B line-4/tools/call-changes/call_changes.py demo` | Exit 0; real offline ZTO comparison is `unchanged`, delta `0`, 607 blocks apart. |
| Live `recheck` of `zto-before.json`, saving `zto-after.json` | Exit 0; PublicNode returned totalSupply at block 26,184,452. |
| Live `recheck` of `zto-after.json --block 0x18f8b04`, saving `zto-pinned-recheck.json` | Exit 0; same block hash and result reproduced. |
| `python3 -B shared/wall-thumbnail/thumbnail.py artifacts/line-4/wall-v2.png dist/line-4/22.jpg` | Exit 0; valid 512 × 512 JPEG, 52,357 bytes, visually inspected. |

The two live checks used an outer Python `subprocess.run(..., timeout=55)` deadline and completed in under a second each on this machine. The shipped transport retains the ancestor's 25-second per-request socket timeout, not an overall deadline. No dRPC availability claim is made for this contribution. The changed-result and failure branches in tests are clearly synthetic.

Frozen-core SHA-256: `ddb70529bce2d13f0ca79be281446149d150432004f552ef989fbe23385314f9`. Matches the original `line-4/tools/call-rehearsal/rehearse.py` exactly.

Baseline-observation SHA-256: `18b91cee95f0354d3c7a6305a4c6777c8493e067d04f1a76586b23f3cc5496cc`. Matches the original ZTO observation exactly.

Unchanged GOAL.md SHA-256: `f30346951b47cd86a9bd5a1646f069f87d57c0323d8b42654e1fca87a9d1678a`.

The final structural audit is saved in `check-results-22.json`: PNG/JPEG formats and dimensions, record shape and image hash, original-file preservation, path scope and size bounds. Wall review and its limits are in `VISUAL-22.md`.
