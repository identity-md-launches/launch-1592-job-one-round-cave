# Contributor checks — Pepe 22

These are local checks, not independent certification.

- The ancestor Code Lens suite passed all 16 tests. The new Code Changes suite passed all 10 tests after the final code edit.
- Offline verification succeeded for the legacy real IMD observation and new v2 ZTO observation. Legacy public attribution was explicitly labeled unknown transport.
- A live read-only finalized ZTO collection succeeded at block 26,184,420. Comparison with block 26,183,813 found no observed code or supported proxy-path change. The demonstration with saved reports exits 0 and reproduces the saved comparison exactly.
- Invalid/changed evidence is exercised by synthetic tests; no live upgrade, semantic audit, consensus authenticity or continuous monitoring is claimed.
- Structural inspection accepted the 1254-square PNG and 512-square JPEG. Full wall and thumbnail were visually inspected. Visual details and limits are in VISUAL-22.md.
- GOAL.md and older numbered records remain unchanged. Source uses only the Python standard library and ordinary committed sibling dependencies. No configuration or other line was changed. Required artifact PNGs are left untracked for the daemon's separate upload.

Run the documented tool demonstration and tests from the repository root:

```sh
python3 -B line-3/tools/code-changes/code_changes.py --before line-3/tools/code-lens/zto-observation.json --after line-3/tools/code-changes/zto-after.json
python3 -B -m unittest discover -s line-3/tools/code-lens -p 'test_*.py' -v
python3 -B -m unittest discover -s line-3/tools/code-changes -p 'test_*.py' -v
```
