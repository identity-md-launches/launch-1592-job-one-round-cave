# Local checks — Pepe 22

Completed locally on 2026-10-13. These are contributor checks, not independent certification. Machine-readable results: `check-results-22.json`.

- New tool: **17/17 tests pass** with `python3 -B -m unittest discover -s line-1/tools/zto-path -p 'test_*.py' -v`.
- Ancestor regression: **16/16 tests pass** with `python3 -B -m unittest discover -s line-1/tools/zto-band -p 'test_*.py' -v`.
- Real same-block comparison: **11/11 outputs equal V4Quoter**, at block **26184260**, hash `0xcd8e7e4ba940af1feac8d6b441c37ef0230c4bcd2fd55d36376038a4b4c36650`. Calls cover both directions, 1-raw-unit inputs, 100 million and 500 million ZTO, and 1000 and 5000 IMD. Exact requests/results are retained in `tools/zto-path/quoter-check.json`.
- Gathering repair: the old relay allowance is replaced with this assignment's relay. The original historical comparison now succeeds: **8/8 outputs equal V4Quoter** at block 26183687. Evidence: `tools/zto-path/band-recheck.json`. Public defaults and ancestor evidence are unchanged.
- The new README's offline command exits **0**, gives `estimated`, and reports **100000000 ZTO → 1196.130391948897309582 IMD**, with **1250000 ZTO** in fees and no unspent input. ZTO Band refuses this size at the same block.
- The real **1000000000 ZTO** request crosses tick 128940, removes all active liquidity, and reaches the recorded coverage limit. It exits **2**, reports unspent input and a `partial` diagnostic, and includes **no `estimate`**. Missing data never becomes assumed empty liquidity.
- Negative bitmap compression, both signed crossing directions, exact-boundary crossing, zero-liquidity gaps, step limits, malformed/omitted tick data, conservation, offline isolation, RPC allowlisting, hash pinning and reorg refusal are covered. Transitions not present in the captured real range are explicitly synthetic tests.
- Both PNG paths decode as **1254 × 1254, 8-bit RGB**, matching the cave. Every PNG chunk CRC and decompressed raster size checked. Both contain identical **2,857,306-byte** output. SHA-256: `1250c32eba2c719780a358071cad37f9c6d4ff54eecec10a592c53da14107c55`.
- JPEG: **512 × 512**, baseline, 8-bit RGB, **54,443 bytes**. SOI/EOI and frame dimensions checked; decoded preview visually inspected.
- Record: only **22.json** added; exact requested top-level and attribute keys, numeric Number 22, and matching image SHA-256. Twenty-one older records remain unchanged, including the placeholders.
- Goal verified byte-for-byte against the starting revision. Changes remain within the allowed line-1 paths. No configuration, library, other line, shared source, or gathering file changed. No new dependency or submodule. Every file in `line-1/` and `dist/line-1/` is below 100,000 bytes.
- Required PNG outputs exist and remain untracked. The numbered JPEG is beside its record under the explicit FILES requirement. No extra workspace image was retained.
- Full wall and thumbnail inspected. Visual requirements and preservation limits are recorded in `VISUAL-22.md`; no unmet visual requirement was observed. Pixel-identical preservation is not asserted for a generative edit.

The calculator remains bounded to the real static-fee ZTO/IMD pool and recorded bitmap coverage. It does not execute a swap, prove RPC truth, or guarantee future token receipt. No transaction was signed or sent.
