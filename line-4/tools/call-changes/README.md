# Call Changes

Check whether the **same Ethereum contract call** returned different bytes or changed between returning and reverting at two finalized blocks. This gives a worker a concrete way to recheck an earlier rehearsal before a person decides whether to submit anything. It uses Python 3.9+ and only the standard library. Copy this entire folder to use it independently; there are no downloads, packages, services or keys required for the offline demo.

From the repository root, run:

```sh
python3 -B line-4/tools/call-changes/call_changes.py demo
```

This command performs **no network requests**. It compares two saved real ZTO `totalSupply()` observations, reports `unchanged`, and prints both block hashes, both decoded values, the time between them and a signed integer delta of `0`. The observations are actual provider responses; synthetic cases appear only in the tests.

## Recheck an actual proposed call

First use the existing [Call Rehearsal](../call-rehearsal/README.md) tool to save a call observation with the intended target, public sender, calldata and native value. This tool repeats those exact fields; it never supplies a sender or recipient for you. ZTO is the supplied default demonstration, with its real Ethereum address `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`. IMD observations and other supported custom calls work too.

For a fresh, read-only ZTO comparison:

```sh
python3 -B line-4/tools/call-changes/call_changes.py recheck line-4/tools/call-changes/zto-before.json --save line-4/tools/call-changes/zto-next.json
```

`--save` is optional and creates a **new** raw Call Rehearsal observation. Repeating this command with an existing destination fails before networking. Choose a new filename or omit `--save`. A valid inconclusive or reverted observation can be saved; saving does not imply success. Nothing is signed, deployed or broadcast.

`--block` accepts `finalized` (default) or a canonical hexadecimal block number. The explicit height must be at or below the provider's finalized head and at or after the baseline observation. For example, this real block was successfully rechecked during development:

```sh
python3 -B line-4/tools/call-changes/call_changes.py recheck line-4/tools/call-changes/zto-before.json --block 0x18f8b04
```

Historical state may later become unavailable at a public endpoint. There is no fallback to another block. The collector confirms Ethereum mainnet, resolves the selected header, checks code and executes the call using that exact block hash with `requireCanonical: true`, then rechecks the header. Use `--rpc https://eth.drpc.org` to select the other supported provider; PublicNode is the default and the actual selected endpoint is saved.

For two observations already on disk:

```sh
python3 -B line-4/tools/call-changes/call_changes.py compare line-4/tools/call-changes/zto-before.json line-4/tools/call-changes/zto-after.json
```

## Reading the result

| Verdict | Exit | Meaning |
| --- | ---: | --- |
| `unchanged` | 0 | Same execution category and exact return/revert bytes. This can include two false returns or two reverts. |
| `changed` | 1 | Different bytes, or a transition between return and revert, at different blocks. |
| `inconclusive` | 2 | RPC failure, unexpected ABI return, or two reverts with missing revert bytes. |
| `inconsistent_observations` | 2 | The same call at the same block produced conflicting execution evidence. |
| Input, transport or consistency error | 2 | JSON error on stderr; no comparison claimed. |

An exit of 0 means **the observations agree**, not that a transaction is successful or safe. Inspect each `result.status`, including `returned_false` and `reverted`. Unknown/custom revert bytes are compared without guessing an ABI. Explicit empty revert data (`0x`) differs from missing data. Error message wording alone is not a contract-result change.

The target, presence and value of sender, native value, calldata, return interpretation and mainnet chain identity must match. Hexadecimal case is normalized. Reversed time, conflicting block identity and invented interpretation fields are rejected. A saved interpretation is never trusted: the tool decodes the raw outcome again. Comparisons across providers retain both source labels and flag `same_provider: false`.

## What happened when tried

On 2026-10-13, a live PublicNode recheck of the ancestor's ZTO observation succeeded:

- Before: block **26,183,845**, hash `0x644962fe0c9268aea3a3222fc32fc97a53030aab1f5298f5a570cf540bdaaeea`.
- After: block **26,184,452**, hash `0xfdc7146392fc1620795459532938a9cd6410f975c9a2b33b0e8d042f6ce8a7b8`.
- Both returned **1000000000000000000000000000** base units; **607 blocks / 7,296 seconds** apart. Verdict `unchanged`; delta `0`.
- A second real request explicitly selected `0x18f8b04` and returned the same header and value. Its raw observation is `zto-pinned-recheck.json`; compare it with `zto-after.json` to reproduce the same-block check offline.
- **36 new offline tests passed**, plus all **20 ancestor tests**. They cover changed integers, false returns, same-block conflicts, missing revert bytes, unavailable state, ABI mismatch, pinning, reorg rejection, explicit block selection, caller preservation, strict JSON, file bounds and CLI exit codes. Changed-result and failure branches are synthetic test cases, not claims of observed live changes.

```sh
python3 -B -m unittest discover -s line-4/tools/call-changes -p 'test_*.py' -v
```

## Limits and provenance

This compares call results, not internal execution or economic side effects. Equal bytes do not prove equal runtime code, token movement, balances, allowances, gas or safety. A historical result cannot guarantee future inclusion. No receipt, trace, state diff, gas estimate, signature or cryptographic authenticity proof is produced. Provider-default gas/fee context is not fixed by the original observation format; disagreements may reflect those defaults. Same-block conflicts are therefore reported as inconsistent evidence, not a contract state change. Revert classification and basic ABI decoding inherit the original tool's bounded behavior.

Files must resolve inside the current working directory. Input observations and RPC responses are capped at 90,000 bytes; each hex value is capped at 32 KiB. Duplicate JSON keys and non-finite numbers are rejected. Output creation is exclusive. The transport allows only `eth_chainId`, `eth_getBlockByNumber`, `eth_getCode` and `eth_call`, disables redirects and environment proxy discovery, and sends `Pepeolithic-CallRehearsal/1.0` as its User-Agent. No environment variables, wallet files or secrets are read. Each HTTP request has a 25-second socket timeout; **this is not a total runtime deadline**. The two development live checks also used an external 55-second process deadline and completed successfully.

`rehearse_core.py` is a byte-for-byte, reviewed copy of `../call-rehearsal/rehearse.py`, kept here so this folder is portable. `zto-before.json` is an exact copy of the ancestor's saved real observation. `zto-after.json` and `zto-pinned-recheck.json` were captured by this tool. The original tool and observations were not edited. File hashes and checks are recorded in the line's [CHECKS-22.md](../../CHECKS-22.md).

Protocol references: [EIP-1898 hash-pinned state queries](https://eips.ethereum.org/EIPS/eip-1898) and [Ethereum JSON-RPC](https://ethereum.org/developers/docs/apis/json-rpc/).
