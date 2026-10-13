# ZTO Path

Calculate exact-input ZTO/IMD swap estimates across a bounded set of Uniswap v4 bitmap words and initialized liquidity ticks. This extends ZTO Band beyond its single tick-spacing interval. It runs on Python 3.10+ with the standard library and the ordinary sibling files in `../zto-band/`; nothing needs installing.

## One command to see it work

From the repository root:

```sh
python3 -B line-1/tools/zto-path/zto_path.py --snapshot line-1/tools/zto-path/observation.json
```

This offline command replays real Ethereum state at **block 26,184,260** and estimates **100,000,000 ZTO → 1,196.130391948897309582 IMD**, with **1,250,000 ZTO** in pool fees and no unused input. ZTO Band refuses that same input at that same block because it leaves the first spacing interval. This amount demonstrates coverage; it is not a suggested trade. The supplied observation is historical, not a current price.

Use `--input IMD --amount 1000` for the reverse direction. It estimates **54,049,123.005084273670393622 ZTO**. All arithmetic uses integers; raw token amounts are decimal strings to preserve precision. Human amounts must be positive plain decimals with at most the token's on-chain decimal precision.

## What happened when tried

- **17 new offline tests passed**, and the ancestor's **16 tests still passed**.
- **11 of 11 live read-only V4Quoter comparisons matched exactly**, including tiny inputs, both directions, and amounts that traverse empty bitmap-word boundaries. `quoter-check.json` retains the exact calldata and raw return bytes at the observation's block hash.
- The captured words are **6, 7, 8**. The only initialized tick in that window is **128940**, with net liquidity **−1395488085257384418720526**. At that tick active liquidity becomes zero.
- `--amount 1000000000` crosses that real initialized tick, walks the known empty range, and exits **2** with `outside_coverage`, unused input, and a `partial` diagnostic. It supplies **no `estimate`** for the full requested input.
- The actual captured range has no intermediate initialized tick that changes liquidity while leaving it positive. Those transitions, both crossing directions, exact-boundary recrossing, and zero-liquidity gaps are tested with explicitly synthetic fixtures. No successful live full fill across such a transition is claimed.
- The gathering's unavailable historical quoter comparison was retried successfully using this assignment's archival transport: **8/8** ancestor comparisons matched at block 26,183,687. Evidence is in `band-recheck.json`; the old evidence remains untouched.

Run the offline checks:

```sh
python3 -B -m unittest discover -s line-1/tools/zto-path -p 'test_*.py' -v
```

## Fresh data and same-block comparison

```sh
python3 -B line-1/tools/zto-path/zto_path.py --live --amount 100000000 --save line-1/tools/zto-path/fresh-observation.json --check-quoter --save-check line-1/tools/zto-path/fresh-check.json
```

Default RPC source: [Ethereum PublicNode](https://ethereum-rpc.publicnode.com). `--rpc https://eth.drpc.org` selects the other public provider. `--block` accepts `finalized` (default), `safe`, `latest`, or a decimal block number. The assignment's machine-local archival transport was used for the checked-in observations, with the designated public endpoint recorded as source; the relay address is not a public citation or a portable dependency. The ancestor RPC class now permits this assignment's relay instead of the expired one identified by the gathering.

The collector checks Ethereum chain ID 1, pool identity and initialization, StateView's manager, ordered currencies, hook swap permissions, fees, decimals, and block consistency through ZTO Band. It captures every bitmap word in the selected range and every initialized tick those words declare. All state and quoter calls use the **same EIP-1898 block hash with `requireCanonical: true`**, followed by a block-header recheck. Missing archive state or a reorg is an error, never an excuse to mix blocks. An explicitly requested `--check-quoter` uses network even with `--snapshot`; without it snapshot mode is entirely offline.

Only `eth_chainId`, `eth_getBlockByNumber`, `eth_getLogs`, and `eth_call` are allowed. HTTP proxies from environment variables and redirects are disabled. No wallet, key, signature, transaction broadcast, approval, payment, or deployment is involved. Quoter simulation is discarded by the node. Each RPC call has a 30-second timeout; that is **not a total process deadline**.

## Coverage and output contract

- Default `--word-radius 1` captures the current bitmap word and one on each side. Radius is limited to **0–4** (at most nine words). At most **128 initialized ticks** and **256 calculation steps** are accepted; `--max-steps` can lower the latter bound. Snapshot and evidence JSON files must be below 100 KB.
- Traversal respects empty-word boundaries because fee and amount rounding happens per step. On a downward crossing it subtracts the signed liquidity delta and sets the stored tick to boundary minus one; upward crossing adds it. Known zero-liquidity ranges may be traversed without spending input. Missing bitmap coverage is never treated as zero liquidity.
- Snapshot validation requires contiguous centered words, every initialized tick and no extra tick, canonical ABI widths, positive gross tick liquidity, compatible gross/net liquidity, and nonnegative uint128 liquidity after crossings. Price limits remain strictly inside Uniswap's global square-root-price bounds.
- Exit **0**: fully consumed input, `status: estimated`, and `estimate`. Exit **2**: `outside_coverage`, `step_limit`, or `price_limit`, with only `partial` diagnostics and no full-fill estimate. Exit **1**: malformed/unsupported input, RPC failure, or quoter mismatch; JSON error goes to stderr.
- Reports include the block, source, fee, consumed/unspent input, output, final price/tick/liquidity, initialized crossings, and a per-step trace. Total fees include the directional protocol and LP fee. Input and output must fit the positive int128 pool-delta range.

These are core pool estimates, not executable quotes or minimum-received guarantees. The tool does not prepare transactions, simulate router settlement or token transfers, account for gas/MEV, select slippage tolerance, or establish that a future block has the same liquidity. Saved responses are RPC evidence, not cryptographic proofs. Only this static-fee, no-swap-hook ZTO/IMD pool is supported.

## Sources and reuse

Pool: `0x888b07bd282f587d3c6b0fcb23e7fc55bbb33abe8910dd7492db815dc8dc5592`, Ethereum PoolManager `0x000000000004444c5dc75cb358380d2e3de08a90`; ZTO and IMD addresses, StateView, and pool-key verification are retained in ZTO Band. V4Quoter: [`0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203`](https://etherscan.io/address/0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203).

- [Uniswap StateView](https://github.com/Uniswap/v4-periphery/blob/main/src/lens/StateView.sol): bitmap and tick-liquidity getter interfaces.
- [Uniswap TickBitmap](https://github.com/Uniswap/v4-core/blob/main/src/libraries/TickBitmap.sol): signed compression and one-word search behavior. The MIT notice is included in `LICENSE-Uniswap.txt`.
- [Uniswap SwapMath](https://github.com/Uniswap/v4-core/blob/main/src/libraries/SwapMath.sol) and [SqrtPriceMath](https://github.com/Uniswap/v4-core/blob/main/src/libraries/SqrtPriceMath.sol): the integer step arithmetic already implemented by ZTO Band.
- [Observed Ethereum block](https://etherscan.io/block/26184260).

`zto_path.py` contains the collector, validator, traversal, quoter comparison and CLI; `observation.json` and `quoter-check.json` make the real demonstration and comparisons reproducible without network. Keep the `zto-band` sibling folder when copying this tool to another worker. Tests use only standard-library `unittest`.
