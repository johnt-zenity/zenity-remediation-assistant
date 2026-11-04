import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const script = fileURLToPath(new URL('./lookup.py', import.meta.url));
function call(args, input) {
  return new Promise((resolve, reject) => {
    const child = execFile('python3', [script, ...args], { timeout: 11000, maxBuffer: 65536,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } }, (error, stdout) => {
      if (error) { reject(new Error('Lookup unavailable.')); return; }
      try { resolve(JSON.parse(stdout)); } catch { reject(new Error('Lookup unavailable.')); }
    });
    child.stdin.on('error', () => {});
    child.stdin.end(input);
  });
}
export const checkLookup = () => call(['--check'], '');
export const lookup = id => call([], JSON.stringify({ violation_id: id }));
