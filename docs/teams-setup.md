# Set up the remediation agent in Teams

The Teams agent calls an HTTPS lookup service that you host. That service reads a finding from your Zenity organization and returns redacted evidence to the agent. Complete the service setup before testing a violation in Teams.

For Azure Container Apps with its generated HTTPS endpoint, follow [the Azure and Teams guide](teams-azure-setup.md). The Linux instructions below are an alternative for an existing host.

## Before the session

Have these ready:

1. Access to the application source ZIP and Copilot solution ZIP from the same release.
2. A Power Platform environment with Dataverse, solution import access, and Copilot Studio access. Use the same environment in Power Apps and Copilot Studio.
3. A Teams account licensed and allowed to use custom agents in that Microsoft tenant.
4. A host with Python 3.12 or later, an HTTPS hostname, and a trusted TLS certificate. The example below uses a Linux host with systemd and Nginx. Provisioning the host, DNS, certificate, and Microsoft access can require work before the walkthrough.
5. Your Zenity client ID and secret, organization ID, integration ID, and environment endpoint values.
6. A real violation ID from that integration, with its expected rule ID available for comparison.

Keep credentials in your secret store or restricted files on the host. Do not paste them into chat, agent instructions, or shared meeting notes.

## Deployment invariants

- **Fixed scope:** One configured Zenity organization and integration per lookup service.
- **Separate credentials:** Zenity credentials stay on the host. Copilot connects using a separate service key.
- **Private listener:** Only the HTTPS proxy can reach the Python listener.
- **Restricted access:** The service key authorizes reads within the configured scope. Anyone holding it can call the endpoint, so distribute it only to authorized reviewers through approved connection setup.
- **Read only:** The service retrieves findings and performs no remediation changes.

## 1. Install and configure the lookup service

Use your approved hosting and secret management process. For the Linux example, extract the application source ZIP, then copy its Python modules and `profiles/` directory into `/opt/zenity-remediation`. If your ZIP contains an `application/` directory, copy from that directory.

Create a dedicated service account and restricted configuration directory:

```sh
sudo useradd --system --home-dir /opt/zenity-remediation --shell /usr/sbin/nologin zenity-remediation
sudo install -d -o root -g zenity-remediation -m 0750 /etc/zenity-remediation
```

Make the application files readable by the service account and writable only by your deployment administrator. Check `python3 --version` before proceeding.

Create `/etc/zenity-remediation/connection.json`, replacing every placeholder with the values assigned to your Zenity environment:

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
  "credential_file": "/etc/zenity-remediation/zenity-credentials"
}
```

The endpoint fields control the connection. The `region` field is a label. Preserve the trailing slash on `api_base` and the exact issuer and audience values provided for your environment.

Create `/etc/zenity-remediation/zenity-credentials` using your secret store or a secure editor:

```text
CLIENT_ID=YOUR_ZENITY_CLIENT_ID
CLIENT_SECRET=YOUR_ZENITY_CLIENT_SECRET
```

Generate a random service key of at least 32 characters with your secret manager. Store it in `/etc/zenity-remediation/service.env` as:

```text
REMEDIATION_CONNECTOR_KEY=YOUR_SEPARATE_RANDOM_SERVICE_KEY
```

Protect all three configuration files:

```sh
sudo chown root:zenity-remediation /etc/zenity-remediation/connection.json /etc/zenity-remediation/zenity-credentials /etc/zenity-remediation/service.env
sudo chmod 0640 /etc/zenity-remediation/connection.json /etc/zenity-remediation/zenity-credentials /etc/zenity-remediation/service.env
```

Create `/etc/systemd/system/zenity-remediation.service`:

```ini
[Unit]
Description=Zenity remediation lookup
Wants=network-online.target
After=network-online.target

[Service]
User=zenity-remediation
Group=zenity-remediation
WorkingDirectory=/opt/zenity-remediation
EnvironmentFile=/etc/zenity-remediation/service.env
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /opt/zenity-remediation/connector_server.py --live-config /etc/zenity-remediation/connection.json --bind 127.0.0.1 --port 8766
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

Start it and inspect startup status:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now zenity-remediation
sudo systemctl status zenity-remediation --no-pager
```

Startup validates configuration and reads the credential file. A successful finding lookup is still required to verify Zenity authorization.

## 2. Expose the lookup through HTTPS

Configure your existing HTTPS proxy with your hostname and certificate. This Nginx server block forwards only the lookup path to the loopback listener:

```nginx
server {
    listen 443 ssl;
    server_name lookup.YOUR_DOMAIN;
    ssl_certificate /YOUR_CERTIFICATE_PATH/fullchain.pem;
    ssl_certificate_key /YOUR_CERTIFICATE_PATH/privkey.pem;
    client_max_body_size 8k;
    access_log off;

    location = /api/lookup {
        limit_except POST { deny all; }
        proxy_pass http://127.0.0.1:8766;
        proxy_http_version 1.1;
        proxy_set_header X-API-Key $http_x_api_key;
        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 15s;
    }

    location / { return 404; }
}
```

Validate with `sudo nginx -t`, then reload Nginx through your normal deployment process. Permit inbound HTTPS to the proxy; keep port 8766 closed to external clients. Allow outbound HTTPS to your configured Zenity API and OAuth endpoints. Do not log request bodies, authorization headers, or finding contents.

The base URL is expected to return 404. This adapter has no health page. An unauthenticated JSON POST to `/api/lookup` should return 401:

```sh
curl --silent --show-error --include https://lookup.YOUR_DOMAIN/api/lookup \
  --header 'Content-Type: application/json' \
  --data '{"violation_id":"00000000000000000000000000000000"}'
```

## 3. Import and connect in Power Apps

1. Open Power Apps, select the target environment, and choose **Solutions > Import solution**. Select the Copilot solution ZIP and continue through the import wizard. Wait for the success message.
2. Open the imported solution, choose **Objects**, then open **Zenity remediation lookup**. The connector editor may open in a separate Power Automate tab.
3. Choose **Edit > General**. Set **Host** to your HTTPS hostname, without `https://` or a path. Keep **HTTPS** selected and **Base URL** set to `/`. Choose **Update connector**.
4. On **Test**, create a connection using the separate connector service key. Keep the Zenity client secret on the host.
5. Run **LookupViolation** with your real violation ID. Require `outcome=ok`, `mode=live`, and a matching `context.violation_id` and rule ID. HTTP 200 alone does not establish success.
6. Return to the solution tab and choose **Done** if it displays “Currently editing a Custom Connector.”

## 4. Connect and test in Copilot Studio

1. Open the imported **Zenity Violations Agent Customer Draft** in the same environment.
2. Open **Tools > Read a Zenity finding for remediation planning**. Complete the connection configuration. The packaged action uses user credentials, so reviewers may need to create or verify their own authorized service connection.
3. Keep Microsoft authentication enabled. Restrict agent access to the reviewers authorized for this service's Zenity scope.
4. In **Test your agent**, supply the real violation ID and check the returned rule, observation time, and general advice. Complete any connection verification prompt, then repeat in a new conversation.
5. Publish after the lookup succeeds. An import or published status by itself does not verify the connection.

## 5. Install in Teams

1. Open **Channels > Microsoft 365 and Microsoft Teams**. If Channels is hidden, open the extra tabs menu. In the newer designer, use **Build > Channels > Add channel**.
2. Select Teams only if that is your intended destination. Choose **Add channel**, then **See agent in Teams** or **View in Microsoft Teams**.
3. Sign in to Teams with an authorized account in the same tenant. Add the agent for your own test first. Broader distribution may require Teams administrator approval.
4. Repeat the finding lookup in a fresh Teams conversation. A successful Studio test does not establish Teams acceptance.

See [Microsoft's Teams channel guide](https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams) for tenant distribution options.

## Acceptance checks

| Vector | Input | Required result |
| --- | --- | --- |
| TS01 | JSON POST without service key | HTTP 401; no finding content |
| TS02 | Authorized real violation ID | `outcome=ok`, `mode=live`, exact violation and expected rule |
| TS03 | Unknown all-zero ID | No invented finding or remediation proposal |
| TS04 | Account outside the reviewer audience | Agent access denied |
| TS05 | Real ID in Teams | Same finding as the connector test; general advice; no changes performed |

## Troubleshooting

| Symptom | Check |
| --- | --- |
| “You need a paid subscription to use Microsoft Teams” | The signed-in account needs a Teams license and tenant access. Copilot Studio access alone is insufficient. |
| “This app cannot be found” | Check the Teams account and tenant, agent access, channel setup, and app policy. |
| Connector 401 | Check the connector service key and that the proxy forwards `X-API-Key`. |
| `auth_failed` | Check the host's Zenity credentials, organization, OAuth endpoints, audience, and issuer. |
| `not_found_or_denied` | Check the exact violation ID against the configured integration and authorized scope. |
| Timeout | Check service status, HTTPS reachability, outbound access, proxy limits, and upstream response time. |
| Connector blocked by policy | The Power Platform administrator must review the connector and hostname against the tenant's policy. |

Share safe error codes, correlation IDs, and deployment version for troubleshooting. Keep credentials and finding contents out of support messages.
