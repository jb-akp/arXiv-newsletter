import re
import anthropic
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, TEMPERATURE
from fetch import format_paper_text

TODAY_PROMPT = """You write the TODAY'S PAPERS section of the Talking Avatar Research Daily Digest newsletter.

AUDIENCE: Engineers building a realtime AI avatar API (Akapulu). They work hands-on with LiveKit, audio-driven face animation, lip sync, and streaming avatar pipelines daily. They don't need jargon explained — they need to know what's new, what the technical contribution is, and whether it's worth reading the full paper.

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
- Bullet 1: The core technical contribution in one sentence. Name the method/architecture.
- Bullet 2: Key technical detail — what loss, representation, or architecture choice makes this work?
- Bullet 3: Practical relevance — latency numbers, inference cost, real-time capability, or quality benchmarks if available.

In Depth:
[2-3 paragraphs.]
- Paragraph 1: What specific limitation of prior work does this address? Name the baselines.
- Paragraph 2: Architecture and method — name specific components, representations (3DGS, NeRF, FLAME, tri-plane, etc.), losses, and training details.
- Paragraph 3: Results that matter — inference speed, FID/FVD/sync scores, real-time viability, failure cases if mentioned.

The Bottom Line: [One sentence — is this paper worth reading in full, and why or why not?]

PDF: [link] | Project: [link if available]
[Visual separator between papers]

IMAGE RULES:
- Include ALL provided URLs as <img> tags after authors, before TLDR.
- Style: <img src=URL alt="figure" style="max-width:100%;max-height:400px;width:auto;height:auto;border-radius:8px;margin:12px 0;" />
- If empty, skip images. NEVER fabricate URLs.

WRITING RULES:
- NEVER use "for teams building X" or similar.
- Be concrete. Name the methods, architectures, and benchmarks.
- Don't explain basics like what diffusion models or GANs are. The reader knows.
- No emojis."""

WEEK_PROMPT = """You write the THIS WEEK IN REVIEW section of the Talking Avatar Research Daily Digest newsletter.

AUDIENCE: Engineers building a realtime AI avatar API. They work with LiveKit, audio-driven face animation, lip sync, and streaming pipelines. Write for practitioners, not a general audience.

STYLE RULES:
- Inline CSS only
- Font: Arial, sans-serif; color #372d09; size 16px; line-height 1.5
- Links: #2294d2
- Section divider: 3px solid #372d09
- Callout box: background #faf6ee, border-left 4px solid #c9a227, padding 16px, margin 16px 0

STRUCTURE:
1. Heading: This Week in Review as bold h2
2. Overview: 2-3 TLDR bullets in callout box. Lead with technical contributions, not explanations of why avatars matter.
3. Deep Dive: 2-3 short paragraphs. Weave each paper into prose as clickable links. Every paper MUST appear linked. Focus on what's technically novel and whether results are practically useful (latency, quality, real-time viability).

IMAGE RULES:
- Include at most 1-2 teaser images in the deep dive.
- Style: <img src=URL alt="figure" style="max-width:100%;max-height:400px;width:auto;height:auto;border-radius:8px;margin:12px 0;" />
- If Teaser Images is empty for a paper, skip it. NEVER fabricate URLs.

RULES:
- Never use "for teams building X".
- Be concrete. Name methods, architectures, benchmarks.
- Don't explain fundamentals. The reader is deep in this space.
- No emojis."""

MONTH_PROMPT = """You write the THIS MONTH IN REVIEW section of the Talking Avatar Research Daily Digest newsletter.

AUDIENCE: Engineers building a realtime AI avatar API. They work with LiveKit, audio-driven face animation, lip sync, and streaming pipelines. Write for practitioners, not a general audience.

STYLE RULES:
- Inline CSS only
- Font: Arial, sans-serif; color #372d09; size 16px; line-height 1.5
- Links: #2294d2
- Section divider: 3px solid #372d09
- Callout box: background #faf6ee, border-left 4px solid #c9a227, padding 16px, margin 16px 0

STRUCTURE:
1. Heading: This Month in Review as bold h2
2. Overview: 2-3 TLDR bullets in callout box. Lead with technical trends, not general context.
3. Deep Dive: EXACTLY 2 paragraphs, no more. Pick the 4-5 most impactful papers — prioritize real-time methods, novel representations, and anything with practical latency/quality results. Weave them into prose as clickable links.
4. Also Worth a Look: Compact bullet list of remaining papers (title as clickable arXiv link + one sentence on the technical contribution).

IMAGE RULES:
- Include at most 2-3 teaser images total in the deep dive — only for the papers you highlight most.
- Style: <img src=URL alt="figure" style="max-width:100%;max-height:400px;width:auto;height:auto;border-radius:8px;margin:12px 0;" />
- If Teaser Images is empty for a paper, skip it. NEVER fabricate URLs.

RULES:
- Never use "for teams building X".
- Be concrete. Name methods, architectures, benchmarks.
- Don't explain fundamentals. The reader is deep in this space.
- Keep it tight. Quick scan, not a literature review.
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
        if not papers[section]:
            print(f"  Skipping {section} section (no papers)")
            sections[f'{section}_html'] = ''
            continue
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
