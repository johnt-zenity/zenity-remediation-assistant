# Set up the standalone Copilot agent

Use this guide to add the standalone Zenity remediation agent to your Microsoft environment. For the review page and its integrated agent experience, follow [the installation guide](../deploy/customer/README.md).

## Before you begin

Have these items ready:

- The [Copilot solution beta ZIP](https://github.com/johnt-zenity/zenity-remediation-assistant/releases/tag/v0.1.0-beta.1).
- An HTTPS address for the lookup service and a separate connector service key.
- Your Zenity API client ID and client secret, plus the organization and integration IDs the service will use.
- A Microsoft 365 environment where you can import solutions and assign agent access.

## 1. Connect the lookup service to Zenity

Configure the service for one Zenity organization and integration. Put your `CLIENT_ID` and `CLIENT_SECRET` in the hosting platform's secret store and mount them into the service. Keep them out of Copilot Studio, the solution ZIP, and conversation inputs. Create a separate random connector service key of at least 32 characters for `X-API-Key`.

The service uses the API base URL, OAuth token URL, audience and issuer configured for your Zenity region. Obtain these values from your Zenity administrator and confirm they match your organization before connecting the agent.

### Run the standalone lookup service

The standalone chat uses a separate lookup adapter. It is included as `connector_server.py` in the application source ZIP. The review-page service at `/plan` does not implement this connector endpoint.

On a host with Python 3.12 or later, mount the same fixed-scope `connection.json` and Zenity credential file described in the installation guide. Set `REMEDIATION_CONNECTOR_KEY` from your secret store to a separate random value of at least 32 characters, then run from the repository root:

```sh
python3 connector_server.py --live-config /run/config/connection.json --bind 127.0.0.1 --port 8766
```

Put your HTTPS reverse proxy in front of this loopback listener and forward `POST /api/lookup` with the `X-API-Key` header. Use this HTTPS hostname in the custom connector. Keep the listener private to that proxy, manage the process with your hosting platform, and restrict agent access to your reviewer group. The adapter validates the connection scope before reading Zenity and supports no resource changes.

## 2. Import and connect the agent

1. In Power Apps, select the environment where you want the agent, open **Solutions**, and import the downloaded solution ZIP.
2. Open the **Zenity remediation lookup** custom connector. Replace `lookup.customer.example` with your lookup service's HTTPS hostname and save the connector.
3. Create a connector connection using the connector service key. The key protects the service connection and is separate from your Zenity API credentials.
4. Open the imported agent in Copilot Studio and confirm its `LookupViolation` action uses that connection.

## 3. Give reviewers access

Require Microsoft authentication for the agent. Assign access to the reviewer group authorized to see findings for this Zenity organization. Keep the organization and integration fixed in the service configuration. Reviewers cannot select another customer through chat.

## 4. Verify the setup

Test with an authorized reviewer and a real violation ID. Confirm the agent returns the matching finding and proposes remediation from its rule and evidence. Verify that a reviewer without access is denied, an unknown ID returns no invented finding, and no Azure or Zenity resource changes are made.

The agent reads findings and proposes a plan. Validate the general advice against your environment before making changes.
