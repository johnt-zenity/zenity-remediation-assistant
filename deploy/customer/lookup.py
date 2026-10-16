"""Private customer reader. Input and credentials never select an API host."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lookup_result import lookup_result
from engine import run_action
from zenity_reader import load_connection, ZenityReader

connection = load_connection(os.environ['REMEDIATION_CONFIG'])
reader = ZenityReader(connection)
if sys.argv[1:] == ['--check']:
    print(json.dumps({'configured': True}))
else:
    raw = sys.stdin.buffer.read(8193)
    if len(raw) > 8192:
        raise ValueError('Input exceeds limit.')
    print(json.dumps(lookup_result(run_action(json.loads(raw), reader=reader, profile=connection.profile))))
