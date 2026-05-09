# Security Rules

## Secrets

Never commit secrets.

Do not commit:

- API keys.
- Access tokens.
- Session cookies.
- Passwords.
- Private keys.
- Production `.env` files.
- Instagram credentials.
- Sudo passwords.

Use environment variables for configuration. Keep `.env.example` limited to placeholders.

If a temporary sudo password is provided during an operational task, use it only for that task. Do not persist it anywhere.

## Public Exposure

Be careful exposing a public IP. Direct IP access is acceptable for the MVP, but the service should still be locked down reasonably.

Before deployment, consider:

- Firewall rules.
- nginx binding and proxy behavior.
- Whether the app should bind only to `127.0.0.1` behind nginx.
- Basic rate limiting.
- Request size limits.
- Logging that avoids sensitive data.
- Whether direct port exposure is still needed after nginx or Cloudflare is configured.

## Instagram And Platform Risk

Do not build:

- Login bypass.
- CAPTCHA bypass.
- Rate-limit evasion.
- Aggressive scraping.
- Credential sharing.
- Automated behavior intended to avoid platform controls.

The first MVP should support manual post URL plus pasted caption ingestion. Later ingestion must be evaluated for platform compliance, reliability, and operational risk.

## Data Safety

Preserve original source links and pasted text. Make extracted recipe data editable or replaceable so bad extraction does not permanently damage the source record.
