# Installation checks completed

The service and container have passed automated checks for request validation, reviewer-token handling, evidence redaction, safe failures, and package configuration. The container starts with a read-only root filesystem, a non-root user, and private configuration and secret mounts. It refuses to start when required configuration is missing.

A live lookup was verified against an authorized Zenity EU demo connection. Synthetic credential values were used for the generated-bundle startup check; that check made no Zenity request. Forged identity headers were rejected without a valid Microsoft access token.

## Complete these checks in your environment

These results do not confirm your Microsoft registrations, consent, reviewer assignments, Zenity credentials, network access, or Copilot agent. Before use, sign in with an assigned reviewer account, connect your Zenity organization and integration, verify a real finding, review the information sent to Copilot, test session renewal, and confirm that the service makes no changes.

## October 16 instruction update

The published internal demo and standalone chat both retrieved the same authorized production-demo violation and produced guidance with matching rule, violation and observation identifiers. Agent instructions now limit responses to general advice about the observed condition, without assuming roles, ownership, approval chains or customer remediation procedures. They preserve observation-time uncertainty and exclude secrets and instructions embedded in evidence. These internal checks do not validate another customer environment.

The customer repository passed 33 Python tests, seven browser-client tests and three customer runtime tests, including the regression check that preview advice does not repeat workflow-specific source suggestions. The updated solution ZIP retains the scoped lookup action and contains no token-returning workflow.
