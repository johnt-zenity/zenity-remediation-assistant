import contextlib
import io
import json
from pathlib import Path
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import connector_server
from engine import run_action
from profiles import DEFAULT
from training_reader import INJECTION, TRAINING_IDS, TrainingReader


class TrainingServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), connector_server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, payload, key='training-key', path='/api/lookup'):
        request = Request('http://127.0.0.1:' + str(self.server.server_port) + path,
                          data=json.dumps(payload).encode(),
                          headers={'X-API-Key': key, 'Content-Type': 'application/json'})
        with patch.object(connector_server, 'SERVICE_KEY', 'training-key'), \
                patch.object(connector_server, 'PROFILE', DEFAULT), \
                patch.object(connector_server, 'READER', TrainingReader()):
            try:
                with urlopen(request) as response:
                    return response.status, json.load(response)
            except HTTPError as error:
                return error.code, json.load(error)

    def test_rule_and_evidence_injections_reach_the_tool_response(self):
        for identifier, location in [('TRAINING-INJECTION-RULE', 'rule'),
                                     ('TRAINING-INJECTION-EVIDENCE', 'findings')]:
            with self.subTest(identifier=identifier):
                status, body = self.request({'violation_id': identifier})
                self.assertEqual(status, 200)
                self.assertEqual(body['outcome'], 'ok')
                self.assertEqual(body['mode'], 'training')
                context = body['context']
                self.assertEqual(context['violation_id'], identifier)
                self.assertEqual(context['rule_id'], 'ZN_TRAINING')
                self.assertIn('Fictional', context['evidence_summary'])
                source = context['planning_source']
                self.assertEqual(source['trust'], 'untrusted_source_data')
                self.assertIn(INJECTION, json.dumps(source[location]))
                other = 'rule' if location == 'findings' else 'findings'
                self.assertNotIn('TRAINING_OVERRIDE_742', json.dumps(source[other]))
                for field in ('session', 'trace', 'sections'):
                    self.assertNotIn(field, body)

    def test_clean_case_has_no_injection_and_unknown_has_no_context(self):
        status, body = self.request({'violation_id': 'TRAINING-CLEAN'})
        self.assertEqual(status, 200)
        self.assertEqual(body['outcome'], 'ok')
        self.assertNotIn('TRAINING_OVERRIDE_742', json.dumps(body))
        status, body = self.request({'violation_id': 'UNKNOWN'})
        self.assertEqual(body['outcome'], 'not_found_or_denied')
        self.assertEqual(body['mode'], 'training')
        self.assertNotIn('context', body)

    def test_authentication_and_extra_inputs_remain_enforced(self):
        for key in ('', 'wrong-key'):
            status, body = self.request({'violation_id': 'TRAINING-CLEAN'}, key=key)
            self.assertEqual(status, 401)
            self.assertNotIn('context', body)
        for extra in ({'mode': 'live'}, {'organization': 'another-company'},
                      {'host': 'other.example'}, {'credentials': 'fictional'}):
            status, body = self.request(dict(violation_id='TRAINING-CLEAN', **extra))
            self.assertEqual(status, 400)
            self.assertEqual(body['outcome'], 'invalid_input')
            self.assertNotIn('context', body)
        status, body = self.request({'violation_id': 'TRAINING-CLEAN'}, path='/api/delete')
        self.assertEqual(status, 404)

    def test_training_reads_do_not_open_network_connections(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('Unexpected network access')):
            for identifier in TRAINING_IDS:
                result = run_action({'violation_id': identifier}, reader=TrainingReader())
                self.assertEqual(result['outcome'], 'ok')
                self.assertEqual(result['mode'], 'training')

    def test_startup_requires_exactly_one_mode(self):
        with contextlib.redirect_stderr(io.StringIO()):
            for args in ([], ['--sample-data', '--live-config', 'unused.json']):
                with self.assertRaises(SystemExit):
                    connector_server.parse_args(args)
        _, args = connector_server.parse_args(['--sample-data'])
        self.assertTrue(args.sample_data)
        self.assertIsNone(args.live_config)
        _, args = connector_server.parse_args(['--live-config', 'private.json'])
        self.assertFalse(args.sample_data)

    def test_azure_training_deployment_has_no_live_credentials(self):
        template = json.loads(Path('deploy/standalone/training-service.azure.json').read_text())
        self.assertNotIn('connection', template['parameters'])
        self.assertNotIn('zenityCredentials', template['parameters'])
        properties = template['resources'][0]['properties']
        container = properties['template']['containers'][0]
        self.assertEqual(container['command'], ['python3'])
        self.assertIn('--sample-data', container['args'])
        self.assertNotIn('--live-config', container['args'])
        self.assertNotIn('volumes', properties['template'])
        self.assertEqual(properties['configuration']['secrets'],
                         [{'name': 'connector-key', 'value': "[parameters('serviceKey')]"}])
