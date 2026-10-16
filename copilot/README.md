# Use the standalone Copilot agent

The standalone agent looks up a Zenity violation and proposes remediation from the returned rule and evidence. It can read findings. It cannot change Zenity or Microsoft resources.

## What you need

- The [Copilot solution beta ZIP](https://github.com/johnt-zenity/zenity-remediation-assistant/releases/tag/v0.1.0-beta.1).
- An HTTPS lookup service configured for one Zenity organization and integration.
- Your Zenity `CLIENT_ID` and `CLIENT_SECRET`, stored in the lookup service's secret store.
- A separate connector service key for the agent's `X-API-Key` connection.
- A Microsoft reviewer group with access to your Copilot environment.

## Connect the agent

1. Configure the lookup service with your Zenity credentials and fixed organization and integration.
2. Download the solution ZIP and import it in Power Apps under **Solutions**.
3. Set the connector hostname to your HTTPS lookup service and create its connection using the connector service key.
4. In Copilot Studio, confirm `LookupViolation` uses that connection and require Microsoft authentication for the agent.
5. Assign access to your authorized reviewer group and test an allowed, denied, and unknown violation ID.

For an existing agent, use [the standalone instructions](standalone-agent-instructions.md). Attach the finding lookup action with `violation_id` as its only input. Remove token acquisition workflows from the agent. A successful tool response contains the finding context and `outcome=ok`; an access token is never a valid finding response. The returned rule and evidence supply the context needed to propose remediation.

Keep Zenity credentials in the service secret store. The connector service key is used only to connect Copilot to the service. Do not enter either secret in the agent instructions, conversation, or solution.

For the review page, use [the installation guide](../deploy/customer/README.md). The page retrieves the finding before invoking the agent and passes the redacted context directly.
