"""Offline regression tests. Synthetic branches are not live-chain observations."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import call_changes as c

BEFORE = {'schema': c.core.SCHEMA, 'chain_id': 1, 'source': c.core.ENDPOINTS[0],
          'block': {'number': '0x100', 'hash': '0x' + 'ab' * 32, 'timestamp': '0x1000'},
          'call': {'to': c.core.TOKENS['ZTO'], 'data': '0x18160ddd', 'value': '0x0'},
          'returns': 'uint256', 'code_present': True,
          'outcome': {'result': '0x' + format(10, '064x')}}
LATER = {'number': '0x102', 'hash': '0x' + 'cd' * 32, 'timestamp': '0x1018'}


def pair():
    a, b = copy.deepcopy(BEFORE), copy.deepcopy(BEFORE)
    b['block'] = dict(LATER)
    return a, b


def returned(number):
    return {'result': '0x' + format(number, '064x')}


def reverted(raw=None, message='execution reverted', code=3):
    error = {'code': code, 'message': message}
    if raw is not None:
        error['data'] = raw
    return {'error': error}


class FakeRPC:
    endpoint = c.core.ENDPOINTS[1]

    def __init__(self, *, code='0x6000', outcome=None, changed=False, wrong_number=False,
                 chain='0x1', finalized_change=False):
        self.calls = []
        self.code, self.chain = code, chain
        self.outcome = returned(10) if outcome is None else outcome
        self.changed, self.wrong_number = changed, wrong_number
        self.finalized_change = finalized_change
        self.request_counts = {}

    def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'eth_chainId':
            return self.chain
        if method == 'eth_getBlockByNumber':
            tag = params[0]
            self.request_counts[tag] = self.request_counts.get(tag, 0) + 1
            block = dict(LATER if tag in ('finalized', LATER['number']) else BEFORE['block'])
            if self.wrong_number and tag == BEFORE['block']['number']:
                block['number'] = '0xff'
            if self.changed and tag != 'finalized' and self.request_counts[tag] >= 2:
                block['hash'] = '0x' + 'ef' * 32
            if self.finalized_change and tag == LATER['number']:
                block['hash'] = '0x' + 'ef' * 32
            return block
        if method == 'eth_getCode':
            return self.code
        if method == 'eth_call':
            if 'error' in self.outcome:
                raise c.core.RPCError(self.outcome['error'])
            return self.outcome['result']
        raise AssertionError('unapproved method: ' + method)


class CompareTests(unittest.TestCase):
    def test_equal_uint256_and_elapsed_context(self):
        result = c.compare(*pair())
        self.assertEqual(result['verdict'], 'unchanged')
        self.assertEqual(result['uint256_delta'], '0')
        self.assertEqual(result['blocks_apart'], 2)
        self.assertEqual(result['seconds_apart'], 24)
        self.assertFalse(result['same_block'])

    def test_signed_arbitrary_precision_delta(self):
        for old, new in [(10, 7), (7, 10), (2**256 - 1, 0)]:
            a, b = pair()
            a['outcome'], b['outcome'] = returned(old), returned(new)
            result = c.compare(a, b)
            self.assertEqual(result['verdict'], 'changed')
            self.assertEqual(result['uint256_delta'], str(new - old))

    def test_same_block_difference_is_inconsistent_not_state_change(self):
        a, b = pair()
        b['block'] = dict(a['block'])
        b['outcome'] = returned(11)
        report = c.compare(a, b)
        self.assertEqual(report['verdict'], 'inconsistent_observations')
        self.assertEqual(c.exit_code(report), 2)

    def test_same_block_identical_result(self):
        result = c.compare(BEFORE, copy.deepcopy(BEFORE))
        self.assertTrue(result['same_block'])
        self.assertEqual(result['verdict'], 'unchanged')

    def test_all_call_fields_must_match(self):
        changes = {'to': c.core.TOKENS['IMD'], 'from': c.core.TOKENS['IMD'],
                   'data': '0xaabbccdd', 'value': '0x1'}
        for key, value in changes.items():
            a, b = pair()
            # Both remain valid explicit-sender calls while one chosen field differs.
            a['call']['from'] = c.core.TOKENS['ZTO']
            b['call']['from'] = c.core.TOKENS['ZTO']
            b['call'][key] = value
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, 'different target'):
                c.compare(a, b)

    def test_omitted_sender_is_not_assumed_to_equal_explicit_sender(self):
        a, b = pair()
        b['call']['from'] = c.core.TOKENS['IMD']
        with self.assertRaisesRegex(ValueError, 'different target'):
            c.compare(a, b)

    def test_normalized_hex_and_endpoint_provenance(self):
        a, b = pair()
        b['call']['to'] = '0x' + b['call']['to'][2:].upper()
        b['outcome']['result'] = '0x' + b['outcome']['result'][2:].upper()
        b['source'] = c.core.ENDPOINTS[1]
        result = c.compare(a, b)
        self.assertEqual(result['verdict'], 'unchanged')
        self.assertFalse(result['same_provider'])
        self.assertEqual(result['after']['source'], c.core.ENDPOINTS[1])

    def test_different_interpretation_rejected(self):
        a, b = pair()
        b['returns'] = 'raw'
        with self.assertRaisesRegex(ValueError, 'return interpretations'):
            c.compare(a, b)

    def test_block_identity_and_order(self):
        for field, value, message in [
            ('number', '0xff', 'precede'),
            ('number', '0x100', 'conflicting hash'),
            ('hash', BEFORE['block']['hash'], 'same hash'),
            ('timestamp', '0x1000', 'later timestamp')]:
            a, b = pair()
            b['block'][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, message):
                c.compare(a, b)

    def test_false_is_retained_and_change_is_reported(self):
        a, b = pair()
        a['returns'] = b['returns'] = 'bool'
        a['outcome'], b['outcome'] = returned(1), returned(0)
        result = c.compare(a, b)
        self.assertEqual(result['verdict'], 'changed')
        self.assertEqual(result['after']['result']['status'], 'returned_false')
        a['outcome'] = returned(0)
        self.assertEqual(c.compare(a, b)['verdict'], 'unchanged')

    def test_rpc_failure_and_bad_abi_are_not_unchanged(self):
        for outcome in [reverted(message='historical state unavailable', code=-32000),
                        {'result': '0x'}, {'result': '0xab'}]:
            a, b = pair()
            a['outcome'] = b['outcome'] = outcome
            with self.subTest(outcome=outcome):
                self.assertEqual(c.compare(a, b)['verdict'], 'inconclusive')

    def test_noncanonical_bool_is_inconclusive(self):
        a, b = pair()
        a['returns'] = b['returns'] = 'bool'
        self.assertEqual(c.compare(a, b)['verdict'], 'inconclusive')

    def test_return_revert_transition_does_not_require_revert_bytes(self):
        a, b = pair()
        b['outcome'] = reverted()
        self.assertEqual(c.compare(a, b)['verdict'], 'changed')
        a['outcome'], b['outcome'] = b['outcome'], a['outcome']
        self.assertEqual(c.compare(a, b)['verdict'], 'changed')

    def test_missing_revert_data_is_inconclusive(self):
        for error_data in [None, {'nested': '0xabcd'}, 'not hex']:
            a, b = pair()
            a['outcome'], b['outcome'] = reverted(error_data), reverted('0x')
            with self.subTest(error_data=error_data):
                self.assertEqual(c.compare(a, b)['verdict'], 'inconclusive')

    def test_explicit_empty_revert_bytes_are_evidence(self):
        a, b = pair()
        a['outcome'], b['outcome'] = reverted('0x'), reverted('0x', message='revert at opcode')
        self.assertEqual(c.compare(a, b)['verdict'], 'unchanged')

    def test_custom_revert_data_compared_exactly(self):
        a, b = pair()
        a['outcome'], b['outcome'] = reverted('0xaabbccdd'), reverted('0xAABBCCDD')
        self.assertEqual(c.compare(a, b)['verdict'], 'unchanged')
        b['outcome'] = reverted('0x11223344')
        self.assertEqual(c.compare(a, b)['verdict'], 'changed')

    def test_raw_empty_result_is_comparable(self):
        a, b = pair()
        a['returns'] = b['returns'] = 'raw'
        a['outcome'] = b['outcome'] = {'result': '0x'}
        self.assertEqual(c.compare(a, b)['verdict'], 'unchanged')

    def test_inputs_not_mutated(self):
        a, b = pair()
        saved = copy.deepcopy((a, b))
        c.compare(a, b)
        self.assertEqual((a, b), saved)

    def test_strict_schema_and_chain(self):
        for key, value in [('chain_id', True), ('chain_id', 2), ('code_present', False),
                           ('source', 'unknown'), ('trusted_verdict', 'unchanged')]:
            a, b = pair()
            b[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.compare(a, b)

    def test_large_error_is_rejected(self):
        a, b = pair()
        b['outcome'] = reverted(message='a' * c.core.LIMIT)
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            c.compare(a, b)


class CaptureTests(unittest.TestCase):
    def test_historical_block_pins_all_state_reads(self):
        rpc = FakeRPC()
        obs = c.capture(rpc, BEFORE['call'], 'uint256', '0x100')
        pin = {'blockHash': BEFORE['block']['hash'], 'requireCanonical': True}
        self.assertIn(('eth_getCode', [BEFORE['call']['to'], pin]), rpc.calls)
        self.assertIn(('eth_call', [BEFORE['call'], pin]), rpc.calls)
        self.assertEqual(rpc.calls[-1], ('eth_getBlockByNumber', ['0x100', False]))
        self.assertEqual(obs['source'], c.core.ENDPOINTS[1])
        self.assertEqual(obs['block'], BEFORE['block'])

    def test_finalized_default_and_explicit_height(self):
        for selector in ['finalized', '0x102']:
            with self.subTest(selector=selector):
                result = c.capture(FakeRPC(), BEFORE['call'], 'uint256', selector)
                self.assertEqual(result['block'], LATER)

    def test_unfinalized_request_stops_before_execution(self):
        rpc = FakeRPC()
        with self.assertRaisesRegex(ValueError, 'newer than'):
            c.capture(rpc, BEFORE['call'], 'uint256', '0x103')
        self.assertNotIn('eth_call', [m for m, _ in rpc.calls])

    def test_wrong_header_changed_header_and_wrong_chain(self):
        for options, selector, message in [
            ({'wrong_number': True}, '0x100', 'wrong requested block'),
            ({'changed': True}, '0x100', 'block changed'),
            ({'finalized_change': True}, '0x102', 'finalized header changed'),
            ({'chain': '0xa'}, 'finalized', 'mainnet')]:
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, message):
                c.capture(FakeRPC(**options), BEFORE['call'], 'uint256', selector)

    def test_code_absent_stops_call(self):
        rpc = FakeRPC(code='0x')
        with self.assertRaisesRegex(ValueError, 'no code'):
            c.capture(rpc, BEFORE['call'], 'uint256')
        self.assertNotIn('eth_call', [m for m, _ in rpc.calls])

    def test_rpc_error_preserved_without_fabricating_data(self):
        outcome = reverted()
        obs = c.capture(FakeRPC(outcome=outcome), BEFORE['call'], 'uint256')
        self.assertEqual(obs['outcome'], outcome)

    def test_invalid_block_and_call_fail_before_network(self):
        for selector in ['latest', 'pending', '256', '0x00', '-1']:
            rpc = FakeRPC()
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                c.capture(rpc, BEFORE['call'], 'uint256', selector)
            self.assertEqual(rpc.calls, [])
        rpc = FakeRPC()
        with self.assertRaises(ValueError):
            c.capture(rpc, dict(BEFORE['call'], data='0xabcd'), 'raw')
        self.assertEqual(rpc.calls, [])

    def test_read_only_transport_allowlist(self):
        rpc = c.core.RPC(c.core.ENDPOINTS[0])
        with self.assertRaisesRegex(ValueError, 'allowlisted'):
            rpc.call('eth_sendRawTransaction', [])


class FileAndCLITests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_duplicate_keys_nonfinite_numbers_and_oversized_files(self):
        path = self.root / 'bad.json'
        for raw in ['{"schema":1,"schema":2}', '{"x":NaN}', ' ' * (c.core.LIMIT + 1)]:
            path.write_text(raw)
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                c.load_observation(path)

    def test_workspace_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, 'workspace'):
            c.load_observation('../outside.json')

    def test_exclusive_save_and_round_trip(self):
        path = self.root / 'observation.json'
        c.save_observation(path, BEFORE)
        self.assertEqual(c.load_observation(path), BEFORE)
        with self.assertRaises(FileExistsError):
            c.save_observation(path, BEFORE)

    def test_cli_exit_codes_and_json_reports(self):
        before_path, after_path = self.root / 'before.json', self.root / 'after.json'
        a, b = pair()
        c.save_observation(before_path, a)
        for outcome, expected in [(returned(10), 0), (returned(11), 1), ({'result': '0x'}, 2)]:
            b['outcome'] = outcome
            after_path.write_text(json.dumps(b))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                actual = c.main(['compare', str(before_path), str(after_path)])
            self.assertEqual(actual, expected)
            self.assertEqual(json.loads(output.getvalue())['schema'], c.SCHEMA)

    def test_recheck_output_conflict_fails_before_rpc(self):
        path = self.root / 'before.json'
        c.save_observation(path, BEFORE)
        with patch.object(c.core, 'RPC') as rpc, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(c.main(['recheck', str(path), '--save', str(path)]), 2)
        rpc.assert_not_called()
        self.assertEqual(c.load_observation(path), BEFORE)

    def test_recheck_older_block_fails_before_rpc(self):
        path = self.root / 'before.json'
        c.save_observation(path, BEFORE)
        with patch.object(c.core, 'RPC') as rpc, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(c.main(['recheck', str(path), '--block', '0xff']), 2)
        rpc.assert_not_called()

    def test_recheck_preserves_sender_and_saves_raw_after(self):
        a, b = pair()
        a['call']['from'] = b['call']['from'] = c.core.TOKENS['IMD']
        path, destination = self.root / 'before.json', self.root / 'after.json'
        c.save_observation(path, a)
        fake = FakeRPC()
        with patch.object(c.core, 'RPC', return_value=fake), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main(['recheck', str(path), '--save', str(destination)]), 0)
        self.assertEqual(c.load_observation(destination)['call'], a['call'])

    def test_demo_uses_real_saved_pair_without_network(self):
        output = io.StringIO()
        with patch.object(c.core, 'RPC', side_effect=AssertionError('offline')), contextlib.redirect_stdout(output):
            self.assertEqual(c.main(['demo']), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['call']['to'], c.core.TOKENS['ZTO'])
        self.assertEqual(report['verdict'], 'unchanged')
        self.assertGreater(report['blocks_apart'], 0)
        self.assertEqual(report['after']['result']['uint256'], '1000000000000000000000000000')


if __name__ == '__main__':
    unittest.main()
