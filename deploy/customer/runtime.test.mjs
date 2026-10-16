import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPair, SignJWT, exportJWK, createLocalJWKSet } from 'jose';
import { createReviewerAuth } from './auth.mjs';
import { validateConfig, browserConfig } from './config.mjs';
import { createApp } from './server.mjs';

const guid = n => `${n.repeat(8)}-${n.repeat(4)}-${n.repeat(4)}-${n.repeat(4)}-${n.repeat(12)}`;
const config = validateConfig({ tenantId: guid('1'), clientId: guid('2'), apiClientId: guid('3'),
  environmentId: guid('4'), schemaName: 'test_agent', origin: 'https://review.example.com' });
const { publicKey, privateKey } = await generateKeyPair('RS256');
const key = { ...await exportJWK(publicKey), kid: 'test', alg: 'RS256', use: 'sig' };
const auth = createReviewerAuth(config, createLocalJWKSet({ keys: [key] }));
async function token(overrides = {}, signingKey = privateKey) {
  return new SignJWT({ ver: '2.0', tid: config.tenantId, oid: guid('5'), azp: config.clientId,
    scp: 'Remediation.Review', roles: ['Remediation.Reviewer'], ...overrides })
    .setProtectedHeader({ alg: 'RS256', kid: 'test' }).setIssuedAt()
    .setIssuer(overrides.iss || `https://login.microsoftonline.com/${config.tenantId}/v2.0`)
    .setAudience(overrides.aud || config.apiClientId).setExpirationTime(overrides.exp || '5m').sign(signingKey);
}
test('signed reviewer tokens enforce tenant, audience, caller, scope, role and expiry', async () => {
  assert.deepEqual(await auth(await token()), { id: guid('5') });
  for (const claims of [{ tid: guid('6') }, { aud: config.clientId }, { azp: guid('6') },
    { scp: '' }, { roles: [] }, { ver: '1.0' }, { exp: 1 }, { iss: 'https://other.example.com' }]) {
    await assert.rejects(auth(await token(claims)));
  }
  const other = await generateKeyPair('RS256');
  await assert.rejects(auth(await token({}, other.privateKey)));
});
test('configuration fixes an HTTPS origin and exposes only browser identifiers', () => {
  for (const origin of ['http://review.example.com', 'https://user:pass@review.example.com', 'https://review.example.com/path']) {
    assert.throws(() => validateConfig({ ...config, origin }));
  }
  assert.throws(() => validateConfig({ ...config, tenantId: 'YOUR_TENANT' }));
  assert.deepEqual(Object.keys(browserConfig(config)).sort(), ['apiScope', 'clientId', 'tenantId']);
});
test('HTTP boundary validates identity before lookup and preserves the same source', async () => {
  const reads = [], plans = [];
  const finding = id => ({ mode: 'live', outcome: 'ok', context: { violation_id: id, rule_id: 'ZN_S00001',
    planning_source: { rule: { description: 'Salesforce rule evidence' }, findings: [] } } });
  const app = createApp(config, { authorize: auth, lookup: async id => {
    reads.push(id); return id === 'denied' ? { outcome: 'not_found_or_denied' } : id === 'mismatch' ? finding('other') : finding(id);
  }, review: async (input, credential) => {
    plans.push({ input, credential });
    if (input.violation_id === 'agent-fail') throw new Error('private upstream error');
    return { source: 'copilot_studio', messages: ['Proposed Salesforce change.'] };
  } });
  const server = app.listen(0, '127.0.0.1');
  await new Promise(resolve => server.once('listening', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const headers = { Origin: config.origin, 'Sec-Fetch-Site': 'same-origin', 'Content-Type': 'application/json',
    Authorization: `Bearer ${await token()}`, 'X-Copilot-Authorization': 'Bearer copilot.token' };
  const post = (body = { violation_id: 'live-id' }, changes = {}) => fetch(base + '/plan', {
    method: 'POST', headers: { ...headers, ...changes }, body: JSON.stringify(body) });
  try {
    for (const changes of [{ Authorization: '', 'X-User-Id': 'admin', 'X-User-Role': 'admin' },
      { Authorization: `Bearer ${await token({ roles: [] })}` }, { Origin: 'https://attacker.example' },
      { 'Sec-Fetch-Site': 'cross-site' }]) assert.ok((await post(undefined, changes)).status >= 400);
    for (const body of [{ violation_id: 'live-id', context: {} }, { violation_id: 'live-id', organization_id: 'other' },
      { violation_id: '../../secret' }]) assert.equal((await post(body)).status, 400);
    assert.equal((await post(undefined, { 'X-Copilot-Authorization': '' })).status, 400);
    assert.equal(reads.length, 0);
    const response = await post(); assert.equal(response.status, 200);
    const value = await response.json();
    assert.deepEqual(reads, ['live-id']);
    assert.deepEqual(plans, [{ input: { violation_id: 'live-id', context: value.finding.context }, credential: 'copilot.token' }]);
    for (const id of ['denied', 'mismatch']) assert.equal((await post({ violation_id: id })).status, 502);
    assert.equal(plans.length, 1);
    const failure = await (await post({ violation_id: 'agent-fail' })).json();
    assert.deepEqual(failure.finding, finding('agent-fail'));
    assert.equal(JSON.stringify(failure).includes('private upstream'), false);
    assert.equal((await fetch(base + '/api/lookup')).status, 404);
  } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
});
