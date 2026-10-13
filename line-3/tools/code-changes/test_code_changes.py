"""Synthetic changes test decisions; saved ZTO is a real chain observation."""
import copy
import sys
from pathlib import Path
import unittest

import code_changes as changes
import code_lens as lens
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code-lens'))
from test_code_lens import FakeRPC, word


def later(report):
    result = copy.deepcopy(report)
    result['block'] = {'number': hex(lens.quantity(report['block']['number']) + 1),
                       'hash': lens.digest(b'synthetic later block')}
    return result


class ChangesTests(unittest.TestCase):
    def test_real_observation_self_comparison(self):
        report = lens.read_report('line-3/tools/code-lens/zto-observation.json')
        result = changes.compare(report, report)
        self.assertEqual(result['status'], 'unchanged-at-observed-blocks')
        self.assertEqual(result['before_provenance']['transport_source'], 'unknown-legacy')

    def test_public_transport_provenance(self):
        for endpoint in lens.PUBLIC_SOURCES:
            rpc = FakeRPC()
            rpc.endpoint = endpoint
            report = lens.collect(rpc, lens.ZTO)
            self.assertEqual(report['source'], endpoint)
            self.assertEqual(report['transport_source'], endpoint)
            self.assertTrue(lens.verify(report))

    def test_relay_redaction_and_label_tampering(self):
        rpc = FakeRPC()
        rpc.endpoint = 'http://127.0.0.1:42747/rpc/1'
        report = lens.collect(rpc, lens.ZTO)
        self.assertNotIn('127.0.0.1', str(report))
        self.assertEqual(report['source_kind'], 'attribution-only')
        report['source_kind'] = 'selected-public-endpoint'
        with self.assertRaisesRegex(ValueError, 'upstream'):
            lens.verify(report)

    def test_public_source_mismatch(self):
        report = lens.collect(FakeRPC(), lens.ZTO)
        report['source'] = 'https://eth.drpc.org'
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            lens.verify(report)

    def test_changed_terminal_code(self):
        before = lens.collect(FakeRPC(), lens.ZTO)
        after = later(lens.collect(FakeRPC({lens.ZTO: '0x6001'}), lens.ZTO))
        result = changes.compare(before, after)
        self.assertTrue(result['effective_code_changed'])
        self.assertFalse(result['candidate_path_changed'])
        self.assertEqual(result['changes'][0]['changed_fields'], ['code_hash'])

    def test_path_changes_without_effective_hash_change(self):
        before = lens.collect(FakeRPC({lens.ZTO: '0x6000'}), lens.ZTO)
        after = later(lens.collect(FakeRPC({lens.ZTO: '0x6000', lens.IMD: '0x6000'},
                      {(lens.ZTO, lens.SLOTS['implementation']): word(lens.IMD)}), lens.ZTO))
        result = changes.compare(before, after)
        self.assertTrue(result['candidate_path_changed'])
        self.assertFalse(result['effective_code_changed'])
        self.assertEqual(len(result['changes']), 2)

    def test_unchanged_later_block(self):
        before = lens.collect(FakeRPC(), lens.ZTO)
        self.assertEqual(changes.compare(before, later(before))['changes'], [])

    def test_same_block_conflicting_evidence(self):
        before = lens.collect(FakeRPC(), lens.ZTO)
        after = lens.collect(FakeRPC({lens.ZTO: '0x6001'}), lens.ZTO)
        with self.assertRaisesRegex(ValueError, 'conflicting evidence'):
            changes.compare(before, after)

    def test_reject_target_order_fork_and_tampered_hash(self):
        before = lens.collect(FakeRPC(), lens.ZTO)
        other = lens.collect(FakeRPC({lens.IMD: '0x6000'}), lens.IMD)
        with self.assertRaisesRegex(ValueError, 'different targets'):
            changes.compare(before, other)
        with self.assertRaisesRegex(ValueError, 'precedes'):
            changes.compare(later(before), before)
        fork = copy.deepcopy(before)
        fork['block']['hash'] = lens.digest(b'fork')
        with self.assertRaisesRegex(ValueError, 'competing'):
            changes.compare(before, fork)
        broken = later(before)
        broken['nodes'][0]['code_hash'] = lens.digest(b'bad')
        with self.assertRaisesRegex(ValueError, 'runtime hash'):
            changes.compare(before, broken)

    def test_beacon_runtime_change_detected(self):
        beacon = '0x000000000004444c5dc75cb358380d2e3de08a90'
        slots = {(lens.ZTO, lens.SLOTS['beacon']): word(beacon)}
        codes = {lens.ZTO: '0x6000', lens.IMD: '0x6001', beacon: '0x6002'}
        before = lens.collect(FakeRPC(codes, slots, {beacon: word(lens.IMD)}), lens.ZTO)
        codes = dict(codes, **{beacon: '0x6003'})
        after = later(lens.collect(FakeRPC(codes, slots, {beacon: word(lens.IMD)}), lens.ZTO))
        result = changes.compare(before, after)
        self.assertEqual(result['status'], 'changed')
        self.assertFalse(result['effective_code_changed'])
        self.assertIn('beacon', result['changes'][0]['changed_fields'])


if __name__ == '__main__':
    unittest.main()
