import { readFileSync } from 'node:fs';
const GUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export function validateConfig(config) {
  if (!config || ['tenantId', 'clientId', 'apiClientId', 'environmentId'].some(key => !GUID.test(config[key] || '')) ||
      !/^[A-Za-z0-9_]{1,128}$/.test(config.schemaName || '')) throw new Error('Invalid Microsoft configuration.');
  const url = new URL(config.origin);
  if (url.protocol !== 'https:' || url.origin !== config.origin || url.username || url.password) throw new Error('An exact HTTPS origin is required.');
  return Object.freeze({ tenantId: config.tenantId, clientId: config.clientId, apiClientId: config.apiClientId,
    environmentId: config.environmentId, schemaName: config.schemaName, origin: url.origin });
}
export function loadConfig(path = process.env.REMEDIATION_APP_CONFIG) {
  if (!path) throw new Error('REMEDIATION_APP_CONFIG is required.');
  return validateConfig(JSON.parse(readFileSync(path, 'utf8')));
}
export function browserConfig(config) {
  return { tenantId: config.tenantId, clientId: config.clientId,
    apiScope: `api://${config.apiClientId}/Remediation.Review` };
}
