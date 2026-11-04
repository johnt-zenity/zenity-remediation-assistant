# Prepare your installation

Ask your Zenity contact for the installation files. If you received the application source, create a bundle for your Microsoft tenant and Zenity integration with the command below. This command records your Zenity region endpoints and configuration IDs. It does not read or include your Zenity credentials.

```sh
python3 deploy/package_customer.py \
  --customer YOUR_DEPLOYMENT_NAME \
  --organization YOUR_ZENITY_ORGANIZATION_ID \
  --integration YOUR_ZENITY_INTEGRATION_ID \
  --zenity-api-base YOUR_ZENITY_API_BASE_URL \
  --zenity-token-url YOUR_ZENITY_OAUTH_TOKEN_URL \
  --zenity-audience YOUR_ZENITY_API_AUDIENCE \
  --zenity-issuer YOUR_ZENITY_TOKEN_ISSUER \
  --zenity-region YOUR_ZENITY_REGION_LABEL \
  --host YOUR_REVIEW_HOST \
  --tenant-id YOUR_MICROSOFT_TENANT_ID \
  --spa-client-id YOUR_SPA_CLIENT_ID \
  --api-client-id YOUR_REVIEW_API_CLIENT_ID \
  --environment-id YOUR_COPILOT_ENVIRONMENT_ID \
  --agent-schema YOUR_PUBLISHED_AGENT_SCHEMA \
  --output ./installation-bundle
```

Use lowercase letters, numbers, and hyphens for `YOUR_DEPLOYMENT_NAME`. Use the ID values and region-specific API and OAuth settings supplied by your Zenity administrator. Set `YOUR_REVIEW_HOST` to the HTTPS hostname reviewers will use. Keep the generated bundle in your organization's approved deployment storage.

## Install and test

Follow [Install the Zenity remediation assistant](customer/README.md) to add your Zenity credentials to your host's secret store, build the image, host the service over HTTPS, and verify reviewer access before use.

For a standalone Copilot chat experience, ask your Zenity contact for the Copilot solution ZIP and follow [Set up the standalone Copilot agent](../docs/copilot-customer-portability-spec.md). It uses a separate connector service key. The review page does not need that connector.

The service reads `api_base`, `token_url`, `audience` and `issuer` from each installation's connection configuration. The `region` value is a label. Zenity's production reference lists the same API and Auth0 values for prod EU and US tenants; enter those values for either region. Other Zenity environments can use their assigned endpoint values without code changes. Each installation uses one Zenity organization and integration. The assistant provides read-only findings and proposed remediation guidance.
