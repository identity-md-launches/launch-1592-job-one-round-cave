"""Offline tests; synthetic proxy state is never presented as a chain observation."""
import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

import code_lens as lens

ZERO = '0x' + '00' * 32
BLOCK_HASH = lens.digest(b'unit-test block; not a real observation')
BEACON = '0x000000000004444c5dc75cb358380d2e3de08a90'


def word(addr):
    return '0x' + addr[2:].rjust(64, '0')


class FakeRPC:
    def __init__(self, codes=None, storage=None, beacons=None):
        self.codes = codes if codes is not None else {lens.ZTO: '0x60006000f3'}
        self.storage = storage or {}
        self.beacons = beacons or {}
        self.endpoint = lens.PUBLIC_RPC
        self.calls = []
        self.chain = '0x1'
        self.reorg = False

    def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'eth_chainId':
            return self.chain
        if method == 'eth_getBlockByNumber':
            return {'number': '0x123', 'hash': lens.digest(b'changed') if self.reorg
                    and params[0] != 'finalized' else BLOCK_HASH}
        if method == 'eth_getCode':
            return self.codes.get(params[0], '0x')
        if method == 'eth_getStorageAt':
            return self.storage.get((params[0], params[1]), ZERO)
        if method == 'eth_call':
            return self.beacons[params[0]['to']]
        raise AssertionError('unexpected method ' + method)


class CodeLensTests(unittest.TestCase):
    def test_ethereum_keccak_vectors(self):
        self.assertEqual(lens.digest(b''),
                         '0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470')
        self.assertEqual(lens.digest(b'abc'),
                         '0x4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45')
        self.assertEqual(lens.SLOTS['implementation'],
                         '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc')
        self.assertEqual(lens.SLOTS['beacon'],
                         '0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50')

    def test_real_committed_observations(self):
        for name in ('zto', 'imd'):
            path = Path(__file__).parent / (name + '-observation.json')
            report = lens.read_report(str(path))
            self.assertTrue(lens.verify(report))
            self.assertEqual(report['target'], {'zto': lens.ZTO, 'imd': lens.IMD}[name])
            self.assertEqual(report['nodes'][0]['kind'], 'no-supported-proxy-signal')

    def test_read_operations_are_hash_pinned(self):
        rpc = FakeRPC()
        lens.collect(rpc, lens.ZTO)
        pinned = {'blockHash': BLOCK_HASH, 'requireCanonical': True}
        for method, params in rpc.calls:
            self.assertIn(method, lens.RPC.METHODS)
            if method in ('eth_getCode', 'eth_getStorageAt', 'eth_call'):
                self.assertEqual(params[-1], pinned)

    def test_exact_minimal_proxy(self):
        clone = '0x' + lens.CLONE_PREFIX + lens.IMD[2:] + lens.CLONE_SUFFIX
        rpc = FakeRPC({lens.ZTO: clone, lens.IMD: '0x6000'})
        result = lens.collect(rpc, lens.ZTO)
        self.assertEqual(result['effective_address'], lens.IMD)
        self.assertEqual(result['nodes'][0]['kind'], 'eip1167-exact')
        self.assertTrue(lens.verify(result))
        # A clone variant must not silently be recognized as the exact template.
        self.assertIsNone(lens.clone_target(clone + '00'))

    def test_eip1967_implementation_candidate(self):
        rpc = FakeRPC({lens.ZTO: '0x6000', lens.IMD: '0x6001'},
                      {(lens.ZTO, lens.SLOTS['implementation']): word(lens.IMD)})
        report = lens.collect(rpc, lens.ZTO)
        self.assertEqual(report['nodes'][0]['next_address'], lens.IMD)
        self.assertEqual(report['nodes'][0]['kind'], 'eip1967-implementation-candidate')
        self.assertTrue(lens.verify(report))

    def test_beacon_candidate(self):
        rpc = FakeRPC({lens.ZTO: '0x6000', lens.IMD: '0x6001', BEACON: '0x6002'},
                      {(lens.ZTO, lens.SLOTS['beacon']): word(BEACON)}, {BEACON: word(lens.IMD)})
        report = lens.collect(rpc, lens.ZTO)
        self.assertEqual(report['effective_address'], lens.IMD)
        self.assertTrue(lens.verify(report))
        calls = [params for method, params in rpc.calls if method == 'eth_call']
        self.assertEqual(calls, [[{'to': BEACON, 'data': '0x5c60da1b'},
                                 {'blockHash': BLOCK_HASH, 'requireCanonical': True}]])
        broken = copy.deepcopy(report)
        broken['nodes'][0]['beacon']['code_hash'] = lens.digest(b'wrong')
        with self.assertRaisesRegex(ValueError, 'beacon code hash'):
            lens.verify(broken)

    def test_reject_empty_target_wrong_chain_and_reorg(self):
        with self.assertRaisesRegex(ValueError, 'no runtime code'):
            lens.collect(FakeRPC({}), lens.ZTO)
        rpc = FakeRPC()
        rpc.chain = '0xaa36a7'
        with self.assertRaisesRegex(ValueError, 'not Ethereum'):
            lens.collect(rpc, lens.ZTO)
        rpc = FakeRPC()
        rpc.reorg = True
        with self.assertRaisesRegex(ValueError, 'block changed'):
            lens.collect(rpc, lens.ZTO)

    def test_proxy_cycle_and_depth_limit(self):
        with self.assertRaisesRegex(ValueError, 'cycle'):
            lens.collect(FakeRPC(storage={(lens.ZTO, lens.SLOTS['implementation']): word(lens.ZTO)}), lens.ZTO)
        # Synthetic addresses for bounded traversal only, not deployment inputs.
        targets = ['0x' + format(i, '040x') for i in range(1, 7)]
        rpc = FakeRPC({t: '0x6000' for t in targets},
                      {(a, lens.SLOTS['implementation']): word(b) for a, b in zip(targets, targets[1:])})
        with self.assertRaisesRegex(ValueError, 'depth'):
            lens.collect(rpc, targets[0])
        rpc = FakeRPC({t: '0x6000' for t in targets[:5]},
                      {(a, lens.SLOTS['implementation']): word(b) for a, b in zip(targets[:4], targets[1:5])})
        self.assertEqual(len(lens.collect(rpc, targets[0])['nodes']), 5)

    def test_reject_ambiguous_or_malformed_proxy_slots(self):
        rpc = FakeRPC({lens.ZTO: '0x6000', BEACON: '0x6002'},
                      {(lens.ZTO, lens.SLOTS['implementation']): word(lens.IMD),
                       (lens.ZTO, lens.SLOTS['beacon']): word(BEACON)}, {BEACON: word(lens.IMD)})
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            lens.collect(rpc, lens.ZTO)
        with self.assertRaisesRegex(ValueError, 'padding'):
            lens.slot_address('0x' + '01' * 32)
        with self.assertRaises(ValueError):
            lens.slot_address('0x01')

    def test_no_code_or_zero_result_beacon(self):
        state = {(lens.ZTO, lens.SLOTS['beacon']): word(BEACON)}
        with self.assertRaisesRegex(ValueError, 'beacon has no code'):
            lens.collect(FakeRPC(storage=state), lens.ZTO)
        with self.assertRaisesRegex(ValueError, 'zero implementation'):
            lens.collect(FakeRPC({lens.ZTO: '0x6000', BEACON: '0x6001'}, state, {BEACON: ZERO}), lens.ZTO)

    def test_expected_reviewed_hash_match_and_mismatch(self):
        expected = lens.digest(bytes.fromhex('60006000f3'))
        self.assertTrue(lens.verify(lens.collect(FakeRPC(), lens.ZTO, expected)))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            lens.collect(FakeRPC(), lens.ZTO, lens.digest(b'wrong code'))

    def test_tampered_observation_rejected(self):
        report = lens.collect(FakeRPC(), lens.ZTO)
        mutations = [('code', '0x6001'), ('code_bytes', 123), ('kind', 'eip1167-exact'),
                     ('next_address', lens.IMD), ('address', lens.IMD)]
        for field, value in mutations:
            broken = copy.deepcopy(report)
            broken['nodes'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                lens.verify(broken)
        broken = copy.deepcopy(report)
        broken['effective_code_hash'] = lens.digest(b'wrong')
        with self.assertRaises(ValueError):
            lens.verify(broken)

    def test_no_truncated_proxy_path(self):
        rpc = FakeRPC({lens.ZTO: '0x6000', lens.IMD: '0x6001'},
                      {(lens.ZTO, lens.SLOTS['implementation']): word(lens.IMD)})
        report = lens.collect(rpc, lens.ZTO)
        report['nodes'].pop()
        with self.assertRaisesRegex(ValueError, 'omits'):
            lens.verify(report)

    def test_rpc_envelope_and_read_only_guard(self):
        rpc = lens.RPC(lens.PUBLIC_RPC)
        rpc.opener = Mock()
        rpc.opener.open.return_value = io.BytesIO(json.dumps({'jsonrpc': '2.0', 'id': 99, 'result': '0x1'}).encode())
        with self.assertRaisesRegex(ValueError, 'envelope'):
            rpc.call('eth_chainId', [])
        with self.assertRaisesRegex(ValueError, 'allowlisted'):
            rpc.call('eth_sendRawTransaction', [])
        with self.assertRaisesRegex(ValueError, 'only beacon'):
            rpc.call('eth_call', [{'to': lens.ZTO, 'data': '0xdeadbeef'}, {}])
        with self.assertRaisesRegex(ValueError, 'documented'):
            lens.RPC('https://untrusted.example/rpc')

    def test_malformed_runtime_and_target(self):
        for value in ('0x1', '0xz0', '6000', '0x' + '00' * (lens.MAX_CODE + 1)):
            with self.subTest(value=value[:20]), self.assertRaises(ValueError):
                lens.code_bytes(value)
        for value in ('0x' + '00' * 20, '0x123', '../secret'):
            with self.assertRaises(ValueError):
                lens.address(value)

    def test_files_must_stay_in_workspace(self):
        with self.assertRaisesRegex(ValueError, 'current workspace'):
            lens.read_report('/etc/passwd')


if __name__ == '__main__':
    unittest.main()
