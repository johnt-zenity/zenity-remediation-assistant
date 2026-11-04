# Implementation

The customer runtime retrieves a scoped AISPM violation, projects source context and invokes the customer's published Copilot agent. The internal Corpo Valley deployment has completed a real EU demo review. The portable customer image and generated bundle have passed build, startup and authorization checks. Live customer authentication, Azure provisioning and advice acceptance remain target-environment checks. See [validation results](customer-runtime-validation.md).

## Customer request boundary

`deploy/customer/server.mjs` hosts the page and `POST /plan`. Before lookup, `auth.mjs` validates the review API token against the configured tenant's signing keys, issuer, audience, SPA caller, delegated scope and reviewer role. The request must have the configured HTTPS origin, same-origin Fetch Metadata and exactly a `violation_id`. A separate Power Platform token is used for Copilot invocation. Browser input cannot choose credentials, organization, integration, agent or source context.

The private reader runs as a child process with an 11-second timeout. There is no public lookup endpoint in this runtime. Startup verifies configuration and credential-file shape; it does not establish live API authorization. Four active reviews are allowed per process. Planning has a 150-second deadline; a timeout does not guarantee cancellation of a Microsoft conversation.

## Reader and source context

`zenity_reader.py` reads the configured EU organization and integration. `engine.py` validates action inputs, record identity and required fields, with a 10-second lookup budget and at most one transient retry. OAuth tokens stay in reader process memory. Checks on Zenity tokens received from the configured TLS-authenticated OAuth endpoint differ from the cryptographic validation applied to arbitrary customer API tokens.

`evidence.py` projects six rule text fields and at most five supporting evidence entries. It bounds text lengths, redacts recognized credentials, token patterns, secret assignments, email addresses and original resource name/ID references, and omits identity collections, unknown nested values and URL paths/queries. Other sensitive information may remain in narrative text. Review the projection against your data policy.

The reader preserves API resource types. It supports one configured integration and uses the tenant's configured regional API and OAuth endpoints, audience and issuer. These fixed deployment values use HTTPS, and redirects are denied. Token claims are checked against the configured organization, audience, issuer and expiry. AISPM violations and AIDR runtime findings have distinct record contracts.

## Agent and rendering

`copilot/web/client.js` starts a new conversation using fixed server-side environment and schema settings. It passes the retrieved context directly, excludes greetings and non-message activities, bounds returned text and rejects incomplete turns. The agent requires no lookup connector. A planning failure preserves the retrieved violation and returns a safe error.

Agent instructions treat source text as data, require source identifiers and prohibit resource changes or following embedded directives. These instructions require live model evaluation. The application renders retrieved text and responses through text nodes and exposes no mutation operation.

## Other execution surfaces

The internal Corpo Valley page uses its hosting gateway and a private HTTP lookup service within the same pod. The customer runtime validates Entra API tokens directly and requires no Corpo Valley identity headers.

`server.py` is a loopback developer preview with deterministic source-guidance formatting. It invokes no model and keeps up to 100 sanitized sessions in memory for 30 minutes. `connector_server.py` and the standalone lookup adapters are separate test surfaces; customer deployment uses [the full application guide](../deploy/customer/README.md).

## Verification

Python tests cover scope, identity, evidence projection, input rejection and package isolation. JavaScript tests cover customer API token validation, HTTP boundaries and simulated agent activities. The [runtime specification](customer-runtime-spec.md) and [deployment contract](customer-deployment-spec.md) define code and live acceptance vectors. Local results establish transport behavior; live customer reviews establish reviewer access and guidance quality.
