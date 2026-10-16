# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python remediation preview and Copilot Studio integration. Core lookup and evidence handling live in `engine.py`, `zenity_reader.py`, `evidence.py`, and `profiles.py`; `server.py` serves the local browser preview, while `connector_server.py` and `connector_azure.py` expose connector adapters. Browser assets are in `static/`. Copilot action setup and the browser client live in `copilot/`; customer packaging and deployment guides are in `deploy/`. Specifications, security invariants, and test vectors are in `docs/`. Python tests are in `tests/`.

## Build, Test, and Development Commands

- `python3 server.py` starts the synthetic local preview at `http://127.0.0.1:8765`.
- `python3 -m unittest discover -s tests -v` runs the Python test suite.
- `python3 evaluate.py` runs synthetic evaluation vectors and latency samples.
- `npm ci && npm test` from `copilot/web/` installs locked dependencies and runs browser-client tests.
- `npm run build` from `copilot/web/` bundles the client into `deploy/corpo-valley/static-site/public/app.js`.

## Coding Style & Naming Conventions

Use four spaces for Python indentation and follow existing module patterns. Use descriptive `snake_case` for Python functions and files; use the existing JavaScript ES module style and `camelCase` for JavaScript functions. Keep customer scope fixed, credentials outside Git, and source evidence bounded and redacted. Update the relevant specification and published vectors when changing action behavior or security invariants. No repository-wide formatter or linter is configured; keep changes consistent with nearby code.

## Testing Guidelines

Add or update focused tests under `tests/` for Python behavior and `copilot/web/client.test.js` for browser client behavior. Keep synthetic fixtures free of real credentials or customer data. Run the relevant test command above after changes; run both suites for cross-layer changes. Evaluation results describe synthetic vectors and do not substitute for Copilot Studio conversation checks.

## Commit & Pull Request Guidelines

Recent commits use short imperative subjects, for example `Classify empty Copilot response safely`. Follow that style and keep each commit focused. Pull requests should explain behavior and security impact, list verification commands and results, link related work when available, and include screenshots for visible UI changes. Document deployment or configuration changes in the corresponding `README.md` or guide.

## Security & Configuration

Never commit credentials, live connection files, or customer identity data. Keep secrets in a local file outside the repository or a deployment secret store. Preserve fixed organization/integration scope, reviewer authentication boundaries, and the no-mutation behavior described in the specs.
