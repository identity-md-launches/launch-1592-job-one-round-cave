#!/usr/bin/env python3
"""Join Code Changes and Call Changes reports without inventing same-block evidence."""

import argparse
import json
from pathlib import Path
import re
import sys


ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}\Z")
HASH = re.compile(r"0x[0-9a-fA-F]{64}\Z")
NUMBER = re.compile(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)\Z")
LIMIT = 96_000


class EvidenceError(ValueError):
    pass


def unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise EvidenceError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def reject_constant(value):
    raise EvidenceError(f"non-finite JSON number: {value}")


def load_report(filename):
    path = Path(filename).resolve()
    if not path.is_relative_to(Path.cwd().resolve()):
        raise EvidenceError("report path must stay inside the current workspace")
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise EvidenceError("report missing or exceeds 96,000 bytes")
    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=unique_pairs,
                          parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid JSON: {exc}") from exc


def block(obj, label):
    if not isinstance(obj, dict) or not isinstance(obj.get("number"), str) or not NUMBER.fullmatch(obj["number"]):
        raise EvidenceError(f"{label}: invalid block number")
    digest = obj.get("hash")
    if not isinstance(digest, str) or not HASH.fullmatch(digest):
        raise EvidenceError(f"{label}: invalid block hash")
    return {"number": int(obj["number"], 16), "hash": digest.lower()}


def address(value, label):
    if not isinstance(value, str) or not ADDRESS.fullmatch(value):
        raise EvidenceError(f"{label}: invalid address")
    return value.lower()


def join(code, call):
    if not isinstance(code, dict) or code.get("schema") != "code-changes-v1":
        raise EvidenceError("expected a Code Changes v1 report")
    if not isinstance(call, dict) or call.get("schema") != "call-changes-v1":
        raise EvidenceError("expected a Call Changes v1 report")
    if type(code.get("chain_id")) is not int or type(call.get("chain_id")) is not int:
        raise EvidenceError("missing numeric chain identity")
    if code["chain_id"] != 1 or call["chain_id"] != 1:
        raise EvidenceError("reports must describe Ethereum mainnet")
    code_target = address(code.get("target"), "code target")
    call_target = address(call.get("call", {}).get("to") if isinstance(call.get("call"), dict) else None,
                          "call target")
    if code.get("status") not in ("changed", "unchanged-at-observed-blocks"):
        raise EvidenceError("unknown code comparison outcome")
    if call.get("verdict") not in ("changed", "unchanged", "inconclusive", "inconsistent_observations"):
        raise EvidenceError("unknown call comparison outcome")
    if type(code.get("effective_code_changed")) is not bool or type(code.get("candidate_path_changed")) is not bool:
        raise EvidenceError("missing code change flags")
    changes = code.get("changes")
    if not isinstance(changes, list) or bool(changes) != (code["status"] == "changed"):
        raise EvidenceError("code comparison status contradicts its changes")
    if not changes and (code["effective_code_changed"] or code["candidate_path_changed"]):
        raise EvidenceError("unchanged code comparison has changed flags")
    alignment = {}
    for side in ("before", "after"):
        cb = block(code.get(f"{side}_block"), f"code {side}")
        call_side = call.get(side)
        if not isinstance(call_side, dict):
            raise EvidenceError(f"call {side}: missing observation")
        ab = block(call_side.get("block"), f"call {side}")
        alignment[side] = {
            "code_block": cb,
            "call_block": ab,
            "same_block": cb == ab,
            "height_gap_call_minus_code": ab["number"] - cb["number"],
        }
    if alignment["before"]["code_block"]["number"] > alignment["after"]["code_block"]["number"]:
        raise EvidenceError("code comparison runs backwards")
    if alignment["before"]["call_block"]["number"] > alignment["after"]["call_block"]["number"]:
        raise EvidenceError("call comparison runs backwards")
    for kind in ("code_block", "call_block"):
        earlier = alignment["before"][kind]
        later = alignment["after"][kind]
        if (earlier["number"] == later["number"]) != (earlier["hash"] == later["hash"]):
            raise EvidenceError(f"{kind}: conflicting endpoint block identities")
    before_call = alignment["before"]["call_block"]
    after_call = alignment["after"]["call_block"]
    if type(call.get("blocks_apart")) is not int or call["blocks_apart"] != after_call["number"] - before_call["number"]:
        raise EvidenceError("call block gap contradicts its observations")
    if type(call.get("same_block")) is not bool or call["same_block"] != (before_call == after_call):
        raise EvidenceError("call same-block flag contradicts its observations")
    same_target = code_target == call_target
    same_blocks = all(item["same_block"] for item in alignment.values())
    status = "different_target" if not same_target else "aligned" if same_blocks else "different_blocks"
    return {
        "schema": "change-context-v1",
        "chain_id": 1,
        "code_target": code_target,
        "call_target": call_target,
        "status": status,
        "alignment": alignment,
        "code_status": code["status"],
        "effective_code_changed": code["effective_code_changed"],
        "candidate_path_changed": code["candidate_path_changed"],
        "call_verdict": call["verdict"],
        "meaning": (
            "Reports concern different targets; no combined interpretation is available."
            if not same_target else
            "Before and after observations share their respective block hashes. The reports can be read together, but matching evidence does not prove causation or safety."
            if same_blocks else
            "The reports concern the same target at different blocks. Do not attribute the call result to the code observations at either endpoint."
        ),
        "limits": "This joins report metadata; it does not replay raw RPC evidence, authenticate a provider, prove continuous state, or predict a future transaction.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", default="shared/change-context/code-comparison.json")
    parser.add_argument("--call", default="shared/change-context/call-comparison.json")
    parser.add_argument("--require-aligned", action="store_true",
                        help="exit 2 when targets or endpoint blocks differ")
    args = parser.parse_args(argv)
    try:
        report = join(load_report(args.code), load_report(args.call))
    except (EvidenceError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 2 if args.require_aligned and report["status"] != "aligned" else 0


if __name__ == "__main__":
    sys.exit(main())
