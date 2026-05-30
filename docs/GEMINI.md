# Gemini API setup (gw ask)

Gitwise uses Google's Gemini API for `gw ask`. The integration is minimal:

- **Model:** `gemini-2.5-flash-lite` (free tier, low cost)
- **No SDK dependency** — plain HTTPS via Python stdlib
- **Small context** — recent commits, branch list, short status (not full history)
- **Redacted** — remote URLs strip embedded credentials; no git user/email sent

## Get a free API key

1. Open [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key (no credit card required for free tier)
3. Store it using **one** of the options below

## Where to put your API key

### Option 1: Environment variable (recommended)

**Windows PowerShell (current session):**

```powershell
$env:GEMINI_API_KEY = "your-key-here"
```

**Windows PowerShell (persistent — add to your profile):**

```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-key-here", "User")
```

**Linux / macOS:**

```bash
export GEMINI_API_KEY="your-key-here"
```

### Option 2: Key file

Create a file with your key on a single line (no quotes):

```
C:\Users\YOU\.gitwise\gemini_api_key
```

On Linux/macOS: `~/.gitwise/gemini_api_key`

### Option 3: Project `.env` (gitignored)

In your repo root:

```
GEMINI_API_KEY=your-key-here
```

## Usage

```bash
gw ask "what does ahead/behind mean?"
gw ask "save all my code in the safest way"
gw ask "should I pull before pushing?" -n    # dry-run: no execution
```

When the LLM suggests git commands, Gitwise:

1. Checks commands are safe (git-only, no credentials/shell tricks)
2. Compares them to what `gw do` / `gw save` would run
3. Offers to run the **Gitwise-validated** plan — never raw unverified LLM commands

## Privacy

- Only local git metadata is sent to Gemini
- No passwords, tokens, or full `.git/config` contents
- HTTPS remote URLs are redacted if they contain `user:pass@`

## Troubleshooting

| Error | Fix |
|-------|-----|
| API key not found | Set `GEMINI_API_KEY` or create `~/.gitwise/gemini_api_key` |
| Invalid API key | Regenerate at AI Studio |
| Rate limit (429) | Free tier daily limit — wait and retry |
| Unverified plan | Rephrase as `gw do "..."` or ask for explanation only |
