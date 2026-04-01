# arXiv Talking Avatar Research Digest

Daily newsletter covering talking head, talking avatar, and audio-visual speech research from arXiv. Fetches papers, validates images, writes HTML sections via Claude, and sends via Gmail.

## Setup

1. **Gmail app password**: Google Account → Security → 2-Step Verification → App Passwords. Generate one for "Mail".

2. **Environment variables** — add to your `~/.zshrc`:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   export GMAIL_USER=your@gmail.com
   export GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   export GMAIL_TO=jimmybradford55@yahoo.com  # optional, this is the default
   ```

3. **Run**:
   ```bash
   cd ~/claudecode/skills/arxiv-digest
   python3 run.py
   ```

## Scripts

| File | What it does |
|------|-------------|
| `config.py` | Search terms, date windows, email + API settings |
| `fetch.py` | Hits arXiv API for 3 time windows, parses XML, validates real image URLs |
| `write.py` | Calls Claude API (Sonnet) to write Today / Week / Month HTML sections |
| `send.py` | Assembles full HTML email and sends via Gmail SMTP |
| `run.py` | Orchestrates all three — this is what you run |

## Testing individual steps

```bash
# Test fetch only (prints paper titles + image URLs)
python3 fetch.py

# Test write only (saves HTML to /tmp/arxiv_*.html)
python3 write.py

# Test send only (saves HTML preview to /tmp/arxiv_test_email.html, sends if env vars set)
python3 send.py
```
