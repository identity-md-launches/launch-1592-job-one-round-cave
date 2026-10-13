#!/usr/bin/env python3
"""Compare verified runtime/proxy observations; never send a transaction."""
import argparse
import json
from pathlib import Path
import sys

# An explicit workspace-local sibling, never a dependency download.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code-lens'))
import code_lens as lens


def identity(report):
    nodes = []
    for n in report['nodes']:
        beacon = n.get('beacon')
        nodes.append({'address': lens.address(n['address']),
                      'code_hash': lens.fixed_hex(n['code_hash'], 32),
                      'storage': {k: lens.fixed_hex(v, 32) for k, v in n['storage'].items()},
                      'kind': n['kind'], 'next_address': n['next_address'],
                      'beacon': {'address': lens.address(beacon['address']),
                                 'code_hash': lens.fixed_hex(beacon['code_hash'], 32),
                                 'implementation_result': lens.fixed_hex(beacon['implementation_result'], 32)}
                                if beacon else None})
    return nodes


def compare(before, after):
    lens.verify(before)
    lens.verify(after)
    lens.require(before['target'] == after['target'], 'observations have different targets')
    old_number = lens.quantity(before['block']['number'])
    new_number = lens.quantity(after['block']['number'])
    lens.require(new_number >= old_number, 'after block precedes before block')
    same_height = new_number == old_number
    same_hash = lens.fixed_hex(before['block']['hash'], 32) == lens.fixed_hex(after['block']['hash'], 32)
    lens.require(same_height == same_hash, 'inconsistent or competing block identities')
    old, new = identity(before), identity(after)
    lens.require(not same_hash or old == new, 'conflicting evidence at the same block')
    changes = []
    for index in range(max(len(old), len(new))):
        left = old[index] if index < len(old) else None
        right = new[index] if index < len(new) else None
        if left != right:
            fields = sorted(set(left or {}) | set(right or {}))
            changes.append({'path_index': index, 'before_address': left['address'] if left else None,
                            'after_address': right['address'] if right else None,
                            'changed_fields': [f for f in fields if (left or {}).get(f) != (right or {}).get(f)],
                            'before': left, 'after': right})
    return {'schema': 'code-changes-v1', 'chain_id': 1, 'target': before['target'],
            'before_block': before['block'], 'after_block': after['block'],
            'before_provenance': lens.provenance(before),
            'after_provenance': lens.provenance(after),
            'status': 'changed' if changes else 'unchanged-at-observed-blocks',
            'effective_code_changed': old[-1]['code_hash'] != new[-1]['code_hash'],
            'candidate_path_changed': [(n['address'], n['kind'], n['next_address']) for n in old]
                                      != [(n['address'], n['kind'], n['next_address']) for n in new],
            'changes': changes,
            'scope': 'Endpoint observations only; not consensus authentication, continuous monitoring, '
                     'semantic review, or proof of no intervening upgrades.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, help='workspace Code Lens report')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--after', help='workspace later Code Lens report (offline)')
    group.add_argument('--live', action='store_true', help='read the same target at the finalized block')
    parser.add_argument('--rpc', default=lens.PUBLIC_RPC)
    args = parser.parse_args()
    try:
        before = lens.read_report(args.before)
        lens.verify(before)
        after = lens.collect(lens.RPC(args.rpc), before['target']) if args.live else lens.read_report(args.after)
        result = compare(before, after)
        if args.live:
            result['after_observation'] = after
        print(json.dumps(result, indent=2))
        return 2 if result['status'] == 'changed' else 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('Code Changes: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
