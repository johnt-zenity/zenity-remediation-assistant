"""Generate a customer deployment bundle without reading credentials."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copilot.configure import configure
from zenity_reader import Connection


def package(customer, organization, integration, host, destination, app_config=None, zenity_endpoints=None):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', customer):
        raise ValueError('Customer must be a lowercase deployment label.')
    zenity_endpoints = zenity_endpoints or {}
    connection = Connection(organization, integration, '/run/secrets/zenity-credentials',
        organization_name=customer, **zenity_endpoints)
    contract = configure(host)
    if app_config is not None:
        guid = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        if any(not re.fullmatch(guid, app_config.get(key, '')) for key in ('tenantId', 'clientId', 'apiClientId', 'environmentId')):
            raise ValueError('Microsoft configuration requires valid GUIDs.')
        if not re.fullmatch(r'[A-Za-z0-9_]{1,128}', app_config.get('schemaName', '')):
            raise ValueError('Invalid agent schema name.')
        app_config = {key: app_config[key] for key in ('tenantId','clientId','apiClientId','environmentId','schemaName')}
        app_config['origin'] = 'https://' + contract['host']
    destination = Path(destination)
    # A bundle can contain another customer's scope. Never replace it silently.
    if destination.exists():
        raise ValueError('Choose a new bundle directory.')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    destination.mkdir(parents=True)
    (destination / 'connection.local.json').write_text(json.dumps({
        'organization_id': connection.organization_id,
        'integration_id': connection.integration_id,
        'organization_name': customer,
        'region': connection.region,
        'api_base': connection.api_base, 'token_url': connection.token_url,
        'audience': connection.audience, 'issuer': connection.issuer,
        'credential_file': connection.credential_file}, indent=2) + '\n')
    (destination / 'deployment.json').write_text(json.dumps({
        'customer': customer, 'source_revision': revision,
        'review_host': contract['host'], 'status': 'pending_deployment_and_acceptance'}, indent=2) + '\n')
    configuration = destination / 'config'
    configuration.mkdir()
    shutil.copyfile(destination / 'connection.local.json', configuration / 'connection.json')
    if app_config is not None:
        (configuration / 'app.json').write_text(json.dumps(app_config, indent=2) + '\n')
    application = destination / 'application'
    application.mkdir()
    for name in ('lookup_result.py','engine.py','profiles.py','evidence.py','live_guidance.py','zenity_auth.py','zenity_reader.py'):
        shutil.copyfile(ROOT / name, application / name)
    shutil.copytree(ROOT / 'profiles', application / 'profiles', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT / 'deploy/customer', application / 'deploy/customer',
        ignore=shutil.ignore_patterns('node_modules','*.test.mjs','__pycache__','app.js','app.js.LEGAL.txt'))
    for name in ('package.json','package-lock.json','app-entry.js','client.js'):
        target = application / 'copilot/web' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'copilot/web' / name, target)
    shutil.copyfile(ROOT / 'copilot/agent-instructions.md', destination / 'agent-instructions.md')
    for name in ('customer-runtime-spec.md', 'customer-deployment-spec.md', 'customer-runtime-validation.md'):
        source = (ROOT / 'docs' / name).read_text()
        target = application / 'docs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source)
        (destination / name).write_text(source.replace('../deploy/customer/README.md', 'application/deploy/customer/README.md'))
    (destination / 'README.md').write_text('# Customer application bundle\n\nFollow [the deployment instructions](application/deploy/customer/README.md). Build from `application/` and mount `config/` plus your private Zenity credential file. Configure the customer Microsoft IDs before startup if this bundle was generated without app configuration. No credentials are included.\n')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('customer', 'organization', 'integration', 'host', 'output'):
        parser.add_argument('--' + name, required=True)
    for name in ('tenant-id','spa-client-id','api-client-id','environment-id','agent-schema',
            'zenity-api-base','zenity-token-url','zenity-audience','zenity-issuer','zenity-region'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        result = package(args.customer, args.organization, args.integration, args.host, args.output,
            {'tenantId':args.tenant_id,'clientId':args.spa_client_id,'apiClientId':args.api_client_id,
             'environmentId':args.environment_id,'schemaName':args.agent_schema},
            {'api_base':args.zenity_api_base,'token_url':args.zenity_token_url,
             'audience':args.zenity_audience,'issuer':args.zenity_issuer,'region':args.zenity_region})
    except ValueError as error:
        parser.error(str(error))
    print('Customer deployment bundle generated. Hosting and acceptance are pending.')
