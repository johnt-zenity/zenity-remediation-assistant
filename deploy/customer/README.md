# Install the Zenity remediation assistant

Use this guide to connect your Zenity tenant and Microsoft tenant, then run the review page for your reviewers. The service reads one Zenity organization and configured integration. Reviewers sign in with assigned accounts from your Microsoft tenant.

## 1. Set up reviewer access

Use your own tenant for the review application and Copilot agent:

1. Register a single-tenant review API application. Set its requested access token version to `2`, expose the admin-consent delegated scope `api://API_CLIENT_ID/Remediation.Review`, and define a user app role `Remediation.Reviewer`.
2. Require assignment on the API enterprise application. Assign your reviewer group to `Remediation.Reviewer`.
3. Register a single-tenant SPA with the exact redirect URI `https://YOUR_REVIEW_HOST/`. Add delegated permission for the review API scope and `https://api.powerplatform.com/CopilotStudio.Copilots.Invoke`. Complete the consent required by your tenant.
4. Create and publish your Copilot agent in that tenant with Microsoft authentication. Apply the supplied agent instructions and assign the intended reviewers access. The agent receives retrieved context and needs no lookup tool. In Settings > Advanced > Metadata, record its environment ID and schema name for the bundle. See [Microsoft's authenticated SDK integration guide](https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-integrate-web-or-native-app-m365-agents-sdk).

The backend verifies token signature, expiry, issuer, tenant, API audience, SPA caller, scope and reviewer role. The browser obtains separate tokens for the review API and Copilot. Follow [Microsoft's scope and role guidance](https://learn.microsoft.com/en-us/entra/identity-platform/scenario-protected-web-api-verification-scope-app-roles) for the registration and assignments.

## 2. Connect your Zenity tenant

Store the Zenity API client ID and secret for this organization in your host's secret store. The browser and Copilot agent cannot read these credentials.

Create a private credential file on your host or in its secret store with these two entries. Mount it at `/run/secrets/zenity-credentials` inside the container:

```text
CLIENT_ID=YOUR_ZENITY_CLIENT_ID
CLIENT_SECRET=YOUR_ZENITY_CLIENT_SECRET
```

Your installation bundle contains `config/app.json`, `config/connection.json`, agent instructions, deployment metadata and a container build context under `application/`. Confirm the Zenity organization, integration, region label, endpoint values, Microsoft tenant and host are the ones assigned to your installation. The bundle contains no credentials.

The runtime requires these mounted files:

| File | Purpose |
| --- | --- |
| `/run/config/app.json` | Fixed HTTPS origin, tenant, SPA/API IDs and agent configuration |
| `/run/config/connection.json` | Zenity organization, integration, environment endpoint values, token validation values and credential path |
| `/run/secrets/zenity-credentials` | Customer-supplied API client ID and secret |

Your `connection.json` includes the endpoint values for your Zenity environment. For production tenants in EU or US, the API reference lists these values:

- API base: `https://api.zenity.io/`
- OAuth token URL: `https://zenity-prod.eu.auth0.com/oauth/token`
- Audience: `https://zenity-prod.eu.zenity.io/api/v3`
- Issuer: `https://zenity-prod.eu.auth0.com/`

The production API uses these same endpoints for EU and US tenant regions. For another Zenity environment, use the API base URL, OAuth token URL, audience and issuer provided for that environment. Set `region` to a label such as `prod-us`; the endpoint fields control the connection.

```json
{
  "organization_id": "org_YOUR_ORGANIZATION_ID",
  "integration_id": "YOUR_INTEGRATION_ID",
  "organization_name": "your-deployment",
  "region": "your-region-label",
  "api_base": "https://YOUR_REGIONAL_API_HOST/",
  "token_url": "https://YOUR_REGIONAL_AUTH_HOST/oauth/token",
  "audience": "YOUR_REGIONAL_API_AUDIENCE",
  "issuer": "https://YOUR_REGIONAL_AUTH_HOST/",
  "credential_file": "/run/secrets/zenity-credentials"
}
```

Set `REMEDIATION_APP_CONFIG=/run/config/app.json` and `REMEDIATION_CONFIG=/run/config/connection.json`. The credential path in the connection must be `/run/secrets/zenity-credentials`. Grant read access to container UID 1000 through your secret mounting mechanism. Missing or invalid configuration prevents startup. Startup checks local configuration; the first live lookup tests actual credential authorization.

## 3. Build and publish the container image

From the installation bundle's `application/` directory:

```sh
docker build -f deploy/customer/Dockerfile -t REGISTRY/zenity-remediation:BUILD_TAG .
docker push REGISTRY/zenity-remediation:BUILD_TAG
```

Record the pushed digest and deploy `REGISTRY/zenity-remediation@sha256:YOUR_DIGEST`. The image includes the review page, backend and private reader. It excludes demo configuration, local files and credentials and runs as UID 1000.

## 4. Run the service behind HTTPS

For an existing container host, use the included Compose file:

```sh
export REMEDIATION_IMAGE=REGISTRY/zenity-remediation@sha256:YOUR_DIGEST
export REMEDIATION_CONFIG_DIR=/absolute/path/to/customer-bundle/config
export ZENITY_CREDENTIAL_FILE=/absolute/path/to/private/zenity-credentials
docker compose -f deploy/customer/compose.yaml up -d
```

Compose binds port 8080 on loopback. Put your HTTPS reverse proxy in front of it, using exactly the origin in `app.json` and SPA redirect registration. Allow a request timeout of at least 180 seconds. The container uses a read-only root filesystem, temporary `/tmp`, dropped capabilities and a 1 GiB memory limit. No separately exposed lookup service, service key or Corpo Valley headers are required.

For Azure Container Apps, use `deploy/customer/azure-container-app.json`. Supply an existing Consumption environment, registry pull credential, immutable image digest, Zenity credential contents, connection JSON and application JSON as template parameters. Store credential-bearing parameter files privately. This template deploys the entire application with HTTPS ingress, 0.5 vCPU, 1 GiB memory, zero minimum replicas and one maximum replica.

```sh
az deployment group validate \
  --resource-group YOUR_RESOURCE_GROUP \
  --template-file deploy/customer/azure-container-app.json \
  --parameters @parameters.local.json
az deployment group create \
  --resource-group YOUR_RESOURCE_GROUP \
  --template-file deploy/customer/azure-container-app.json \
  --parameters @parameters.local.json
```

The ARM parameter file needs `appName`, `location`, `environmentId`, `registryServer`, `registryPullUsername`, `registryPullPassword`, `imageDigest`, `zenityCredentials`, `connection` and `appConfig`. Configure your chosen hostname and certificate in Container Apps. If using its generated hostname, update `appConfig.origin` and the SPA redirect URI to that exact hostname, then redeploy the template. The API admits requests only from the configured origin and assigned reviewers; the static sign-in page and health endpoint contain no violation data.

Allow outbound HTTPS to `login.microsoftonline.com`, `api.powerplatform.com` and the Zenity API and OAuth hosts configured for your environment. Account for published agent endpoint hosts used by the Microsoft SDK under your network policy. Never log authorization headers, credential files, prompts or raw violation responses.

## 5. Check access and review a finding

1. Sign in as an assigned reviewer and review a real violation. Confirm the violation ID, rule ID and observation time match Zenity.
2. Confirm that an unassigned reviewer, another tenant, a missing token and forged identity headers cannot access a finding.
3. Submit an unknown ID and confirm Copilot does not receive finding context. Review advice for each resource type your team supports.
4. Test sign-in renewal and a cold container start. Confirm sensitive values are absent from browser responses and Copilot context.
5. Cause a planning failure and confirm the finding remains visible with a safe error. Verify the service makes no resource changes.

Record your image digest, Microsoft environment, agent version and results. Complete these checks with your own Microsoft tenant, Zenity connection and reviewer accounts before inviting users.
