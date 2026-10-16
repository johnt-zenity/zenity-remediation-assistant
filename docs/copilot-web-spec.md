# Violation context passed to Copilot

The backend retrieves an AISPM violation from the configured Zenity integration. It passes bounded, redacted context directly to the published customer agent and displays the same violation alongside its proposed plan.

## Named invariants

1. **ServerSource**: the browser submits only a violation ID; the backend retrieves evidence.
2. **SameViolation**: agent input and displayed context use the same record.
3. **FixedScope**: organization, integration, credentials and agent are deployment settings.
4. **ReviewerAccess**: validate the API token before retrieval; use the separate reviewer token for Copilot.
5. **ReadOnly**: produce guidance without changing resources or violation status.

## Milestones and test vectors

1. Configure and publish the customer agent using the supplied instructions.
2. Deploy the application with customer credentials and assigned Microsoft reviewers.
3. Run the following live acceptance checks and record agent version and source revision.

| ID | Test | Expected |
| --- | --- | --- |
| CT01 | Authorized real violation | One lookup; same context passed to agent and displayed |
| CT02 | Missing, denied or unavailable record | No agent invocation |
| CT03 | Browser supplies evidence or scope | Reject before lookup |
| CT04 | Agent failure after lookup | Preserve retrieved violation with a safe error |
| CT05 | Rule and resource-specific review | Plan addresses actual evidence and uses matching source identifiers |
| CT06 | Instruction-like source text | Treat as data; follow no embedded directives |

These require execution in your target environment. Use [customer deployment acceptance](customer-deployment-spec.md) for authorization, cold-start and platform checks.
