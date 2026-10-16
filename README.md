# Zenity Remediation Assistant

Review an AISPM violation from your Zenity tenant and receive a proposed remediation plan from your Copilot Studio agent. The assistant displays the finding and plan together. It does not change your resources or violation status.

## Choose how your team will use it

- **Review page:** Follow [Install the assistant](deploy/customer/README.md) to connect your Microsoft tenant and Zenity organization, host the page, and verify reviewer access.
- **Standalone Copilot chat:** Download the [Copilot solution beta](https://github.com/johnt-zenity/zenity-remediation-assistant/releases/tag/v0.1.0-beta.1), then follow [Set up the Copilot agent](docs/copilot-customer-portability-spec.md) to connect it to your lookup service.

## What you need

- A Zenity API client ID and client secret for the organization you want to review.
- A configured Zenity integration and the region-specific API and OAuth settings assigned to your organization.
- A Microsoft tenant, a published Copilot Studio agent, and a reviewer group.
- An HTTPS host for the review page or lookup service.

Store the Zenity credentials in the service host's secret store. They are not sent to the browser or Copilot. The standalone chat connection uses a separate connector service key.

## Review and privacy

The service retrieves a finding before asking Copilot for a plan. It sends selected rule details and redacted evidence. Redaction removes recognized secrets, email addresses, resource names and IDs, unknown nested fields, and URL paths and queries. Narrative text may still contain sensitive information, so review the fields sent to Copilot against your organization's data policy.

Recommendations provide general guidance about the observed condition. Validate their relevance to your environment before making changes. Microsoft conversation retention follows your tenant settings.

## Check your setup

Before inviting reviewers, use [the installation checks](docs/customer-deployment-spec.md) to confirm sign-in, access restrictions, Zenity lookup, finding identity, safe failures, and read-only behavior. [How it works](HOW_IT_WORKS.md) explains the request and authentication flow.

## Beta release

[Download v0.1.0-beta.1](https://github.com/johnt-zenity/zenity-remediation-assistant/releases/tag/v0.1.0-beta.1). The application ZIP contains the customer application source, setup guides and Copilot solution. The separate Copilot solution ZIP installs the standalone chat agent. Configure your own Microsoft and Zenity connections, then complete the installation checks before inviting reviewers.

## Support

For setup help, support, or debugging, contact [John Travise](mailto:johnt@zenity.io). Include the release version, error message and steps to reproduce. Include a correlation ID if one is shown. Diagnostic information stays in your deployment unless you choose to share it.
