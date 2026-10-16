# How the review service handles your request

The review page accepts a violation ID. Its private backend checks your Microsoft sign-in, reads the matching violation from the Zenity organization configured for this installation, removes selected sensitive fields, and gives the resulting context to your Copilot agent. The page shows the same violation alongside the proposed plan.

## Your access controls

Your Microsoft tenant verifies reviewer identity, access token signature and expiry, application audience, review permission and reviewer role before lookup. The browser uses separate tokens for the review API and Copilot. The service trusts verified tokens and does not use identity claims supplied in request headers.

## Your Zenity connection

The service reads one configured Zenity organization and integration. Your installation configuration supplies the API base URL, OAuth token URL, API audience and expected token issuer for your Zenity environment. These HTTPS endpoints are fixed for the installation and cannot be selected through the page or chat. The service checks the returned token's organization, audience, issuer and expiry before making the API request. It loads your `CLIENT_ID` and `CLIENT_SECRET` from the host's secret store. These values stay in the private service and are never sent to the browser or Copilot. The page submits only the violation ID. A failed or denied lookup prevents the agent from receiving finding context.

## Information sent to Copilot

The service sends the rule details and selected evidence needed to propose remediation. It removes recognized secrets and email addresses, resource names and identifiers, unknown nested fields, and URL paths and queries. Redaction recognizes specific patterns and may leave sensitive text in descriptions. Review the projected data against your organization's policy before sending real findings to Copilot.

The agent can read findings and propose a plan. It has no operation for changing resources or violation status. Its recommendations provide general advice about the observed condition and require validation against the customer environment.

## Checks to complete

Before production use, confirm that invalid or expired Microsoft tokens are rejected, unauthorized reviewers are denied, a failed lookup prevents agent invocation, and an agent failure leaves the Zenity finding visible. Test a real violation in your tenant, check the redacted fields, validate recommendations against your platform, and verify that the application makes no changes.
