# Customer host sizing

The complete customer application template uses Azure Container Apps Consumption with 0.5 vCPU, 1 GiB memory, zero minimum replicas and one maximum replica. Compose applies a 0.5 CPU and 1 GiB limit. The container includes the browser page, review backend and private reader, with no database or persistent review storage.

## Named invariants

1. **ReviewerAuthorization**: cryptographically validate the customer API token before lookup.
2. **PrivateReader**: keep Zenity credentials and lookup server-side within the application container.
3. **FixedScope**: configure one Zenity organization and integration at deployment.
4. **BoundedCapacity**: allow four concurrent reviews per process; reject additional requests with HTTP 429.
5. **ColdStartAcceptance**: test the first real review after scale-to-zero against the hosting timeout.

## Milestones and vectors

Follow [the runtime guide](../deploy/customer/README.md) to configure and deploy. Run CR01-10 from [the runtime specification](customer-runtime-spec.md), then CD01-12 from [the deployment contract](customer-deployment-spec.md). Record image digest, source revision, live authorization and cold-start latency. The full Azure template has not yet passed live target-environment provisioning.
