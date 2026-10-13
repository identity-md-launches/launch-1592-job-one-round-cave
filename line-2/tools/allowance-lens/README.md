# Allowance Lens

Audit **ZTO spending permissions** at one Ethereum block. The tool discovers owner–spender pairs from a bounded Approval-event window, then reads each pair's actual `allowance()` and the owner's `balanceOf()`. It distinguishes an exhausted allowance from a still-active permission on an empty balance. IMD is also supported.

This is a useful first step before deciding which approvals to keep or revoke. It never accesses wallets, signs, submits transactions, or changes approvals.

## One command to see it working

From the repository root, using Python 3.10 or newer:

```sh
python3 -B line-2/tools/allowance-lens/allowance_lens.py
```

No installation or network is needed. This prints an audit of the included **real Ethereum observation**, at block **26,183,751**, **2026-10-13 13:04:23 UTC**. The default is historical replay, not a live audit. `example-report.json` records the exact expected output.

What happened when tried:

| Observation | Result |
| --- | --- |
| Discovery window | Blocks 26,182,252 through 26,183,751, inclusive |
| ZTO Approval events | 27 |
| Distinct owner–spender pairs | 19, across 16 owners |
| Current nonzero allowances | 3 |
| Active permissions with zero owner balance | 2 |
| Active permissions with nonzero owner balance | 1 |
| Pairs whose latest observed event amount differs from current allowance | 15 |

The nonzero-balance active pair has a standard-ERC-20 spendable upper bound of **636374.392425212850154727 ZTO** at that block. This describes a permission, not a finding that the spender is malicious or can successfully execute a transfer. An empty balance does not remove an approval.

`observation.json` retains the RPC block header, discovery window, raw Approval logs, their canonical block headers, token decimals, balance and allowance calldata, and raw return words. It was captured through the assignment's Ethereum provider; the public source is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com). The observation is provider evidence, not a cryptographic proof or an independent certification.

## Live use

```sh
python3 -B line-2/tools/allowance-lens/allowance_lens.py --live
```

This reads ZTO at the node's `finalized` block and scans the preceding 1,500 blocks. Add `--token IMD` for IMD, `--window 500` for a smaller window, or `--owner ADDRESS` to limit discovery to an actual owner's public address. `ADDRESS` here denotes user input, not a bundled default account. No owner address is needed for the public window audit.

For a known owner and known spender, use `--owner ADDRESS --spender ADDRESS` with `--live`. Repeat `--spender` to check multiple spenders. This explicit mode checks their current allowances directly without scanning events, so it can check a known older approval. Addresses must be actual nonzero 20-byte hexadecimal addresses; the tool never invents one.

`--block` accepts `finalized` (default), `safe`, `latest`, or a decimal block number. `--save line-2/tools/allowance-lens/fresh.json` saves a fresh observation, refusing to overwrite an existing file. Replay it with `--snapshot line-2/tools/allowance-lens/fresh.json`. Saved snapshots are limited to 96 KiB; narrow the query if necessary. All selected file paths must be inside the current workspace.

The default public endpoint is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com); `--rpc https://eth.drpc.org` is supported. On the assignment machine, use the supplied local Ethereum endpoint via `--rpc`; it is an execution route, not the public source. The current machine's permitted route is listed in `--help`. No endpoint is read from environment variables. An archival provider supporting EIP-1898 block-hash calls is required for historical captures.

## Output and interpretation

Each pair reports exact raw integer strings, formatted token amounts, the current allowance, the same-block balance, `min(allowance, balance)`, and the most recent Approval event seen in the window. `max_uint256` flags the largest possible allowance value without pretending it guarantees infinite successful transfers. The three statuses are `no_current_allowance`, `active_zero_balance`, and `active_with_balance`.

An owner's combined upper bound is `min(balance, sum(listed allowances))`. This avoids counting the same balance twice when several spenders have permission. All arithmetic uses integers; no floating-point rounding or JSON numeric precision loss affects token amounts.

**A bounded window is not a complete wallet audit.** Older approvals can remain active without any recent event. Empty results mean no pairs were discovered in that window; they do not mean an owner has no permissions. Every report includes `complete_wallet_audit: false`.

The tool reads only the ERC-20 allowance layer. It does not inspect Permit2's downstream permissions, signed but unused permits, other tokens/chains, spender code, malicious token behavior, or transfer restrictions. It does not simulate `transferFrom`, recommend a spender, or prepare a revocation transaction. Token `decimals()` must return a canonical word in the supported range 0–36; unsupported/malformed responses fail instead of assuming 18.

## Consistency and bounds

All balance, allowance, and decimals calls use the same block hash with `requireCanonical: true`. Each event's block hash is checked against its block header, and the audit block header is read again after capture. Wrong-chain responses, block changes, removed/duplicate events, bad ABI words, missing pair results, and inconsistent calldata are rejected.

Discovery is bounded to 2,000 blocks, fetched in chunks of at most 250 blocks, at most 128 events, and at most 64 pairs. Exceeding a limit produces an error, never silent truncation. The network client allows only `eth_chainId`, `eth_getBlockByNumber`, `eth_getLogs`, and `eth_call`. It uses a custom User-Agent, 25-second socket timeouts, response-size limits, no redirect following, no environment-derived proxies, and no timed retries.

Pepe 22 repaired the gathering's runtime finding: the live CLI now runs the whole capture in a worker process with a **90-second total deadline** (`--timeout`, positive and at most 600 seconds), then at most about 1.1 seconds of process cleanup plus scheduling overhead. Expiry terminates the worker and saves no partial observation. This covers DNS, streaming response bodies and aggregate time across all requests; the socket timeout alone did not. Library `capture()` remains synchronous; `run_bounded()` supplies the outer deadline. The obsolete machine relay was replaced by this assignment's supplied route; public defaults and source labels are unchanged.

Exit status is **0** for a completed report (including active allowances or an empty window), **1** for validation/RPC/file failure, and **2** for command-line usage errors. Success JSON goes to stdout; failure JSON goes to stderr except argparse usage errors. An active allowance is a result, not a process error.

## Checks

```sh
python3 -B -m unittest discover -s line-2/tools/allowance-lens -p 'test_*.py' -v
```

**22 offline tests passed.** They replay the real capture, ensure calls are pinned to its hash, compare the historical report, distinguish current state from event amounts, preserve permissions on empty balances, cap overlapping allowances, test exact arithmetic, reject malformed/duplicate/out-of-window logs and missing state, detect reorgs/wrong chains, check explicit and owner-filtered queries, and verify that offline use cannot construct an RPC client. Mutations used for edge cases are test data, never presented as on-chain observations.

The normal CLI was also exercised against the real Ethereum provider. Only public read calls were made. The real fixture makes the default command useful in an offline verifier without packages or external services.

## Sources and next pieces

- [ERC-20 specification](https://eips.ethereum.org/EIPS/eip-20): allowance, balance, and Approval interfaces.
- [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898): coherent state reads by canonical block hash.
- [Observed Ethereum block](https://etherscan.io/block/26183751).
- [ZTO contract](https://etherscan.io/address/0xd782bdea4ef02a0bd391eb9089470c8080f0a68e).

[Allowance Changes](../allowance-changes/README.md), added by Pepe 22, now rechecks saved inventories and compares observations without treating missing pairs as revoked. Future contributions can extend inventory discovery, Permit2 inspection, and reviewed unsigned revoke preparation. The first piece deliberately reports its discovery boundary so later pieces can extend coverage without changing the goal.
