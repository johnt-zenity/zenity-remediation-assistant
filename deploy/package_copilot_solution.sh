#!/bin/sh
set -eu

usage() {
  cat >&2 <<'USAGE'
Usage: deploy/package_copilot_solution.sh ENVIRONMENT_ID SOLUTION_UNIQUE_NAME CUSTOMER_API_HOST OUTPUT_ZIP

Exports the Dataverse solution with PAC, configures the connector host for a
customer deployment, and checks the ZIP for required components and credential
material. It does not import or publish the solution.
USAGE
  exit 2
}

[ "$#" -eq 4 ] || usage
environment_id=$1
solution_name=$2
customer_api_host=$3
output_zip=$4

pac_cli=$(command -v pac || true)
if [ -z "$pac_cli" ] && [ -x "$HOME/.dotnet/tools/pac" ]; then
  pac_cli="$HOME/.dotnet/tools/pac"
fi
[ -n "$pac_cli" ] || { printf 'Power Platform CLI (pac) is required.\n' >&2; exit 1; }

output_dir=$(dirname "$output_zip")
mkdir -p "$output_dir"
tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/zenity-solution.XXXXXX")
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM
raw_zip="$tmp_dir/export.zip"
configured_zip="$tmp_dir/configured.zip"

"$pac_cli" solution export \
  --name "$solution_name" \
  --path "$raw_zip" \
  --environment "$environment_id" \
  --overwrite

python3 - "$raw_zip" "$configured_zip" "$customer_api_host" <<'PY'
import json
import re
import sys
import zipfile
from pathlib import PurePosixPath

source, destination, host = sys.argv[1:]
if not re.fullmatch(r'(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}', host):
    raise SystemExit('Customer API host must be a DNS hostname without scheme, path, query, or credentials.')
if host.lower().split('.')[-1] in {'example', 'invalid', 'localhost'}:
    raise SystemExit('Replace the reserved placeholder host with the deployed customer API host.')

with zipfile.ZipFile(source) as zin:
    entries = {item.filename: item for item in zin.infolist()}
    connector_files = [name for name in entries if name.lower().endswith(('openapidefinition.json', 'openapi.json')) and 'connector' in name.lower()]
    if len(connector_files) != 1:
        raise SystemExit('Expected exactly one connector OpenAPI definition in the exported solution.')
    content = {name: zin.read(name) for name in entries}

connector_path = connector_files[0]
try:
    definition = json.loads(content[connector_path].decode('utf-8-sig'))
except (UnicodeError, json.JSONDecodeError) as error:
    raise SystemExit(f'Connector OpenAPI definition is invalid JSON: {error}')
definition['host'] = host.lower()
if not any(operation.get('operationId') == 'LookupViolation'
           for path in definition.get('paths', {}).values()
           for operation in path.values() if isinstance(operation, dict)):
    raise SystemExit('Connector does not expose LookupViolation.')
if not any(path == '/api/lookup' and operation.get('operationId') == 'LookupViolation'
           for path, methods in definition.get('paths', {}).items()
           for operation in methods.values() if isinstance(operation, dict)):
    raise SystemExit('LookupViolation must use the fixed /api/lookup endpoint.')
content[connector_path] = (json.dumps(definition, indent=2) + '\n').encode()

need_bot = any(name.startswith('bots/') and name.endswith('/bot.xml') for name in entries)
need_action = any(name.startswith('botcomponents/') and '.action.' in name and name.endswith('/data') for name in entries)
need_connection = any('connectionreference' in name.lower() for name in entries)
if not (need_bot and need_action and need_connection):
    raise SystemExit('Solution is incomplete: expected agent, action, and connection reference components.')
if not any(b'LookupViolation' in content[name] for name in entries if name.startswith('botcomponents/') and '.action.' in name and name.endswith('/data')):
    raise SystemExit('The agent action data does not identify LookupViolation.')

credential_patterns = [
    re.compile(rb'(?i)(?:client[_-]?secret|access[_-]?token|refresh[_-]?token|id[_-]?token)\s*[=:]\s*["\']?[^\s"\',}]+'),
    re.compile(rb'(?i)authorization\s*[:=]\s*["\']?Basic\s+[A-Za-z0-9+/=]+'),
    re.compile(rb'(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}'),
]
for name, data in content.items():
    if PurePosixPath(name).suffix.lower() not in {'.json', '.xml', '.yml', '.yaml', '.txt', ''}:
        continue
    for pattern in credential_patterns:
        if pattern.search(data):
            raise SystemExit(f'Credential-like material found in solution member: {name}')

with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
    for name, item in entries.items():
        zout.writestr(item, content[name])
print(f'Validated solution package: agent, LookupViolation, connection reference, host={host.lower()}')
PY

mv "$configured_zip" "$output_zip"
printf 'Customer solution package created: %s\n' "$output_zip"
