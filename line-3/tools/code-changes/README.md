# Code Changes

Compare two block-pinned Ethereum runtime observations before trusting a contract again. It verifies both Code Lens reports, checks target and block ordering, then reports changes in runtime hashes, standard proxy slots, candidate routing, and beacon code/results. A proxy can change while its terminal runtime hash stays the same; this tool reports that separately.

Run this offline demonstration from the repository root:

```sh
python3 -B line-3/tools/code-changes/code_changes.py --before line-3/tools/code-lens/zto-observation.json --after line-3/tools/code-changes/zto-after.json
```

It compares two **real ZTO observations**, using only Python 3.9+ and its standard library. Keep the sibling `code-lens/` directory: its verifier and Keccak implementation are ordinary committed dependencies. No installation or network is needed for the demonstration. Reports must resolve inside the current workspace.

## What happened when tried

ZTO at finalized blocks **26,183,813** and **26,184,420** has the same 1,287-byte runtime, Keccak hash `0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d`, zero implementation/beacon slots, and no supported proxy signal. The new block hash is `0x5843472ab10a0768b425c2350451c92883e3c10d32b29819244eddeace86b2b5`. Output: `unchanged-at-observed-blocks`; both change flags are false. The reproducible comparison is saved in `zto-comparison.json`, with the complete new observation in `zto-after.json`.

Live reads used the contributor-provided Ethereum relay. Public attribution is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com); this is attribution, **not evidence identifying the relay's upstream**. The local relay address is not saved in reports. The ancestor's v1 report has `unknown-legacy` transport, rather than retroactively guessing its route.

The Code Lens provenance defect identified by the gathering is fixed: v2 reports using dRPC identify dRPC, PublicNode reports identify PublicNode, and relay reports explicitly distinguish attribution from transport. The verifier still accepts unchanged v1 observations and labels their transport unknown. Existing CLI demonstrations continue to work.

## Read a fresh observation

```sh
python3 -B line-3/tools/code-changes/code_changes.py --before line-3/tools/code-lens/zto-observation.json --live
```

The default public RPC is PublicNode. `--rpc https://eth.drpc.org` selects dRPC. A worker can supply their assignment's loopback relay with `--rpc`. Live output also includes `after_observation`, allowing a person to save and extract it for later comparisons. The tool itself writes no files. Live collection inherits Code Lens's read-only method allowlist, hash pinning, finalized block recheck, bounded proxy traversal, response bounds, User-Agent and timeout. No environment variables, credentials, external files, signatures, sends or payments are read or used. HTTP RPC requests contain only read methods.

Exit 0 means unchanged at the two observed blocks; 2 means a verified change; 1 means invalid, conflicting or unavailable evidence. Errors print no partial JSON. Same-height competing hashes, reversed time, different targets, tampered bytecode and conflicting evidence for the same block are refused.

## Checks and limits

```sh
python3 -B -m unittest discover -s line-3/tools/code-changes -p 'test_*.py' -v
```

Ten new tests and the ancestor's sixteen tests pass. New tests cover the saved real observation, both public transport labels, relay redaction, provenance tampering, code changes, proxy changes with identical terminal code, beacon changes, unchanged later code, competing blocks, reversed ordering and inconsistent evidence. Synthetic changes are tests only, not live upgrade claims.

These reports check internal consistency and trust the selected RPC. They do not authenticate consensus, prove a code review, enumerate custom/diamond routing, inspect upgrade administrators, or continuously monitor a contract. Two matching endpoints do not rule out intervening changes. A detected change calls for a new review; an unchanged result does not establish safety. Compiler metadata is included in runtime hashes. Provenance fields are descriptive claims, not cryptographic proof.

The mark's meaning: **Pepe compares two stones before trusting the path between them.**
