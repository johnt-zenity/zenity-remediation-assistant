import json
import re
import tempfile
import unittest
from pathlib import Path
from deploy.package_customer import package


class DeploymentTests(unittest.TestCase):
    def test_bundles_have_distinct_scope_and_no_local_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            endpoints = {'api_base':'https://api.zenity.io/','token_url':'https://zenity-prod.eu.auth0.com/oauth/token',
                'audience':'https://zenity-prod.eu.zenity.io/api/v3','issuer':'https://zenity-prod.eu.auth0.com/','region':'prod-us'}
            paths = [package(name, 'org_' + name, name + '-integration',
                name + '.example.com', Path(tmp) / name,
                {key: '11111111-1111-1111-1111-111111111111' for key in ('tenantId','clientId','apiClientId','environmentId')} | {'schemaName':'CustomerAgent'},
                endpoints) for name in ('alpha', 'beta')]
            configs = [json.loads((p / 'connection.local.json').read_text()) for p in paths]
            self.assertNotEqual(configs[0]['organization_id'], configs[1]['organization_id'])
            self.assertNotEqual(configs[0]['integration_id'], configs[1]['integration_id'])
            self.assertEqual((paths[0] / 'agent-instructions.md').read_text(),
                (paths[1] / 'agent-instructions.md').read_text())
            for p in paths:
                self.assertTrue((p / 'application/deploy/customer/Dockerfile').is_file())
                self.assertTrue((p / 'application/deploy/customer/server.mjs').is_file())
                self.assertTrue((p / 'application/copilot/web/app-entry.js').is_file())
                self.assertEqual(json.loads((p / 'config/app.json').read_text())['origin'], 'https://' + p.name + '.example.com')
                self.assertFalse((p / 'application/deploy/customer/node_modules').exists())
                for document in p.rglob('*.md'):
                    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', document.read_text()):
                        if ':' in target or target.startswith('#'):
                            continue
                        self.assertTrue((document.parent / target.split('#')[0]).exists(),
                            f'Broken bundle link in {document.relative_to(p)}: {target}')
                config = (p / 'connection.local.json').read_text()
                self.assertNotIn('/Users/', config)
                self.assertNotIn('client_secret', config)
            with self.assertRaises(ValueError):
                package('alpha', 'org_alpha', 'alpha-integration', 'alpha.example.com', paths[0])
