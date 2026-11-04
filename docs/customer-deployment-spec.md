# Check your installation

Complete these checks in your Microsoft and Zenity environments before you invite reviewers.

## Microsoft sign-in

- An assigned reviewer can sign in and open the review page.
- A person outside the reviewer group cannot access a finding.
- A token from another Microsoft tenant or application is rejected.
- An expired session prompts the reviewer to sign in again.
- Requests with forged identity headers or an unexpected website origin are rejected.

## Zenity lookup and plan

- A valid violation ID returns the matching rule and observation time.
- The rule and finding details shown to the reviewer belong to the same violation ID.
- An unknown or inaccessible ID returns a safe message. The agent does not invent finding details.
- If Copilot cannot produce a plan, the actual Zenity finding remains visible and the page shows a safe error.
- The agent uses the returned rule and evidence. Review its advice against the affected resource and your approval process.
- Asking the agent to make a change produces guidance only. The application does not change resources or violation status.

## Customer configuration

- The service uses the Zenity organization, integration, API base URL, OAuth token URL, audience and issuer you configured. Reviewers cannot choose these values in the page or conversation.
- The configured API and OAuth endpoints use HTTPS, and HTTP redirects are rejected. Confirm these values against the endpoint details Zenity assigned to your environment.
- Your Zenity `CLIENT_ID` and `CLIENT_SECRET` are mounted to the service and are absent from browser responses and Copilot context.
- The page uses HTTPS and only your approved reviewers can reach the review API.
- Your application and agent use the Microsoft tenant, registrations, environment and reviewer assignments you intended.

Record your image digest, configuration version, Microsoft environment, agent version, test date and results. Test with a real violation only after access and data handling are approved in your tenant.
