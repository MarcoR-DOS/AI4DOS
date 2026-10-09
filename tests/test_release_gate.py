"""Live gate classification/budget exercised entirely through synthetic HTTP."""
import importlib.util
import json
from pathlib import Path
import tempfile
import socket
import unittest
from unittest.mock import patch
import httpx

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_gate', ROOT/'tools/validate-release.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
KEY = 'SYNTHETIC_GATE_KEY'


class ReleaseGateTests(unittest.IsolatedAsyncioTestCase):
    def test_offline_gate_blocks_external_dns_and_connect_before_network(self):
        with gate.offline_network():
            with self.assertRaisesRegex(RuntimeError, 'External networking forbidden'):
                socket.getaddrinfo('provider.invalid',443)
            with socket.socket() as connection:
                with self.assertRaisesRegex(RuntimeError, 'External networking forbidden'):
                    connection.connect(('198.51.100.1',443))
                with self.assertRaisesRegex(RuntimeError, 'External networking forbidden'):
                    connection.connect_ex(('198.51.100.1',443))

    def test_secret_scan_rejects_credential_patterns_without_printing_values(self):
        for prefix in (b'sk-proj-',b'sk-or-v1-',b'sk-ant-',b'nvapi-',b'AIza'):
            self.assertTrue(gate.has_secret(prefix+b'X'*40))
        self.assertTrue(gate.has_secret(b'-----BEGIN '+b'PRIVATE KEY-----'))
        self.assertFalse(gate.has_secret(b'API_KEY=\nSECRET=<KEY>\nsynthetic-contract-key'))

    async def test_live_outcomes_request_budget_and_secret_hygiene_offline(self):
        original = httpx.AsyncClient
        for status, expected in ((200,'LIVE PASS'), (404,'LIVE NOT AVAILABLE'),
                                 (401,'FAIL'), (429,'FAIL'), (500,'FAIL')):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                config = Path(folder)/'gateway.json'
                config.write_text(json.dumps(dict(devices={'d':'synthetic-device-key'},
                    provider='gemini',model='gemini-2.5-flash',api_key=KEY,max_output_tokens=128)))
                requests = []
                def handle(request):
                    requests.append(request)
                    if status == 200:
                        return httpx.Response(status, content='data: '+json.dumps({
                            'candidates':[{'content':{'parts':[{'text':'OK'}]},'finishReason':'STOP'}]})+'\n\n')
                    return httpx.Response(status,json={'error':{'message':KEY}})
                class ContractClient(original):
                    def __init__(self, **kwargs):
                        kwargs.setdefault('transport', httpx.MockTransport(handle))
                        super().__init__(**kwargs)
                with patch('httpx.AsyncClient',ContractClient):
                    result = await gate.live(config)
                self.assertEqual(result['status'],expected)
                self.assertEqual(result['requests'],1)
                self.assertEqual(len(requests),1)
                self.assertNotIn(KEY,json.dumps(result))
                if status == 404: self.assertEqual(result['error'],'UPSTREAM_MODEL')

    async def test_missing_live_key_is_unavailable_without_request(self):
        for key_settings in ({}, {'api_key_file':'missing-key'}):
            with self.subTest(key_settings=key_settings), tempfile.TemporaryDirectory() as folder:
                config = Path(folder)/'gateway.json'
                config.write_text(json.dumps(dict(devices={'d':'synthetic-device-key'},
                    provider='gemini',model='gemini-2.5-flash',max_output_tokens=128,**key_settings)))
                with patch.dict('os.environ',{},clear=True):
                    result = await gate.live(config)
                self.assertEqual(result['status'],'LIVE NOT AVAILABLE')
                self.assertEqual(result['requests'],0)
