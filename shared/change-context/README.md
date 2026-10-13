# Change Context

Join a Line 3 Code Changes report and a Line 4 Call Changes report by exact Ethereum target and before/after block hashes. It shows when a stable call result and a stable runtime were observed at different blocks, so a worker does not accidentally claim they were checked together. Python 3.10+ standard library only; no network, keys, installation, signing or sending.

From the workspace root:

```sh
python3 -B shared/change-context/change_context.py
```

The bundled reports are copies of two **real ZTO comparisons**. The command reports `different_blocks`: Code Changes observed block 26,183,813 before and 26,184,420 after, while Call Changes observed 26,183,845 and 26,184,452. Each call observation is **32 blocks later** than the corresponding code observation. The two tools independently report an unchanged runtime and an unchanged `totalSupply()` return, but this glue refuses to claim same-block evidence. Use `--require-aligned` to make that mismatch exit 2; the normal diagnostic exits 0.

For your own reports, first run the two original tools and save their JSON output inside the current workspace. Then run:

```sh
python3 -B shared/change-context/change_context.py --code PATH_TO_CODE_REPORT --call PATH_TO_CALL_REPORT --require-aligned
```

The tool checks schemas, Ethereum chain identity, addresses, block numbers and hashes, comparison ordering, and the code change flags. It does not revalidate the original RPC observations or authenticate either report. Matching blocks would let a worker compare the reports coherently; it would still not prove that code changes caused call changes, that the contract is safe, or that a future transaction will work.

`code-comparison.json` is a byte-for-byte copy of `line-3/tools/code-changes/zto-comparison.json`. `call-comparison.json` is the stdout of `python3 -B line-4/tools/call-changes/call_changes.py demo`, based on that line's two saved real ZTO observations. The comparison files are examples; the script needs only the report JSON format, not the line source files. Input paths stay inside the current workspace, are capped at 96,000 bytes, and reject duplicate JSON keys.
