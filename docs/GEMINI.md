# Gemini setup (`gw ask` and `gw diff`)

`gw ask` and `gw diff` are **optional**. All other Gitwise commands work offline with no API key.

## 1. Get a free key

Create a key at [Google AI Studio](https://aistudio.google.com/apikey) (no credit card on free tier).

## 2. Store the key (pick one)

### A. Project `.env` (easiest after fork)

```bash
copy .env.example .env        # Windows
cp .env.example .env          # Linux / macOS
```

Edit `.env`:

```
GEMINI_API_KEY=your-key-here
```

`.env` is gitignored — it will not be committed.

### B. Environment variable

```powershell
# Windows PowerShell (current session)
$env:GEMINI_API_KEY = "your-key-here"
```

```bash
# Linux / macOS
export GEMINI_API_KEY="your-key-here"
```

### C. Key file in your home directory

One line, no quotes:

- Windows: `%USERPROFILE%\.gitwise\gemini_api_key`
- Linux/macOS: `~/.gitwise/gemini_api_key`

## 3. Try it

```bash
gw ask "what branch am I on?"
gw diff HEAD~2
gw diff abc1234 HEAD -n
```

## How it stays safe

- Model: `gemini-2.5-flash-lite` (free tier, minimal tokens)
- Context is compact and redacted — see [SECURITY.md](SECURITY.md)
- `gw ask`: LLM commands validated against Gitwise planner before run
- `gw diff`: git stats + **unified diff code** (+/- lines, up to ~18k chars, 20 files). `.env`, keys, and credentials stripped.
- API key is sent in an HTTP header, not the URL

## Troubleshooting

| Message | Fix |
|---------|-----|
| API key not found | Create `.env` from `.env.example` or set `GEMINI_API_KEY` |
| Invalid API key | Regenerate at AI Studio |
| Rate limit (429) | Free tier quota — wait and retry |
| Unverified plan (`gw ask`) | Use `gw do "…"` or rephrase your question |
| No differences (`gw diff`) | Check refs with `git log --oneline` |
