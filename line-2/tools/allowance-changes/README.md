# Allowance Changes

Compare ERC-20 spending permissions across two Ethereum blocks, and refresh a saved owner–spender inventory without forgetting approvals that have fallen outside a recent event window. ZTO is the default demonstration; observations for IMD also work. All operations are read-only. Python 3.10+ and its standard library are sufficient; the adjacent Allowance Lens module is the only repository dependency.

## One command to see it working

Run from the repository root:

```sh
python3 -B line-2/tools/allowance-changes/allowance_changes.py
```

No installation or network is needed. This compares two **real saved Ethereum observations**, not synthetic example balances. The exact report is in `example-report.json`.

| What was tried | Observed result |
| --- | --- |
| Before: ancestor observation, block 26,183,751 | 19 ZTO owner–spender pairs, 16 owners |
| After: fresh finalized block 26,184,324 | All 19 pairs rechecked, using one canonical block hash |
| Allowance comparison | All 19 allowances unchanged |
| Balance comparison | Two pair balances changed; no spendable upper bound changed |
| Active allowances after refresh | Three: two on empty balances, one with a positive balance |
| Fresh 50-block discovery, ending at block 26,184,356 | Zero Approval events; this does **not** clear the saved inventory |

The after observation is at **2026-10-13 14:59:35 UTC**, hash `0x2e4f68bb511a5840f25f4df22a81a6a18f4eb9d76bab521ed36dac3d6ef023ad`. Capture used the contributor's Ethereum route, publicly attributed to [Ethereum PublicNode](https://ethereum-rpc.publicnode.com). `recheck.json` holds every raw balance/allowance return, calldata, owner, spender and block header. It contains 16 validated per-owner Allowance Lens observations at the same block. No invented owner address, test wallet, key, signature or transaction is used.

The extra real capture `lens-recheck.json` demonstrates why missing observations must remain unknown:

```sh
python3 -B line-2/tools/allowance-changes/allowance_changes.py --before line-2/tools/allowance-lens/observation.json --after line-2/tools/allowance-changes/lens-recheck.json
```

This reports **19 `not_rechecked` pairs**, rather than claiming their approvals were revoked. It compares different coverage at different blocks; it does not claim those omitted allowances were read at the newer block.

## Refresh an actual inventory

```sh
python3 -B line-2/tools/allowance-changes/allowance_changes.py --refresh --before line-2/tools/allowance-changes/recheck.json --save line-2/tools/allowance-changes/next-recheck.json
```

This live command uses the public endpoint by default, reads all previously listed pairs at one finalized header, prints their comparison, and saves raw evidence only after the entire refresh validates. The output path must be new and within the current workspace. On this assignment machine, append `--rpc http://127.0.0.1:35045/rpc/1`; this relay is a local transport, not a portable source or default. `--rpc https://eth.drpc.org` is the other public choice. No endpoint or proxy is loaded from environment variables.

Use `--before` with an existing Allowance Lens observation or an Allowance Changes inventory; the live command requires it explicitly. A saved refresh can be the input for the next refresh. An empty inventory is rejected because no actual owner/spender pairs were supplied. Use Allowance Lens for bounded discovery or explicit owner/spender reads first. `--block` accepts a decimal block number or `finalized`, `safe`, `latest`; numeric requests must match the returned header. Finalized is the default. Historical reads require archival state and EIP-1898 support.

The default total live-read deadline is **90 seconds**, adjustable with `--timeout` to a positive finite value at most 600 seconds. A spawned worker contains the whole capture, including all owners, DNS and response bodies. The parent terminates it on expiry, with up to about 1.1 seconds of bounded process cleanup plus scheduling overhead. A timeout produces an error and no saved partial result. The ancestor CLI now uses this same deadline mechanism. The library's low-level `capture()` and `refresh()` functions remain synchronous; use `run_bounded()` for an external deadline and the usual `if __name__ == '__main__'` guard in a calling script.

## Interpretation

The `change` field and `counts` describe **allowances**, while the separate balance and spendable deltas describe exposure changes. Raw amounts and signed deltas are exact integer strings, avoiding floating-point and JSON precision loss.

| Change | Meaning |
| --- | --- |
| `unchanged` | Both measured allowances equal, even if the balance changed |
| `became_active` | Measured allowance changed from zero to positive |
| `became_zero` | Measured allowance changed from positive to zero |
| `increased` / `decreased` | Positive allowance grew / shrank |
| `newly_observed` | Pair measured only in the after input; previous state unknown |
| `not_rechecked` | Pair measured only in the before input; current state unknown |

`became_zero` does not establish that a user revoked anything: spending can reduce an allowance too. `newly_observed` does not establish when an approval was created. A zero balance does not cancel a permission. Each same-block spendable upper bound is `min(allowance, balance)`, under standard ERC-20 assumptions. Owner totals use only the intersection of measured pairs and cap summed allowances at that owner's balance, so overlapping spenders and missing coverage cannot fabricate a reduction in exposure.

Offline comparison validates both raw inputs through Allowance Lens, rejects mixed chains/tokens/decimals/blocks within inventories, duplicate pairs, inconsistent balances, backwards blocks/timestamps, and conflicting same-block state. The live refresh verifies the before header is still canonical, uses `requireCanonical: true` on all state calls, checks every owner against the chosen header, then checks that header again. Failed RPCs or validations fail the whole refresh. There is no log scan during refresh and no implicit expansion of the inventory.

The tool is bounded to 64 pairs, 64 per-owner observations, and 96 KiB per input/saved evidence file. Response and method limits come from Allowance Lens. A complete report has exit status **0**, including unknown/missing pairs or nonzero permissions. Validation, network, deadline and file failures have status **1**; argparse usage errors use **2**. Reports go to stdout; failures go to stderr.

Every report says `complete_wallet_audit: false`. Refresh checks the supplied inventory; it does not find additional spenders, Permit2 sub-permissions, unused signed permits, custom authorizations, other tokens or other chains. Returned values are trusted RPC evidence, not cryptographic proofs or guarantees of successful token transfers. Offline replay describes the captured historical blocks.

## Checks

```sh
python3 -B -m unittest discover -s line-2/tools/allowance-changes -p 'test_*.py' -v
python3 -B -m unittest discover -s line-2/tools/allowance-lens -p 'test_*.py' -v
```

Locally, **29 new tests and all 22 ancestor tests passed**. Tests cover the real saved reads and the empty-window example, every allowance transition, precise large integers, missing coverage, overlapping spenders, wrong chain/token/decimals, inconsistent same-block state, reorgs, hash-pinned refresh, CLI offline isolation, file boundaries, overwrite refusal and actual process termination on a short deadline. Modified fixture values in edge-case tests are explicitly synthetic and are never saved as on-chain evidence.

The repaired Allowance Lens live CLI also completed a fresh 50-block capture through the current relay. Its original offline output still matches the ancestor's `example-report.json` exactly. No packages, services, keys, wallet software, deployment or submission are required.

Semantics are based on [ERC-20](https://eips.ethereum.org/EIPS/eip-20) and canonical hash-pinned reads on [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898). Implementation reuses the adjacent ancestor tool; see [USED.md](../../USED.md) for provenance.
