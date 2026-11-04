import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createReviewClient } from './client.js';
const config = { environmentId: '11111111-1111-1111-1111-111111111111', schemaName: 'test_agent' };
const input = id => ({ violation_id: id, context: { violation_id: id, rule_id: 'ZN_TEST', planning_source: { rule: { description: 'Disallowed endpoint' }, findings: [{ stepName: 'HTTP' }] } } });
const bot = text => ({ type: 'message', from: { role: 'bot' }, text });
async function* stream(values) { yield* values; }

test('invalid scope input and missing reviewer token prevent SDK calls', async () => {
  let calls = 0;
  const review = createReviewClient(config, () => { calls++; });
  for (const input of [{ violation_id: 'finding', host: 'other' }, { violation_id: '../../secret' }, []]) {
    await assert.rejects(review(input, 'reviewer.token'), { code: 'invalid_input' });
  }
  await assert.rejects(review(input('finding'), ''), { code: 'authentication' });
  assert.equal(calls, 0);
});
test('each finding starts a fresh conversation and excludes greetings, events and echoes', async () => {
  const requests = [];
  const review = createReviewClient(config, (settings, token) => {
    assert.equal(settings.schemaName, 'test_agent'); assert.equal(token, 'reviewer.token');
    const id = 'conversation-' + requests.length;
    return {
      startConversationStreaming: flag => { assert.equal(flag, false); return stream([{ ...bot('Greeting'), conversation: { id } }]); },
      sendActivityStreaming: (activity, conversation) => {
        assert.equal(conversation, undefined); requests.push({ activity, conversation: id });
        return stream([{ type: 'event', text: 'debug' }, { type: 'message', from: { role: 'user' }, text: 'echo' }, bot('Generated proposal')]);
      },
    };
  });
  const a = await review(input('finding-a'), 'reviewer.token');
  await review(input('finding-b'), 'reviewer.token');
  assert.deepEqual(a.messages, ['Generated proposal']);
  assert.notEqual(requests[0].conversation, requests[1].conversation);
  assert.match(requests[0].activity.text, /Disallowed endpoint/); assert.match(requests[0].activity.text, /HTTP/); assert.match(requests[0].activity.text, /finding-a/); assert.doesNotMatch(requests[0].activity.text, /finding-b/);
});
test('SDK failure and excessive output expose no partial or replacement proposal', async () => {
  const review = createReviewClient(config, () => ({
    startConversationStreaming: () => stream([{ conversation: { id: 'conversation' } }]),
    sendActivityStreaming: async function* () { yield bot('Partial'); throw new Error('private-token'); },
  }));
  await assert.rejects(review(input('finding'), 'reviewer.token'), error => error.code === 'send_stream_failed' && !error.message.includes('private-token'));
  const oversized = createReviewClient(config, () => ({
    startConversationStreaming: () => stream([{ conversation: { id: 'conversation' } }]),
    sendActivityStreaming: () => stream([bot('x'.repeat(20001))]),
  }));
  await assert.rejects(oversized(input('finding'), 'reviewer.token'), { code: 'response_limit' });
  const rejected = createReviewClient(config, () => ({
    startConversationStreaming: async function* () { throw new Error('Copilot Studio request failed with status 401 Unauthorized: private-token'); },
  }));
  await assert.rejects(rejected(input('finding'), 'reviewer.token'), { code: 'start_401' });
});
test('missing deployment configuration fails before SDK use', () => {
  assert.throws(() => createReviewClient({}), { code: 'configuration' });
});
test('a connection event without a proposal is reported without exposing event details', async () => {
  const review = createReviewClient(config, () => ({
    startConversationStreaming: () => stream([]),
    sendActivityStreaming: () => stream([{ type: 'event', name: 'private-connection-details' }]),
  }));
  await assert.rejects(review(input('finding'), 'reviewer.token'), error =>
    error.code === 'send_event_only' && !error.message.includes('private-connection-details'));
});
test('a stale agent lookup request reports a configuration error', async () => {
  const url = 'https://copilotstudio.microsoft.com/c2/tenants/example/environments/example/bots/example/channels/web/conversations/example/user-connections';
  const review = createReviewClient(config, () => ({
    startConversationStreaming: () => stream([]),
    sendActivityStreaming: () => stream([{ type: 'message', name: 'connectors/connectionManagerCard',
      from: { role: 'bot' }, attachments: [{ contentType: 'application/vnd.microsoft.card.adaptive',
        content: { body: [{ type: 'TextBlock', text: `[Open connection manager](${url})` }] } }] }]),
  }));
  await assert.rejects(review(input('finding'), 'reviewer.token'), error =>
    error.code === 'agent_configuration');
});
test('interim typing activities do not truncate a final proposal', async () => {
  const review = createReviewClient(config, () => ({
    startConversationStreaming: () => stream([]),
    sendActivityStreaming: () => stream([...Array.from({ length: 250 }, () => ({ type: 'typing' })), bot('Final proposal')]),
  }));
  const result = await review(input('finding'), 'reviewer.token');
  assert.deepEqual(result.messages, ['Final proposal']);
});
