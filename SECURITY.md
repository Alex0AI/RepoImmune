# Security policy

## Supported versions

The latest release receives security fixes.

## Report a vulnerability

Use GitHub's private security advisory flow. Do not include secrets, personal data, or exploit payloads in a public issue.

## Trust boundary

Repository text, Git objects, GitHub responses, archives, Issue/PR content and test commands are untrusted data. RepoImmune does not execute mined installation or test commands. Local capsules run only project-owned relative files through the current Python interpreter in isolated mode, with no shell, bounded output and a timeout. Absolute paths and symlinks are rejected. Network responses are bounded and rate-limit failures fall back to saved data.

See [docs/threat-model.md](docs/threat-model.md) for controls and residual risks.

