# Security and privacy

Gitwise is designed to run locally, confirm before mutating git state, and never store your credentials in the repository.

## Secrets in this repo

These files are **gitignored** and must never be committed:

| File | Purpose |
|------|---------|
| `.env` | Local API keys (copy from `.env.example`) |
| `~/.gitwise/gemini_api_key` | Optional persistent Gemini key |
| `*.pem`, `*.key`, `credentials.json` | Blocked by `.gitignore` |

**Before pushing:** run `git status` and confirm `.env` does not appear. If it does, do not commit it.

## What Gitwise stores

- **Nothing in the cloud** except optional `gw ask` calls to Google Gemini (see below).
- **No database** — all state comes from live `git` commands in the directory you choose.
- **No git credentials** — Gitwise uses whatever `git` already has (SSH agent, Credential Manager, PAT).

## What leaves your machine

| Command | Network | Data sent |
|---------|---------|-----------|
| `gw whereami`, `gw do`, `gw pull`, `gw save`, `gw undo` | No* | Nothing |
| `gw ask`, `gw diff` | Yes (Gemini API) | Redacted repo snapshot / diff patch |

\*Push/pull/fetch use **git**, which talks to your remote as it normally would.

### `gw ask` privacy

Before any LLM request, Gitwise:

- Redacts HTTPS URLs with embedded passwords (`https://user:pass@...`)
- Strips API-key-like strings and token assignments from context
- Omits `.env`, key files, and PEM paths from `git status` output
- Sends API keys via HTTP header (`x-goog-api-key`), not in the URL
- Never logs your API key in error messages

Gemini free tier may use prompts to improve models (see [Google AI terms](https://ai.google.dev/gemini-api/terms)). Do not use `gw ask` on repos with legally restricted data unless your policy allows it.

## Command safety

- Only `git …` commands run; shell operators (`&&`, `;`, `` ` ``) are rejected.
- Blocked: `git config`, credential helpers, force push (outside recipes), arbitrary scripts.
- `gw ask` never runs raw LLM commands — only Gitwise-validated plans after comparison with the built-in planner.
- Destructive workflows require confirmation; elevated ones require typing `yes`.

## Reporting issues

If you find a path where secrets could leak (logs, context, error output), open an issue without pasting real keys.
