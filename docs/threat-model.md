# Threat model

| Threat | Control | Residual risk |
|---|---|---|
| Prompt injection in Issue/README/code | Treat all content as data; no instruction execution; UI escapes HTML | A human may still follow a malicious link |
| Path traversal / symlink escape | Resolve under capsule root; reject symlinks and absolute arguments | Filesystem race by a local attacker is out of scope |
| Test command injection | Never import upstream command strings; fixed `subprocess` argv; no shell | A project-authored local capsule is executable code and must be reviewed |
| Malicious archives | v0.1 does not extract archives | Future extractor needs size/path/link checks |
| Secret leakage | No environment dump; bounded sanitized errors; read-only Action permissions | User-provided diff can itself contain a secret and should not be published |
| Resource exhaustion | API response and record limits, subprocess timeout, no full clone | AST parsing of a single pathological local file is not yet separately timed |
| GitHub rate limit | Explicit message, token optional, deterministic offline fixtures | Fresh mining waits for quota |
| Untrusted repository scripts | Never run automatically; remote replay must be manually configured in least-privilege CI | Full external behavior reproduction is not automatic in v0.1 |

