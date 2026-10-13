"""Real-observation replay plus explicitly synthetic mutations; no network or wallets."""

import contextlib
import copy
import io
import json
import multiprocessing
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import allowance_changes as changes

lens = changes.lens
BEFORE = changes.load(changes.LENS_DIR / 'observation.json')
AFTER = changes.load(changes.HERE / 'recheck.json')


def word(number):
    return '0x' + format(number, '064x')


def old_inventory():
    """Project real old evidence into per-owner observations without making RPC claims."""
    observations = []
    for balance in BEFORE['raw']['balances']:
        owner = balance['owner']
        values = [copy.deepcopy(a) for a in BEFORE['raw']['allowances'] if a['owner'] == owner]
        obs = copy.deepcopy(BEFORE)
        obs['query'] = {'mode': 'explicit_pairs', 'owner': owner,
                        'spenders': sorted(a['spender'] for a in values),
                        'from_block': lens.quantity(obs['block']['number']),
                        'to_block': lens.quantity(obs['block']['number'])}
        obs['logs'], obs['log_headers'] = [], {}
        obs['raw'] = {'decimals': BEFORE['raw']['decimals'],
                      'balances': [copy.deepcopy(balance)], 'allowances': values}
        observations.append(obs)
    return {'schema': changes.BUNDLE_SCHEMA, 'observations': observations}


class ReplayRPC:
    endpoint = lens.PUBLIC_RPC

    def __init__(self):
        self.calls = []
        self.chain = '0x1'
        self.reorg = False
        self.old_reorg = False
        self.new_reads = 0

    def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'eth_chainId':
            return self.chain
        if method == 'eth_getBlockByNumber':
            if params[0] == BEFORE['block']['number']:
                block = copy.deepcopy(BEFORE['block'])
                if self.old_reorg:
                    block['hash'] = AFTER['observations'][0]['block']['hash']
                return block
            self.new_reads += 1
            block = copy.deepcopy(AFTER['observations'][0]['block'])
            if self.reorg and self.new_reads > 2:
                block['hash'] = BEFORE['block']['hash']
            return block
        if method == 'eth_call':
            assert params[1] == {'blockHash': AFTER['observations'][0]['block']['hash'],
                                 'requireCanonical': True}
            assert params[0]['to'] == lens.TOKENS['ZTO']
            if params[0]['data'] == '0x313ce567':
                return AFTER['observations'][0]['raw']['decimals']
            for obs in AFTER['observations']:
                for item in obs['raw']['balances'] + obs['raw']['allowances']:
                    if item['data'] == params[0]['data']:
                        return item['result']
            raise AssertionError('unrecorded call')
        raise AssertionError('unexpected method: ' + method)


def slow_read():
    # A short synthetic blocking operation tests the process deadline without network.
    time.sleep(3)
    return 'too late'


def worker_error():
    raise ValueError('recorded worker failure')


class ChangesTests(unittest.TestCase):
    def test_real_capture_preserves_all_nineteen_pairs(self):
        result = changes.compare(BEFORE, AFTER)
        self.assertEqual(result['coverage'], {'before_pairs': 19, 'after_pairs': 19,
                         'compared_pairs': 19, 'all_previous_pairs_rechecked': True})
        self.assertEqual(result['counts'], {'unchanged': 19})
        self.assertEqual(result['after_block']['block_number'], 26184324)
        self.assertFalse(result['complete_wallet_audit'])
        self.assertEqual(sum(row['balance_delta_raw'] != '0' for row in result['pairs']), 2)

    def test_missing_pair_is_unknown_not_zero(self):
        partial = copy.deepcopy(AFTER)
        omitted = partial['observations'].pop()
        result = changes.compare(BEFORE, partial)
        self.assertFalse(result['coverage']['all_previous_pairs_rechecked'])
        rows = [row for row in result['pairs'] if row['change'] == 'not_rechecked']
        self.assertEqual(len(rows), len(omitted['raw']['allowances']))
        self.assertTrue(all(row['after'] is None and 'allowance_delta_raw' not in row for row in rows))

    def test_real_empty_recent_window_does_not_erase_nineteen_permissions(self):
        recent = changes.load(changes.HERE / 'lens-recheck.json')
        result = changes.compare(BEFORE, recent)
        self.assertEqual(result['counts'], {'not_rechecked': 19})
        self.assertFalse(result['coverage']['all_previous_pairs_rechecked'])
        self.assertEqual(result['owners_over_compared_pairs'], [])

    def test_newly_observed_is_not_newly_approved(self):
        old = old_inventory()
        old['observations'].pop()
        rows = changes.compare(old, AFTER)['pairs']
        new = [row for row in rows if row['change'] == 'newly_observed']
        self.assertTrue(new)
        self.assertTrue(all(row['before'] is None and 'allowance_delta_raw' not in row for row in new))

    def test_all_allowance_transitions_and_exact_integer_deltas(self):
        cases = [(0, 0, 'unchanged'), (0, lens.MAX_UINT, 'became_active'),
                 (lens.MAX_UINT, 0, 'became_zero'), (1, 2, 'increased'), (2, 1, 'decreased')]
        for before_amount, after_amount, expected in cases:
            with self.subTest(expected=expected):
                old, new = old_inventory(), copy.deepcopy(AFTER)
                old['observations'][0]['raw']['allowances'][0]['result'] = word(before_amount)
                new['observations'][0]['raw']['allowances'][0]['result'] = word(after_amount)
                row = changes.compare(old, new)['pairs'][0]
                self.assertEqual(row['change'], expected)
                self.assertEqual(row['allowance_delta_raw'], str(after_amount - before_amount))

    def test_empty_balance_preserves_active_permission(self):
        result = changes.compare(BEFORE, AFTER)
        rows = [row for row in result['pairs'] if row['after']['status'] == 'active_zero_balance']
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(int(row['after']['allowance_raw']) > 0 for row in rows))

    def test_owner_cap_does_not_double_count_overlapping_spenders(self):
        old, new = old_inventory(), copy.deepcopy(AFTER)
        for bundle in (old, new):
            for obs in bundle['observations']:
                for entry in obs['raw']['allowances']:
                    entry['result'] = word(lens.MAX_UINT)
        report = changes.compare(old, new)
        balances = {row['owner']: row['after']['balance_raw'] for row in report['pairs']}
        self.assertTrue(any(row['compared_pair_count'] > 1 for row in report['owners_over_compared_pairs']))
        for row in report['owners_over_compared_pairs']:
            self.assertEqual(row['after_combined_spendable_upper_bound_raw'], balances[row['owner']])

    def test_totals_exclude_unmeasured_pairs(self):
        after = copy.deepcopy(AFTER)
        after['observations'].pop()
        report = changes.compare(BEFORE, after)
        self.assertEqual(sum(row['compared_pair_count'] for row in report['owners_over_compared_pairs']),
                         report['coverage']['compared_pairs'])

    def test_order_independence(self):
        after = copy.deepcopy(AFTER)
        after['observations'].reverse()
        self.assertEqual(changes.compare(BEFORE, after), changes.compare(BEFORE, AFTER))

    def test_same_block_conflicts_fail_but_identical_replay_works(self):
        old = old_inventory()
        self.assertEqual(changes.compare(BEFORE, old)['counts'], {'unchanged': 19})
        old['observations'][0]['raw']['allowances'][0]['result'] = word(123)
        with self.assertRaisesRegex(ValueError, 'conflicting state'):
            changes.compare(BEFORE, old)

    def test_same_height_different_hash_and_backwards_time_fail(self):
        old = old_inventory()
        for obs in old['observations']:
            obs['block']['hash'] = AFTER['observations'][0]['block']['hash']
        with self.assertRaisesRegex(ValueError, 'same-height block conflict'):
            changes.compare(BEFORE, old)
        with self.assertRaisesRegex(ValueError, 'older'):
            changes.compare(AFTER, BEFORE)

    def test_mixed_blocks_duplicate_pairs_and_empty_bundles_fail(self):
        for kind in ('mixed', 'duplicate', 'empty'):
            after = copy.deepcopy(AFTER)
            if kind == 'mixed':
                after['observations'][0]['block']['hash'] = BEFORE['block']['hash']
            elif kind == 'duplicate':
                after['observations'].append(copy.deepcopy(after['observations'][0]))
            else:
                after['observations'] = []
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                changes.flatten(after)

    def test_bad_raw_calldata_and_missing_response_fail(self):
        for kind in ('calldata', 'missing'):
            after = copy.deepcopy(AFTER)
            if kind == 'calldata':
                after['observations'][0]['raw']['allowances'][0]['data'] = '0x'
            else:
                after['observations'][0]['raw']['allowances'].pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                changes.compare(BEFORE, after)

    def test_changed_decimals_are_not_compared(self):
        after = copy.deepcopy(AFTER)
        for obs in after['observations']:
            obs['raw']['decimals'] = word(6)
        with self.assertRaisesRegex(ValueError, 'matching chain, token and decimals'):
            changes.compare(BEFORE, after)

    def test_changed_token_is_not_compared(self):
        after = copy.deepcopy(AFTER)
        for obs in after['observations']:
            obs['token'] = 'IMD'
            obs['token_address'] = lens.TOKENS['IMD']
        with self.assertRaisesRegex(ValueError, 'matching chain, token and decimals'):
            changes.compare(BEFORE, after)

    def test_conflicting_balance_between_disjoint_pairs_of_same_owner_fails(self):
        after = copy.deepcopy(AFTER)
        original = next(obs for obs in after['observations'] if len(obs['raw']['allowances']) > 1)
        split = copy.deepcopy(original)
        split['raw']['allowances'] = [original['raw']['allowances'].pop()]
        split['query']['spenders'] = [split['raw']['allowances'][0]['spender']]
        original['query']['spenders'].remove(split['query']['spenders'][0])
        split['raw']['balances'][0]['result'] = word(123)
        after['observations'].append(split)
        with self.assertRaisesRegex(ValueError, 'conflicting same-block owner balances'):
            changes.flatten(after)

    def test_backwards_timestamp_is_rejected(self):
        after = copy.deepcopy(AFTER)
        for obs in after['observations']:
            obs['block']['timestamp'] = hex(lens.quantity(BEFORE['block']['timestamp']) - 1)
        with self.assertRaisesRegex(ValueError, 'timestamp predates'):
            changes.compare(BEFORE, after)

    def test_refresh_replays_real_capture_with_hash_pins_and_no_event_scan(self):
        rpc = ReplayRPC()
        self.assertEqual(changes.refresh(rpc, BEFORE), AFTER)
        self.assertFalse(any(method == 'eth_getLogs' for method, _ in rpc.calls))
        self.assertEqual(sum(method == 'eth_call' and params[0]['data'].startswith('0xdd62ed3e')
                             for method, params in rpc.calls), 19)

    def test_inventory_can_be_refreshed_again(self):
        # Reuse the old-block inventory shape as input to exercise consecutive rounds.
        self.assertEqual(changes.refresh(ReplayRPC(), old_inventory()), AFTER)

    def test_wrong_chain_fails_before_any_state_reads(self):
        rpc = ReplayRPC()
        rpc.chain = '0x2105'
        with self.assertRaisesRegex(ValueError, 'Ethereum chain 1'):
            changes.refresh(rpc, BEFORE)
        self.assertEqual(len(rpc.calls), 1)

    def test_reorg_of_either_header_is_rejected(self):
        for field in ('reorg', 'old_reorg'):
            rpc = ReplayRPC()
            setattr(rpc, field, True)
            with self.subTest(field=field), self.assertRaises(ValueError):
                changes.refresh(rpc, BEFORE)

    def test_requested_numeric_block_must_match(self):
        with self.assertRaisesRegex(ValueError, 'different block'):
            changes.refresh(ReplayRPC(), BEFORE, hex(26184325))

    def test_offline_command_cannot_construct_rpc(self):
        output = io.StringIO()
        with patch.object(lens, 'RPC', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(output):
                self.assertEqual(changes.main([]), 0)
        self.assertEqual(json.loads(output.getvalue()), changes.compare(BEFORE, AFTER))

    def test_cli_requires_both_offline_inputs_and_explicit_refresh_inventory(self):
        for args in (['--before', str(changes.HERE / 'recheck.json')], ['--refresh'],
                     ['--timeout', '1'], ['--save', 'line-2/unwanted.json']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(changes.main(args), 1)

    def test_workspace_and_overwrite_guards(self):
        with self.assertRaisesRegex(ValueError, 'current workspace'):
            changes.load(Path.cwd().parent / 'never-read.json')
        with self.assertRaises(FileExistsError):
            changes.save(changes.HERE / 'recheck.json', {})

    def test_retired_relay_is_rejected_and_current_route_is_allowed(self):
        lens.RPC(lens.ASSIGNMENT_RPC)
        with self.assertRaises(ValueError):
            lens.RPC('http://127.0.0.1:37401/rpc/1')

    def test_bounded_worker_success_and_error(self):
        self.assertEqual(lens.run_bounded(abs, (-7,), timeout=3), 7)
        with self.assertRaisesRegex(ValueError, 'recorded worker failure'):
            lens.run_bounded(worker_error, timeout=3)

    def test_total_deadline_terminates_blocked_worker(self):
        children = {child.pid for child in multiprocessing.active_children()}
        start = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, 'total deadline'):
            lens.run_bounded(slow_read, timeout=0.2)
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual({child.pid for child in multiprocessing.active_children()}, children)

    def test_invalid_deadlines_fail_before_start(self):
        for timeout in (0, -1, True, float('inf'), float('nan'), 601):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                lens.run_bounded(abs, (-1,), timeout=timeout)


if __name__ == '__main__':
    unittest.main()
