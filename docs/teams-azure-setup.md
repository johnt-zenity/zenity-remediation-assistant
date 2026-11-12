# Install the remediation agent in Teams with Azure

Use this guide to host the lookup service in your Azure subscription, connect it to your Zenity environment, and install the agent in Teams. Azure Container Apps supplies the HTTPS hostname and certificate. The agent retrieves findings and provides general remediation advice. It performs no resource changes.

**Validation status:** The solution import and Teams channel activation were rehearsed. This API-key Azure deployment recipe and a live finding conversation in Teams still require acceptance in your environment. The older Azure demo uses a different Entra connector contract.

For an interactive installation guide, download [the walkthrough webpage](teams-walkthrough.html) and open it in your browser. The page runs locally. Its progress checklist stores only completion state in that browser.

For instructor-led training, use the [four-session course and lab walkthrough](https://github.com/zenitysec/zenity-remediation-assistant/blob/main/docs/training/README.md).

## 1. Confirm access and prerequisites

Have these available before starting:

1. An Azure subscription and approved region. You need permission to create a resource group, registry, Container Apps environment, app, and user-assigned identity. An authorized administrator must be available for registry role assignments if you cannot make them.
2. Azure CLI with the Container Apps extension, and permission to run builds in the registry.
3. Power Apps and Copilot Studio access in the same Microsoft tenant and Power Platform environment, with Dataverse and permission to import solutions and configure custom connectors. Tenant policy must permit the connector and its HTTPS destination.
4. A licensed Teams account in that tenant, authorized to install custom agents. Organization-wide distribution may require Teams administrator approval.
5. The application source and Copilot solution ZIPs from the same release.
6. Your Zenity client ID and secret, organization ID, integration ID, and assigned API/OAuth endpoint values. Have a real violation ID from that integration and its expected rule ID available.

Keep credentials in approved secret storage. Do not send them by email or paste them into agent instructions, conversations, or shared meeting notes. Creating Azure resources, building and storing images, logging, and running the app can incur charges. This recipe keeps one replica running to reduce cold-start delays.

## 2. Understand the connection

```text
Teams → Copilot Studio → HTTPS lookup service → Zenity API
```

The service fixes the Zenity organization and integration at deployment time. Reviewers supply only a violation ID. The Zenity client credentials remain on the service. A separate random connector service key protects `POST /api/lookup` through `X-API-Key`.

The key authorizes reads within the configured scope. Anyone holding it can call that service, so distribute it only through approved connection setup to authorized reviewers. Microsoft authentication restricts access to the agent; it does not replace the service key check.

## 3. Create or select Azure resources

Sign in and select the intended subscription:

```sh
az login
az account set --subscription YOUR_SUBSCRIPTION_ID
az account show --query '{subscription:name,tenant:tenantId}' --output table
az extension add --name containerapp --upgrade
```

In Azure Portal, create or select:

1. A resource group in your approved Azure region.
2. An Azure Container Registry. Record its name, login server, and resource ID.
3. A Container Apps environment with a Consumption workload profile. Record its resource ID.
4. A user-assigned managed identity. Record its resource ID and principal/object ID.

In the registry's access control settings, an authorized administrator must grant the managed identity image-pull access. Use `AcrPull` for a registry using standard RBAC permissions, or `Container Registry Repository Reader` for a registry using ABAC repository permissions. Apply repository restrictions according to your policy. The deploying account must be able to assign the identity to the app. See [Microsoft's managed identity guidance](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-authentication-managed-identity).

Confirm registry and environment network settings allow the build and app to reach the registry. The app also needs outbound HTTPS to the assigned Zenity API and OAuth endpoints.

## 4. Build the lookup image

Extract the application source ZIP. Work from the directory containing `connector_server.py` and `engine.py`. A generated deployment bundle may place these inside `application/`.

Use [Dockerfile.lookup](../deploy/standalone/Dockerfile.lookup). The build directory must contain only application files. From a clean release extraction:

```sh
mkdir lookup-build
cp connector_server.py engine.py profiles.py evidence.py live_guidance.py zenity_auth.py zenity_reader.py lookup-build/
if [ -f lookup_result.py ]; then cp lookup_result.py lookup-build/; fi
cp -R profiles lookup-build/
cp deploy/standalone/Dockerfile.lookup lookup-build/

az acr build --registry YOUR_REGISTRY_NAME \
  --image zenity-remediation-lookup:0.1.0-beta.1 \
  --file Dockerfile.lookup lookup-build
```

If using an older release ZIP without `deploy/standalone/`, download the Dockerfile linked above into `lookup-build/Dockerfile.lookup` before building. Do not put configuration or credential files in the build directory.

Record the resulting image digest:

```sh
az acr repository show --name YOUR_REGISTRY_NAME \
  --image zenity-remediation-lookup:0.1.0-beta.1 \
  --query digest --output tsv
```

Use `YOUR_REGISTRY.azurecr.io/zenity-remediation-lookup@sha256:YOUR_DIGEST` in the deployment parameters to pin the deployed image.

## 5. Prepare deployment parameters

Download [lookup-service.azure.json](../deploy/standalone/lookup-service.azure.json) and [lookup.parameters.example.json](../deploy/standalone/lookup.parameters.example.json). Copy the example to a private location outside Git:

```sh
cp lookup.parameters.example.json /PRIVATE_PATH/lookup.parameters.local.json
chmod 600 /PRIVATE_PATH/lookup.parameters.local.json
```

Replace every placeholder using a secure editor:

| Parameter | Value |
| --- | --- |
| `appName` | Unique container app name in the resource group |
| `location` | Azure region containing your Container Apps environment |
| `environmentId` | Full Container Apps environment resource ID |
| `identityId` | Full user-assigned managed identity resource ID |
| `registryServer` | Registry login server, without `https://` |
| `image` | Image reference with the recorded digest |
| `serviceKey` | Separate random service key, at least 32 characters, generated by your secret manager |
| `zenityCredentials` | Two-line credential string shown below |
| `connection` | Fixed Zenity scope and assigned environment settings |

The credential string inside JSON uses escaped newlines:

```json
"zenityCredentials": {
  "value": "CLIENT_ID=YOUR_ZENITY_CLIENT_ID\nCLIENT_SECRET=YOUR_ZENITY_CLIENT_SECRET\n"
}
```

Configure the connection object:

```json
{
  "organization_id": "org_YOUR_ORGANIZATION_ID",
  "integration_id": "YOUR_INTEGRATION_ID",
  "organization_name": "your-deployment",
  "region": "your-region-label",
  "api_base": "https://YOUR_API_HOST/",
  "token_url": "https://YOUR_AUTH_HOST/oauth/token",
  "audience": "YOUR_API_AUDIENCE",
  "issuer": "https://YOUR_AUTH_HOST/",
  "credential_file": "/run/secrets/zenity-credentials"
}
```

The endpoint fields control the connection; `region` is a label. Preserve the trailing slash on `api_base` and the exact issuer/audience values assigned to your environment. Do not substitute endpoints based only on geographic region.

The template stores the connection, Zenity credentials, and service key as Container Apps secrets. It mounts the credential/configuration files under `/run/secrets` and supplies the service key through a secret-backed environment variable. Protect the local parameter file according to your secret-retention policy.

## 6. Deploy and check HTTPS

Review the template before deployment. It creates one externally reachable HTTPS endpoint with the service key check enabled, managed identity registry authentication, 0.5 vCPU, 1 GiB memory, and one running replica. No separate virtual machine, Nginx installation, DNS record, or custom certificate is required for the Azure-generated hostname.

```sh
az deployment group validate --resource-group YOUR_RESOURCE_GROUP \
  --template-file lookup-service.azure.json \
  --parameters @/PRIVATE_PATH/lookup.parameters.local.json

az deployment group create --resource-group YOUR_RESOURCE_GROUP \
  --template-file lookup-service.azure.json \
  --parameters @/PRIVATE_PATH/lookup.parameters.local.json \
  --query properties.outputs.hostname.value --output tsv
```

Record the returned hostname. In Azure Portal, open the app and confirm its revision is running. Ingress targets container port `8080`; the platform terminates HTTPS. Do not add a separate external TCP port. See [Microsoft's HTTPS ingress documentation](https://learn.microsoft.com/en-us/azure/container-apps/ingress-overview).

Check that requests without a service key are denied:

```sh
curl --silent --show-error --include https://YOUR_APP_HOST/api/lookup \
  --header 'Content-Type: application/json' \
  --data '{"violation_id":"00000000000000000000000000000000"}'
```

Expect HTTP `401` with no finding content. The root URL has no health page and may return `401` or `404`, depending on the request. A successful startup or anonymous rejection does not verify Zenity authorization.

## 7. Import the Copilot solution and test the connector

1. Open Power Apps and select the target environment. Choose **Solutions > Import solution**, select the Copilot solution ZIP, and continue through the wizard. Wait for the success message.
2. Open the imported solution, then **Objects > Zenity remediation lookup**. The connector editor may open in a separate Power Automate tab.
3. Choose **Edit > General**. Replace `lookup.customer.example` with the Azure hostname. Enter the hostname only, without `https://` or a path. Keep **HTTPS** and **Base URL** `/`. Choose **Update connector**.
4. On **Test**, create a connection using the separate connector service key. Do not enter the Zenity client secret here.
5. Run **LookupViolation** with your real violation ID. Require `outcome=ok`, `mode=live`, the exact `context.violation_id`, and the expected rule ID. HTTP `200` alone is insufficient because safe lookup failures can also return `200`.
6. Return to Power Apps and choose **Done** if it displays “Currently editing a Custom Connector.”

## 8. Configure and publish the agent

1. Open **Zenity Violations Agent Customer Draft** in Copilot Studio in the same environment.
2. Open **Tools > Read a Zenity finding for remediation planning** and complete its connection configuration. The packaged action uses user credentials. Each reviewer may need to create or verify an authorized service connection.
3. Keep Microsoft authentication enabled and restrict agent access to the authorized reviewer audience for this Zenity scope.
4. Start a fresh test conversation. Ask `Explain violation YOUR_REAL_VIOLATION_ID and give general remediation guidance.` Complete any connection verification prompt, then repeat in a new conversation.
5. Compare the finding, rule ID, and observation time with the connector result. Confirm the advice is general and no changes are performed. Publish after the lookup succeeds.

## 9. Install and test in Teams

1. Open **Channels > Microsoft 365 and Microsoft Teams**. If Channels is hidden, use the extra tabs menu. In the newer designer, use **Build > Channels > Add channel**.
2. Choose Teams only if that is the desired destination. Add the channel, then choose **See agent in Teams** or **View in Microsoft Teams**.
3. Confirm Teams is signed in to the authorized account in the same tenant. Add the agent for your own test first.
4. Start a fresh conversation and repeat the real violation lookup. Complete any connection verification prompt. Require the same finding and rule as the connector test.
5. After the personal test succeeds, follow your Teams app approval and reviewer distribution process. See [Microsoft's Teams publishing guide](https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams).

A published status or successful Studio test does not establish that Teams acceptance passed.

## 10. Record acceptance results

| Vector | Input | Required result |
| --- | --- | --- |
| AZT01 | HTTPS request without service key | HTTP 401 and no finding content |
| AZT02 | Authorized real violation ID in connector test | Live outcome, exact finding and expected rule |
| AZT03 | Unknown all-zero violation ID | No invented finding or finding-specific advice |
| AZT04 | Account outside the reviewer audience | Agent access denied |
| AZT05 | Real ID in a fresh Teams conversation | Same finding and rule, general guidance, no changes performed |

Record the version, completed checks, and safe error/correlation codes for any failure. Keep credentials and private finding contents out of support messages.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Image pull failure | Image digest, managed identity assignment, registry role model, network reachability, and role propagation |
| App does not start | Revision system logs, required secret files, credential format, endpoint settings, and minimum service key length |
| Teams requests a paid subscription | Teams license and tenant access for the signed-in account |
| Teams cannot find the app | Account/tenant, agent sharing, channel setup, and Teams app policy |
| Connector returns 401 | Service key and `X-API-Key` header |
| `auth_failed` | Zenity client credentials, organization, OAuth endpoint, audience, and issuer |
| `not_found_or_denied` | Exact violation ID, configured integration, and authorized scope |
| Timeout | Revision health, outbound HTTPS, upstream response time, and connector timeout |
| Policy blocks the connector | Power Platform policy review for the connector and hostname |

For an existing Linux host instead, use [the systemd and Nginx setup](teams-setup.md).
