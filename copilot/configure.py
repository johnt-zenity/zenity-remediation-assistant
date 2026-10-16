"""Configure a connector import host without credentials."""
import argparse
import json
import re
from pathlib import Path


def configure(host):
    if not re.fullmatch(r'(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}',host):
        raise ValueError('Provide a DNS host only, without scheme, path, query or credentials.')
    if host.lower().split('.')[-1] in {'example', 'invalid', 'localhost'}:
        raise ValueError('Replace the reserved placeholder with the deployed host.')
    spec=json.loads(Path(__file__).with_name('openapi.template.json').read_text())
    spec['host']=host.lower()
    return spec

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try: spec=configure(args.host)
    except ValueError as error: parser.error(str(error))
    Path(args.output).write_text(json.dumps(spec,indent=2)+'\n')
