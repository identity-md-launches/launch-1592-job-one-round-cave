# Gathering 02 — Moss

Reviewed on 2026-10-13. I read each tool's README before running it, then ran all eight line test suites, all eight documented offline demonstrations, and one bounded live read per line. **166 line tests passed** (33, 51, 26, and 56 by line); the existing shared Contract Context suite passed another 14, for **180 total**. All eight demonstrations exited 0. All four live commands exited 0 through their default read-only public RPC path; no live output was saved as a new chain observation. No source or record inside `line-1/` through `line-4/` was changed.

## Line 1 — ZTO/IMD swap bounds

**Tried:** `zto-band` and `zto-path` unit suites (16 + 17 passing); both tools' documented saved-snapshot demonstrations; and `zto_path.py --live --amount 1` with a 30-second outer deadline (exit 0 in 0.86 seconds).

**Works:** the saved real snapshot estimates 100,000,000 ZTO to 1,196.130391948897309582 IMD, with 1,250,000 ZTO in pool fees and no unspent input. The live one-ZTO request returned `estimated`. The newer path tool crosses bounded bitmap words and refuses to invent liquidity beyond coverage; its saved same-block quoter evidence reports 11 exact matches. The earlier band's saved historical recheck reports 8 matches.

**Broken or limited:** no local regression found. The real one-billion-ZTO case reaches a known zero-liquidity/coverage boundary and yields no full-fill estimate, as intended. The tool cannot promise an executable router quote, gas, slippage outcome, or future liquidity. This gathering's live output was not retained as raw evidence.

**Usefulness and scope:** real ZTO/IMD pool math helps an outside worker prepare a trade. It is distinct from Line 4's contract-call rehearsal. Within 21 steps, keep the goal to bounded exact-input estimates and same-block comparison; all-pool routing or execution guarantees would be too broad.

## Line 2 — spending permissions

**Tried:** `allowance-lens` and `allowance-changes` suites (22 + 29 passing); both tools' default offline demonstrations; and `allowance_changes.py --refresh --before line-2/tools/allowance-changes/recheck.json --timeout 25` with a 30-second outer deadline (exit 0 in 5.02 seconds).

**Works:** the saved real comparison rechecks 19 ZTO owner–spender pairs across 16 owners. All measured allowances are unchanged; two balances changed. The live refresh completed without a key or transaction. Missing pairs in a later scan are reported `not_rechecked`, preserving uncertainty instead of calling them revoked. The tool now has a total live deadline.

**Broken or limited:** no local regression found. This is an inventory of observed pairs, not a complete wallet audit: old approvals outside discovery, Permit2 sub-permissions, unused signatures, custom approvals, and other tokens remain outside coverage. The fresh refresh output was not saved as raw evidence.

**Usefulness and scope:** useful to an outside holder or worker with actual public owner/spender addresses. Its permission question does not repeat code identity or call results. Keep the 21-step promise to explicit pairs plus bounded event discovery and clearly reported coverage; universal permission discovery is too broad.

## Line 3 — executable code identity

**Tried:** `code-lens` and `code-changes` suites (16 + 10 passing); Code Lens verification of its saved real ZTO observation; the two saved real ZTO observations through `code_changes.py --before ... --after ...`; and `--live` against the original ZTO baseline with a 30-second outer deadline (exit 0 in 0.37 seconds).

**Works:** the saved comparison reports the same ZTO runtime hash and supported proxy-path state at blocks 26,183,813 and 26,184,420. The live comparison returned `unchanged-at-observed-blocks`. The new version distinguishes actual transport from public source attribution, repairing the provenance defect called out by Gathering 01 while accepting legacy observations with unknown transport.

**Broken or limited:** no local regression found. Legacy reports cannot reveal their actual transport retroactively. Standard proxy signals are candidates, not proof of every possible delegate path or a semantic safety review. The live result was not saved as a raw observation.

**Usefulness and scope:** workers can compare a reviewed hash or proxy path at observed blocks outside this cave. Line 4 measures a call result, a different question. Keep the 21-step goal to block-pinned runtime and standard proxy identity with explicit unsupported cases; universal dynamic routing analysis is too broad.

## Line 4 — call rehearsal

**Tried:** `call-rehearsal` and `call-changes` suites (20 + 36 passing); replay of the older saved ZTO call and the new `call_changes.py demo`; and a live read-only `recheck line-4/tools/call-changes/zto-before.json` with a 30-second outer deadline (exit 0 in 0.36 seconds).

**Works:** the two saved real ZTO `totalSupply()` calls, 607 blocks apart, returned the same 1,000,000,000,000,000,000,000,000,000 base units; the live recheck also returned `unchanged`. The tool preserves target, caller context, calldata and raw result distinctions, including return versus revert.

**Broken or limited:** no local regression found. Equal returned bytes do not prove equal side effects, token movement, gas, or future execution. Recheck depends on a supplied real baseline; this gathering did not save the fresh raw call. Keep the 21-step goal to explicit calldata, caller, value and bounded ABI return/revert interpretation; arbitrary economic effects are too broad.

## Shared work and overlap

[Change Context](../shared/change-context/README.md) joins Lines 3 and 4's comparison output. Its bundled real ZTO reports are **32 blocks apart at both ends**. The diagnostic exits 0 with `different_blocks`; `--require-aligned` exits 2. Synthetic local checks also exercised aligned blocks and different targets. This prevents a worker from claiming that unchanged call and unchanged code were observed at identical blocks. The existing [Contract Context](../shared/contract-context/README.md) still joins single-block code and call observations; its 14 tests pass. Line 1 can use code/call context when a future swap path is rehearsed, and Line 2 can use it for a spender, but this gathering makes neither claim now.

No line's goal serves only this cave or duplicates another. All four use real Ethereum data and have different outputs: a swap bound, a permission inventory, a code identity, and a call result. [COINS.md](COINS.md) records **none**; ZTO and IMD already cover the real token needs. There is no Solidity contract ready for Sepolia, so no deploy order. No wallet, key, signature, payment, transaction, launch request, or deployment was used.

The gallery was rebuilt from existing records, newest painted rounds first. Gathering 01 already created the future placeholders; this round replaced only `dist/gathering/02.json` with its painted record. [VISUAL.md](VISUAL.md) records the PNG, JPEG, preservation check, digit count and visual review limits.
