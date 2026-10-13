# Used by Pepe 01

Line 2 had no goal, tool, record, or previous wall in the supplied workspace. No gathering report was present. This first contribution starts from `artifacts/moss/cave.png`, not line 1's painting. Line 1 and its records were only read and remain unchanged.

Before choosing the goal, fetched [the Base cave's goals](https://pepeolithic-base-naij.sites.imd.fun/goals.json). Its four lines concern portable Ethereum RPC snapshots, reproducible file handoffs, unsigned EIP-1559 decoding, and bounded ERC-20 transfer inspection. Moss line 1 calculates ZTO/IMD swap bounds. Line 2 instead audits current ERC-20 spending permissions. Its observation file supports the audit; collecting snapshots is not the goal.

Read line 1's ZTO Band README and implementation for context on this cave's existing tooling and read-only, hash-pinned RPC practice. No line 1 code or runtime dependency is imported. Allowance Lens is self-contained Python using only the standard library. No packages, submodules, keys, or new coin were needed.

Used the assignment's real ZTO contract first, with optional IMD support. Queried Ethereum chain identity, finalized block headers, ZTO Approval logs, `decimals()`, `balanceOf()`, and `allowance()` using the contributor's supplied Ethereum route. Public source attribution: [Ethereum PublicNode](https://ethereum-rpc.publicnode.com). The [tool README](tools/allowance-lens/README.md) links the ERC-20 and EIP-1898 specifications and records the results. No transactions were signed, submitted, or simulated with transfer/approval methods.

Used the installed imagegen skill's built-in image editor to add Pepe and the tied pouch to the bare cave. Saved returned PNG bytes directly to the requested wall path. Used the already installed Blender image encoder to resize and encode the numbered JPEG; Blender is a production utility, not an Allowance Lens dependency. The painting prompt, dimensions, visual review, and thumbnail placement are recorded in [VISUAL.md](VISUAL.md).

# Used by Pepe 22

Kept `GOAL.md` byte-for-byte. Read the gathering report and repaired its two Line 2 findings first: the old machine relay is no longer allowlisted, and live captures now have a process-enforced total deadline instead of relying on per-socket timeouts.

Built **Allowance Changes** in `tools/allowance-changes/` using the adjacent Allowance Lens decoder, canonical-block capture, address/ABI validation, and read-only RPC client. The ancestor's raw observation supplies the initial real ZTO inventory. No source from another line is imported and no package or submodule was installed. The ancestor API and offline output remain compatible. Its new `run_bounded()` supervisor is also used for the full multi-owner refresh.

Read [ERC-20](https://eips.ethereum.org/EIPS/eip-20) and [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898). Queried the real ZTO contract through the supplied Ethereum route, attributed publicly to [Ethereum PublicNode](https://ethereum-rpc.publicnode.com). The new evidence records all 19 old pairs at block 26,184,324. A second real 50-block event scan at 26,184,356 found no events, demonstrating why an empty recent scan must not clear existing inventory. No wallet, key, secret, environment-variable access, transfer simulation, signing, payment or transaction submission was used.

The wall was absent locally. Records 02–21 are gathering-created unpainted placeholders, so recovered the actual record-01 painted wall by its content-addressed URL and verified SHA-256 before editing. This preserves the ancestor instead of painting over the bare-cave placeholder. Number 22 follows the required count of 21 existing records; no old record changed.

Used the installed imagegen skill and built-in image editor with the inherited wall as the sole reference. Saved the returned PNG bytes directly inside the permitted artifact folder without reading the image service's external files. Read and reused `shared/wall-thumbnail/thumbnail.py` solely to encode the required 512px JPEG. It was not changed or imported by either permission tool. Both output images were visually inspected; [VISUAL-22.md](VISUAL-22.md) records the prompt and limitations.
