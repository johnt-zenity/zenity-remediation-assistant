# Zenity Remediation Assistant 0.1.0-beta.1

Review an AISPM violation from your Zenity integration and receive general remediation guidance grounded in the returned rule and evidence. The assistant reads findings and proposes options. It makes no resource changes.

## Downloads

- `ZenityRemediationAssistant-0.1.0-beta.1.zip`: application source, setup guides and the Copilot solution.
- `ZenityViolationsAgent-0.1.0-beta.1.zip`: importable solution for standalone Copilot chat.
- `SHA256SUMS.txt`: checksums for both ZIP files.

## Set up your installation

Extract the application ZIP and follow [Install the assistant](../deploy/customer/README.md). Configure your own Microsoft registrations, reviewer access and Zenity credentials. Set the API and OAuth endpoints for your Zenity environment.

For standalone chat, follow [Set up the Copilot agent](copilot-customer-portability-spec.md). The source includes the separate `connector_server.py` lookup adapter. Set its service key, put it behind HTTPS, import the solution and configure its connector hostname.

## Beta validation

Live checks passed against an authorized internal production-demo integration through both the review page and chat. Unknown IDs returned no invented finding. A mismatched application context was rejected. A synthetic evidence-injection check withheld its test secret and preserved the distinction between a posture condition and an incident.

The customer source passed 33 Python tests, seven browser-client tests and three customer runtime tests. The solution ZIP contains the scoped lookup action and general-advice instructions. It contains no token-returning workflow or credentials.

Complete sign-in, consent, access restrictions, connection setup and live finding checks in your own environment before inviting reviewers. Fresh customer-tenant installation remains a beta acceptance check.

## Support

Contact [John Travise](mailto:johnt@zenity.io) for setup help, support or debugging. Include the release version, error message and steps to reproduce, plus a correlation ID if one is shown. Diagnostic information stays in your deployment unless you share it.
