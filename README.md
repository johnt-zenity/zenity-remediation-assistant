# Zenity Remediation Assistant

Review an AISPM violation from your Zenity tenant and receive a proposed remediation plan from your Copilot Studio agent. The assistant displays the finding and plan together. It does not change your resources or violation status.

## Choose your installation

1. **Teams agent:** Follow [Install in Teams with Azure](docs/teams-azure-setup.md). Deploy the HTTPS lookup service in your Azure subscription, connect your Zenity environment, import the Copilot solution, and test a finding in Teams.
2. **Review page:** Follow [Install the assistant](deploy/customer/README.md) to host the browser application with Microsoft sign-in and an integrated Copilot response.
3. **Existing service host:** Use [the standalone agent guide](docs/copilot-customer-portability-spec.md). An [existing Linux host](docs/teams-setup.md) can run the lookup service behind your HTTPS proxy.

## Team training

Use the [four-session Copilot Studio Teams course](docs/training/README.md) for a step-by-step build, connector setup, testing and Teams publication. It includes an editable deck, a workbook, exact sample inputs and a test results sheet.

## Teams setup resources

- [Detailed Azure and Teams guide](docs/teams-azure-setup.md): prerequisites, hosting, credentials, connector setup, publishing, and troubleshooting.
- [Interactive walkthrough](docs/teams-walkthrough.html): download the HTML file from GitHub and open it in your browser. It includes copyable commands, downloadable deployment files, and a completion checklist. Progress stays in your browser.
- [Lookup container definition](deploy/standalone/Dockerfile.lookup), [Azure deployment template](deploy/standalone/lookup-service.azure.json), and [example parameters](deploy/standalone/lookup.parameters.example.json): use with the detailed guide. Keep filled parameter files outside Git.

Azure Container Apps provides the HTTPS hostname and certificate. This installation uses your Azure subscription and can incur Azure charges. The lookup service is configured for one Zenity organization and integration, and requires a separate connector service key.

## What you need

1. A Zenity API client ID and secret, organization and integration IDs, assigned API/OAuth endpoint values, and a real violation ID for verification.
2. Power Apps and Copilot Studio access in the same Microsoft tenant and Power Platform environment, with Dataverse and permission to import solutions and configure custom connectors.
3. A licensed Teams account authorized to use the agent. Your tenant's app distribution and connector policies must permit the installation.
4. For the Azure setup, deployment and image-build access in your subscription, with an administrator available for managed identity role assignments when needed.

Store Zenity credentials in your host's secret store. Keep them out of browser configuration, agent instructions, and conversation inputs. The connector service key is separate from your Zenity client secret.

## Review and privacy

The service retrieves a finding before asking Copilot for a plan. It sends selected rule details and redacted evidence. Redaction removes recognized secrets, email addresses, resource names and IDs, unknown nested fields, and URL paths and queries. Narrative text may still contain sensitive information, so review the fields sent to Copilot against your organization's data policy.

Recommendations provide general guidance about the observed condition. Validate their relevance to your environment before making changes. Microsoft conversation retention follows your tenant settings.

## Check your setup

For Teams, complete the [Teams setup checks](docs/teams-azure-setup.md#10-record-acceptance-results). For the review page, use [the installation checks](docs/customer-deployment-spec.md) to confirm sign-in, access restrictions, Zenity lookup, finding identity, safe failures, and read-only behavior. [How it works](HOW_IT_WORKS.md) explains the request and authentication flow.

## Runtime updates

CI follows the latest Node.js LTS and stable Python 3 releases. Customer images use `node:lts-slim`; the standalone lookup image uses `python:3-slim`. GitHub Actions follow maintained major-version tags with weekly Dependabot checks. Rebuild deployed images to adopt runtime updates, then repeat the setup checks.

## Beta release

Before inviting reviewers, test the Azure API-key deployment and a live finding conversation in Teams in your environment.

[Download v0.1.0-beta.1](https://github.com/johnt-zenity/zenity-remediation-assistant/releases/tag/v0.1.0-beta.1). The application ZIP contains the customer application source, setup guides and Copilot solution. The separate Copilot solution ZIP installs the standalone chat agent. Configure your own Microsoft and Zenity connections, then complete the installation checks before inviting reviewers. The guides and deployment files on `main` include updates made after this beta ZIP was published; use the current guide when setting up Azure and Teams.

## Support

For setup help, support, or debugging, contact [John Travise](mailto:johnt@zenity.io). Include the release version, error message and steps to reproduce. Include a correlation ID if one is shown. Diagnostic information stays in your deployment unless you choose to share it.
