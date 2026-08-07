# Security Policy

## Supported versions

Security fixes are applied to the latest maintained release/branch unless a release note states otherwise.

## Reporting a vulnerability

Do not publish exploitable details, credentials, tokens, personal data or proof-of-concept payloads in a public issue.

Use GitHub private vulnerability reporting when enabled for this repository. If that option is unavailable, contact the maintainer through the public profile and request a private reporting channel before sharing sensitive details.

Include, when possible:

- affected version/commit;
- affected component or endpoint;
- impact and preconditions;
- minimal reproduction steps;
- suggested mitigation;
- whether credentials or personal data may have been exposed.

## Scope

The project CI includes automated tests, coverage, static security analysis, dependency auditing and SBOM generation. A green CI run reduces risk but is not a certification and does not guarantee absence of vulnerabilities.

Agronomic, climate and external-data integrations must also be validated against their authoritative sources and applicable operational requirements.
