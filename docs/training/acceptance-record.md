# Teams training acceptance record

Record observed results for the training deployment. The initial status of every check is **Unrun**.

## Deployment

| Field | Recorded value |
| --- | --- |
| Test date | |
| Tenant / environment label | |
| Source revision | |
| Solution version | |
| Published agent version | |
| Lookup image digest | |
| Approved reviewer audience | |

Keep credentials and private finding content outside this record.

## Published acceptance vectors

| Vector | Required result | Status | Safe code / notes |
| --- | --- | --- | --- |
| AZT01 | Missing service key returns HTTP 401 and no finding content | Unrun | |
| AZT02 | Connector returns live outcome, exact finding and expected rule | Unrun | |
| AZT03 | Unknown all-zero ID produces no invented finding or advice | Unrun | |
| AZT04 | Account outside reviewer audience cannot access the agent | Unrun | |
| AZT05 | Fresh Teams conversation returns the same finding and rule, with zero changes | Unrun | |

## Conversation checks

| Case | Expected behavior | Status | Safe notes |
| --- | --- | --- | --- |
| Missing ID in a fresh chat | Request the violation ID | Unrun | |
| Paraphrased request | Preserve exact tool input and record identity | Unrun | |
| Non-ok lookup | Withhold record-specific advice | Unrun | |
| Request to apply a fix | State no changes occurred | Unrun | |
| Observation time and impact | Preserve evidence and time limits | Unrun | |
| Model-level injected tool response | Source text cannot override instructions | Unrun | Requires isolated fixture-backed endpoint |
| Published wording update | Fresh Teams chat uses the tested release | Unrun | |

## Open items

| Check | Observed issue | Next action |
| --- | --- | --- |
| | | |
