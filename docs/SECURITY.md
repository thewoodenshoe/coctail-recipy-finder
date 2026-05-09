# Security

## MVP Threat Model

The MVP is likely a single-owner web app exposed by direct IP or used locally. Main risks:

- Public IP exposure.
- Accidental secret leakage.
- Overly permissive server configuration.
- Abusive or fragile Instagram ingestion behavior.
- Bad inputs causing crashes or data corruption.
- Search or detail pages exposing data unexpectedly if the app becomes public.

## Secrets Handling

Never commit secrets.

Use environment variables for:

- App environment.
- Database URL.
- Future API keys.
- Future authentication secrets.

Keep `.env.example` safe and placeholder-only.

## Public IP Risks

If deployed on a public IP:

- For the temporary direct-IP MVP, bind the app to `0.0.0.0:8000` only when intentionally testing public access.
- Once nginx is introduced, bind the app to localhost behind nginx.
- Use a firewall.
- Avoid exposing debug mode.
- Avoid exposing database files.
- Consider basic auth or IP allowlisting if the app is not meant for public use.

## Basic Hardening

Recommended MVP hardening:

- Request size limits for pasted text.
- Basic rate limiting at nginx if publicly exposed.
- Safe error pages without stack traces.
- URL validation for Instagram links.
- Escape user-provided text in templates.
- Log operational errors without logging secrets.
- Keep direct port exposure limited to the MVP test period.

## Scraping And Platform Risk

Instagram scraping is a platform and reliability risk.

Do not build:

- Login bypass.
- CAPTCHA bypass.
- Rate-limit evasion.
- Aggressive scraping.
- Video downloading.

Manual caption ingestion is the correct first step unless a later decision explicitly changes the ingestion model.
