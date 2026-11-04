# Connect your Copilot agent to the review page

The review page signs you in through your Microsoft tenant. After you submit a violation ID, the private service retrieves the finding from Zenity and passes selected, redacted context to your published Copilot Studio agent. The page displays the finding and the agent's proposed plan together.

## Set up your agent

1. Create or select a Copilot Studio agent in your Microsoft tenant. Enable Microsoft authentication and publish it.
2. Add the supplied [agent instructions](../agent-instructions.md). The review page supplies the violation context, so the agent does not need a lookup connector.
3. Assign the reviewers who should be allowed to use the page and agent.
4. During installation, provide your tenant ID, SPA client ID, Copilot environment ID and agent schema name. Keep these values aligned with the registrations and published agent in your tenant.

## Sign-in and data flow

The browser obtains one Microsoft token for the review API and a separate token for Copilot. The service validates reviewer access before it reads a violation. Zenity credentials stay in the service host. The browser and Copilot receive neither those credentials nor an access token for Zenity.

The service sends selected rule details and evidence to Copilot. Review those fields against your data policy before using real findings. The agent can recommend changes but cannot apply them. Follow [the installation guide](../../deploy/customer/README.md) to configure the host and verify reviewer access.
