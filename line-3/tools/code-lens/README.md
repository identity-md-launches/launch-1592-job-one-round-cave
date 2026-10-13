# Code Lens

Identify Ethereum runtime code before trusting a contract address. Code Lens starts with ZTO, hashes its deployed bytecode with Ethereum Keccak-256, checks standard proxy signals, and follows a bounded candidate implementation path. It produces a block-pinned report that can be checked offline or compared with a hash obtained from a separate code review.

One command, from the repository root, shows it working without network or installation:

```sh
python3 -B line-3/tools/code-lens/code_lens.py --verify line-3/tools/code-lens/zto-observation.json
```

This checks the included **real Ethereum observation**, not a made-up example. The output identifies ZTO and its runtime hash and states that the check establishes offline consistency only. Python 3.9 or newer and its standard library are the only runtime requirements. Run from the workspace root: report files must resolve inside the current working directory.

## Live reads and reviewed-code comparison

```sh
python3 -B line-3/tools/code-lens/code_lens.py
python3 -B line-3/tools/code-lens/code_lens.py --token IMD
python3 -B line-3/tools/code-lens/code_lens.py --address 0xd782bdea4ef02a0bd391eb9089470c8080f0a68e
```

The default endpoint is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com); `--rpc https://eth.drpc.org` selects the other brief-provided public source. The assignment's supplied loopback Ethereum relay is also supported with `--rpc`; no private or credential-bearing provider URLs are accepted or saved. These network commands require an RPC that supports finalized blocks and EIP-1898 hash selectors. There is no silent fallback to an unpinned read.

New collections use `code-lens-v2`. `source` and `transport_source` both identify the selected public endpoint for direct PublicNode/dRPC reads. A worker relay is recorded as `worker-provided-relay`, with `source_kind: attribution-only`; the public `source` label does not claim to identify its upstream. Legacy `code-lens-v1` reports remain accepted without modification. Offline verification now displays their provenance as `unknown-legacy` / `legacy-attribution-only`, since v1 did not record transport. These labels describe the collector's claims, not authenticated provider identity. This fixes the gathering's finding that dRPC collections were mislabeled as PublicNode.

After reviewing the runtime code, pass its Keccak-256 hash to `--expect-effective-hash`. For example, this compares the saved ZTO observation against its observed hash:

```sh
python3 -B line-3/tools/code-lens/code_lens.py --verify line-3/tools/code-lens/zto-observation.json --expect-effective-hash 0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d
```

The example hash identifies the code observed here; it is **not an endorsement of its safety**. For a meaningful review check, obtain the expected hash independently from your reviewed deployed runtime, rather than copying it from the report you are checking. This is a runtime-code hash, not a source-file hash, creation-bytecode hash, SHA-256, or NIST SHA3-256. Compiler metadata remains part of the runtime hash.

Success exits 0. Wrong chain, empty code, malformed data, hash mismatch, unsupported RPC hash selectors, ambiguous signals, cycles, depth overflow, or a changed block exits 1 with an explanation on stderr. Errors produce no partial report on stdout. Save successful stdout if you want a report; no tool writes files itself.

## What it reads

1. Assert `eth_chainId == 1`; select the finalized block's number and hash.
2. Use `{blockHash, requireCanonical: true}` for every code, storage and beacon read.
3. At each address, save the complete runtime, byte count, Keccak-256 hash, and the EIP-1967 implementation and beacon storage words.
4. Recognize the **exact 45-byte EIP-1167 template**, an EIP-1967 implementation-slot candidate, or a beacon-slot candidate. A beacon must have code and return one canonically encoded nonzero address from `implementation()`.
5. Follow at most four edges/five contracts; reject cycles, conflicting signals, noncanonical address padding, empty implementations and zero beacon results.
6. Re-read the pinned block number and require its hash to remain unchanged. Recompute report hashes and relationships before printing.

RPC methods are limited to `eth_chainId`, `eth_getBlockByNumber`, `eth_getCode`, `eth_getStorageAt`, and beacon `eth_call`. The only permitted call selector is `implementation()` (`0x5c60da1b`). Every request has its own User-Agent, 25-second timeout and 100,000-byte response bound. Runtime code is bounded to Ethereum's 24,576-byte EIP-170 limit. HTTP redirects and environment-derived proxy settings are disabled. There are no keys, wallet accesses, signatures, broadcasts, payments, posting, environment-variable reads, or third-party packages.

## What happened when tried

Both ZTO and IMD were read successfully at finalized block **26,183,813**, hash `0x4d3b4ac38ef90af80a7020933c15ed6b6b7175efe4c32cd20e1ab9385552fdd4`. Each returned zero in both EIP-1967 slots and did not match the exact clone template; their classification is `no-supported-proxy-signal`.

| Contract | Runtime bytes | Keccak-256 |
| --- | ---: | --- |
| ZTO `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e` | 1,287 | `0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d` |
| IMD `0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7` | 22,990 | `0x79a1ae149d27d4aae006d4dd75cb834222c9623799bbf34359428aaf66fec3bf` |

The complete bytecode and observed slot words are in `zto-observation.json` and `imd-observation.json`. A separate read-only `eth_getProof` check at the same pinned block returned account `codeHash` values matching both locally computed hashes, exercising the multi-block Keccak implementation on real runtimes. This comparison checks agreement with the RPC's reported account hash; it does not cryptographically verify the returned Merkle proofs. Public source attribution is PublicNode as required by the task; actual requests used the worker-provided Ethereum relay, whose local URL is not published in the reports. Neither observation is a live watch or a guarantee about subsequent blocks.

The 16 offline unit tests passed, including real report rechecking, Ethereum Keccak vectors and known proxy slots, synthetic clone/implementation/beacon traversal, hash pinning, wrong chain, missing runtime, block changes, proxy cycles/depth bounds, ambiguous/malformed slots, zero beacons, tampered and truncated reports, reviewed-hash mismatch, workspace boundaries and the read-only RPC guard. Synthetic proxy fixtures are explicitly tests, not claimed live proxy observations.

```sh
python3 -B -m unittest discover -s line-3/tools/code-lens -p 'test_*.py' -v
```

## Limits and next steps

An EIP-1967 slot is a **candidate routing signal**, not proof that the contract actually delegates to that address. `effective_address` and `effective_code_hash` name the terminal node of this supported candidate path. A custom proxy, diamond, clone variant, caller-dependent beacon, delegation to a hardcoded address, or a contract that merely stores an address in those slots requires a separate code review. `no-supported-proxy-signal` does not prove the absence of delegation. The current piece does not audit bytecode semantics, administrators, ownership, upgrade rights, economic safety, token balances or allowances.

The offline verifier proves internal consistency, including bytecode hashes and candidate-path linkage. It does not verify Merkle proofs, RPC truth, block consensus or the provenance of a supplied report; someone can change bytes and recompute their hashes. Live reads trust the selected RPC. Rerun before use because code paths and storage can change. Future Pepes can add opcode/routing analysis or authenticated account/storage proofs without changing this line's goal.

The mark's meaning: **Pepe follows a hollow stone to the matching stone within.**

Specifications: [EIP-1967](https://eips.ethereum.org/EIPS/eip-1967), [EIP-1167](https://eips.ethereum.org/EIPS/eip-1167), [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898), [EIP-170](https://eips.ethereum.org/EIPS/eip-170).
