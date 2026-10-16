import { createRemoteJWKSet, jwtVerify } from 'jose';
export function createReviewerAuth(config, trustedKeys) {
  const issuer = `https://login.microsoftonline.com/${config.tenantId}/v2.0`;
  const keys = trustedKeys || createRemoteJWKSet(new URL(`https://login.microsoftonline.com/${config.tenantId}/discovery/v2.0/keys`),
    { timeoutDuration: 5000, cooldownDuration: 30000 });
  return async token => {
    const { payload } = await jwtVerify(token, keys, { issuer, audience: config.apiClientId,
      algorithms: ['RS256'], requiredClaims: ['exp', 'iat', 'tid', 'oid', 'scp', 'azp'], clockTolerance: 5 });
    if (payload.ver !== '2.0' || payload.tid !== config.tenantId || payload.azp !== config.clientId ||
        typeof payload.oid !== 'string' || typeof payload.scp !== 'string' ||
        !payload.scp.split(' ').includes('Remediation.Review') ||
        !Array.isArray(payload.roles) || !payload.roles.includes('Remediation.Reviewer')) throw new Error('Reviewer access denied.');
    return { id: payload.oid };
  };
}
