import { InteractionRequiredAuthError, PublicClientApplication } from '@azure/msal-browser';

const SCOPE = 'https://api.powerplatform.com/CopilotStudio.Copilots.Invoke';
const ID = /^[A-Za-z0-9_.~-]{1,128}$/;
const form = document.querySelector('#lookup-form');
const button = document.querySelector('#lookup-button');
const signInButton = document.querySelector('#microsoft-sign-in');
const status = document.querySelector('#status');
const agentStatus = document.querySelector('#agent-status');
const result = document.querySelector('#result');
const agentResult = document.querySelector('#agent-result');
const sections = document.querySelector('#sections');
let identity;
let apiScope;

function textNode(tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}

function section(title, text) {
  const block = document.createElement('article');
  block.className = 'guidance';
  block.append(textNode('h2', title), textNode('p', text));
  sections.append(block);
}

function date(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'Unknown' : parsed.toLocaleString();
}

function renderFinding(value) {
  const context = value.context;
  const source = context.planning_source;
  const rule = source.rule || {};
  document.querySelector('#finding-title').textContent = rule.displayName || context.rule_id;
  document.querySelector('#severity').textContent = context.severity || 'Severity unknown';
  document.querySelector('#finding-meta').textContent = [context.rule_id,
    context.observed_status !== 'unknown' ? context.observed_status : null,
    `Observed ${date(context.observed_at)}`].filter(Boolean).join(' · ');
  sections.replaceChildren();
  section('What was detected', rule.description || rule.summary || 'Review the violation evidence to confirm the rule condition.');
  if (rule.riskReason) section('Why it matters', rule.riskReason);
  const evidence = document.querySelector('#evidence');
  evidence.replaceChildren();
  for (const finding of source.findings || []) {
    if (finding.stepName || finding.title) evidence.append(textNode('h2', finding.stepName || finding.title));
    if (finding.description) evidence.append(textNode('p', finding.description));
    if (finding.destination_origin) evidence.append(textNode('p', finding.destination_origin));
  }
  if (!evidence.childNodes.length) evidence.append(textNode('p', 'No additional evidence is available in this violation.'));
  evidence.append(textNode('p', `Violation ID: ${context.violation_id}`));
  result.hidden = false;
}

async function plan(id, token, apiToken) {
  const response = await fetch('/plan', { method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiToken}`,
      'X-Copilot-Authorization': `Bearer ${token}` },
    body: JSON.stringify({ violation_id: id }) });
  const value = await response.json();
  if (!response.ok) {
    const error = new Error(value.error || 'The assistant could not complete this review.');
    error.code = /^[a-z][a-z0-9_]{0,48}$/.test(value.code || '') ? value.code : `http_${response.status}`;
    error.finding = value.finding;
    throw error;
  }
  if (!Array.isArray(value.messages) || !value.messages.length || value.source !== 'copilot_studio') {
    throw new Error('The assistant returned an invalid response.');
  }
  return value;
}

function account() {
  return identity?.getActiveAccount() || identity?.getAllAccounts()[0] || null;
}

async function acquireReviewerToken(id, scope = SCOPE) {
  const selected = account();
  if (!selected) {
    sessionStorage.setItem('pending_finding_id', id);
    await identity.loginRedirect({ scopes: [scope] });
    return null;
  }
  identity.setActiveAccount(selected);
  try {
    return (await identity.acquireTokenSilent({ scopes: [scope], account: selected })).accessToken;
  } catch (error) {
    if (!(error instanceof InteractionRequiredAuthError)) throw error;
    sessionStorage.setItem('pending_finding_id', id);
    await identity.acquireTokenRedirect({ scopes: [scope], account: selected });
    return null;
  }
}

async function reviewFinding(id) {
  result.hidden = true;
  agentResult.hidden = true;
  status.textContent = '';
  agentStatus.textContent = '';
  if (!ID.test(id)) { status.textContent = 'Enter a valid violation ID.'; return; }
  button.disabled = true;
  try {
    if (!identity) throw new Error('Microsoft sign-in for the assistant is unavailable.');
    status.textContent = 'Connecting your Microsoft account…';
    const token = await acquireReviewerToken(id);
    if (!token) return;
    const apiToken = await acquireReviewerToken(id, apiScope);
    if (!apiToken) return;
    status.textContent = 'Reviewing the violation…';
    try {
      const answer = await plan(id, token, apiToken);
      renderFinding(answer.finding);
      document.querySelector('#agent-plan').textContent = answer.messages.join('\n\n');
      agentResult.hidden = false;
    } catch (error) {
      if (error.finding) renderFinding(error.finding);
      agentStatus.textContent = `${error.message} Support code: ${error.code || 'client_error'}.`;
    }
    status.textContent = '';
  } catch (error) {
    status.textContent = error.message || 'Unable to review this violation. Try again.';
  } finally {
    button.disabled = false;
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  void reviewFinding(document.querySelector('#finding-id').value.trim());
});

signInButton.addEventListener('click', async () => {
  if (!identity) { agentStatus.textContent = 'Microsoft sign-in for the assistant is unavailable.'; return; }
  try {
    await identity.loginRedirect({ scopes: [SCOPE], prompt: 'select_account' });
  } catch {
    agentStatus.textContent = 'Microsoft sign-in could not start. Try again.';
  }
});

async function initialize() {
  try {
    const response = await fetch('/agent-config.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('Configuration unavailable');
    const config = await response.json();
    if (!ID.test(config.tenantId) || !ID.test(config.clientId)) throw new Error('Configuration invalid');
    if (!/^api:\/\/[0-9a-f-]{36}\/Remediation\.Review$/.test(config.apiScope)) throw new Error('Configuration invalid');
    apiScope = config.apiScope;
    identity = new PublicClientApplication({
      auth: { clientId: config.clientId, authority: `https://login.microsoftonline.com/${config.tenantId}`,
        redirectUri: `${location.origin}/` },
      cache: { cacheLocation: 'sessionStorage' },
    });
    await identity.initialize();
    const redirect = await identity.handleRedirectPromise();
    if (redirect?.account) identity.setActiveAccount(redirect.account);
    if (account()) signInButton.textContent = 'Switch Microsoft account';
    const pending = sessionStorage.getItem('pending_finding_id');
    sessionStorage.removeItem('pending_finding_id');
    if (pending && account()) {
      document.querySelector('#finding-id').value = pending;
      await reviewFinding(pending);
    }
  } catch {
    agentStatus.textContent = 'Microsoft sign-in for the assistant is unavailable.';
  }
}

void initialize();
