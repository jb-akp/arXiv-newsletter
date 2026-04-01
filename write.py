import re
import anthropic
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, TEMPERATURE
from fetch import format_paper_text

TODAY_PROMPT = """You write the TODAY'S PAPERS section of the Talking Avatar Research Daily Digest newsletter.

Your readers range from curious beginners to experienced ML researchers. TLDRs should be accessible to anyone; in-depth sections reward those who want to go deeper.

STYLE RULES:
- Inline CSS only (Gmail strips <style> blocks)
- Body font: Arial, sans-serif; color #372d09; size 16px; line-height 1.5
- Links: #2294d2
- Section divider before heading: 3px solid #372d09
- TLDR callout box: background #faf6ee, border-left 4px solid #c9a227, padding 16px, margin 16px 0
- The Bottom Line text: bold italic, color #5a4e1a

FOR EACH PAPER (FULL FORMAT):

[Paper title as bold h2, wrapped in <a href=arXiv link> tag]
[Authors on a separate line, smaller text -- Date]
[Teaser images -- include ALL URLs from Teaser Images field as <img> tags]

TLDR (styled as a callout box):
- Bullet 1: What this paper does, in one plain-English sentence. No jargon.
- Bullet 2: The key insight or technique, explained simply.
- Bullet 3: Why someone might care about this.

In Depth:
[2-3 paragraphs.]
- Paragraph 1: What problem and why is it hard?
- Paragraph 2: How does the approach work? Name methods.
- Paragraph 3: What sets this apart?

The Bottom Line: [One bold, memorable sentence.]

PDF: [link] | Project: [link if available]
[Visual separator between papers]

IMAGE RULES:
- Include ALL provided URLs as <img> tags after authors, before TLDR.
- Style: <img src=URL alt="figure" style="max-width:100%;max-height:400px;width:auto;height:auto;border-radius:8px;margin:12px 0;" />
- If empty, skip images. NEVER fabricate URLs.

WRITING RULES:
- NEVER use "for teams building X" or similar.
- Be concrete. Name the methods.
- If no papers: <p>No new papers today.</p>
- No emojis."""

WEEK_PROMPT = """You write the THIS WEEK IN REVIEW section of the Talking Avatar Research Daily Digest newsletter.

STYLE RULES:
- Inline CSS only
- Font: Arial, sans-serif; color #372d09; size 16px; line-height 1.5
- Links: #2294d2
- Section divider: 3px solid #372d09
- Callout box: background #faf6ee, border-left 4px solid #c9a227, padding 16px, margin 16px 0

STRUCTURE:
1. Heading: This Week in Review as bold h2
2. Overview: 2-3 TLDR bullets in callout box, beginner-friendly.
3. Deep Dive: 2-3 paragraphs. CRITICAL: Do NOT list papers individually. Weave each paper into prose as clickable links. Every paper MUST appear linked.

IMAGE RULES:
- Each paper in the input data has a Teaser Images field with validated URLs (or empty if none exist).
- In the Deep Dive, include ONE teaser image per paper, placed near where the paper is first discussed in the prose.
- Style: <img src=URL alt="figure" style="max-width:100%;max-height:400px;width:auto;height:auto;border-radius:8px;margin:12px 0;" />
- If Teaser Images is empty for a paper, skip it. NEVER fabricate URLs.

RULES:
- Never use "for teams building X".
- Be concrete. Name methods.
- If no papers: <p>No new papers earlier this week.</p>
- No emojis."""

MONTH_PROMPT = """You write the THIS MONTH IN REVIEW section of the Talking Avatar Research Daily Digest newsletter.

STYLE RULES:
- Inline CSS only
- Font: Arial, sans-serif; color #372d09; size 16px; line-height 1.5
- Links: #2294d2
- Section divider: 3px solid #372d09
- Callout box: background #faf6ee, border-left 4px solid #c9a227, padding 16px, margin 16px 0

STRUCTURE:
1. Heading: This Month in Review as bold h2
2. Overview: 2-3 TLDR bullets in callout box.
3. Deep Dive: 2-3 paragraphs. CRITICAL: Do NOT list papers individually. Weave each paper into prose as clickable links. Every paper MUST appear linked.

IMAGE RULES:
- Each paper in the input data has a Teaser Images field with validated URLs (or empty if none exist).
- In the Deep Dive, include ONE teaser image per paper, placed near where the paper is first discussed in the prose.
- Style: <img src=URL alt="figure" style="max-width:100%;max-height:400px;width:auto;height:auto;border-radius:8px;margin:12px 0;" />
- If Teaser Images is empty for a paper, skip it. NEVER fabricate URLs.

RULES:
- Never use "for teams building X".
- Be concrete. Name methods.
- If no papers: <p>No new papers earlier this month.</p>
- No emojis."""


def _dedup_sections(papers: dict) -> dict:
    """Remove papers that appear in earlier sections (today > week > month)."""
    today_ids = {p['versioned_id'] for p in papers['today'] if p['versioned_id']}
    papers['week'] = [p for p in papers['week'] if p['versioned_id'] not in today_ids]
    seen = today_ids | {p['versioned_id'] for p in papers['week'] if p['versioned_id']}
    papers['month'] = [p for p in papers['month'] if p['versioned_id'] not in seen]
    return papers


def _call_claude(client: anthropic.Anthropic, system: str, user_content: str) -> str:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=system,
        messages=[{'role': 'user', 'content': user_content}],
    )
    text = msg.content[0].text.strip()
    # Strip code fences if model wraps in ```html
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    return text


def write_sections(papers: dict) -> dict:
    papers = _dedup_sections(papers)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def fmt(section_papers):
        if not section_papers:
            return 'No papers.'
        return '\n\n---\n\n'.join(format_paper_text(p) for p in section_papers)

    sections = {}
    for section, prompt in [('today', TODAY_PROMPT), ('week', WEEK_PROMPT), ('month', MONTH_PROMPT)]:
        print(f"  Writing {section} section ({len(papers[section])} papers)...")
        sections[f'{section}_html'] = _call_claude(client, prompt, fmt(papers[section]))

    return sections


if __name__ == '__main__':
    import json, sys
    # Reads papers JSON from stdin or runs fetch inline
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            papers = json.load(f)
    else:
        from fetch import fetch_papers
        papers = fetch_papers()

    sections = write_sections(papers)
    for key, html in sections.items():
        out = f'/tmp/arxiv_{key}.html'
        with open(out, 'w') as f:
            f.write(html)
        print(f"  Saved {out}")
