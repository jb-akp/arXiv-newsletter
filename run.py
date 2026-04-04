#!/usr/bin/env python3
"""
arXiv Talking Avatar Research Digest
Fetches papers, writes newsletter sections via Claude, sends via Gmail.

Usage:
    python3 run.py

Required env vars:
    ANTHROPIC_API_KEY
    GMAIL_USER         (your Gmail address)
    GMAIL_APP_PASSWORD (Gmail app password)
    GMAIL_TO           (recipient, defaults to jimmybradford55@yahoo.com)
"""
import sys
import os

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch import fetch_papers
from write import write_sections
from send import assemble_and_send


def main():
    print("=== arXiv Digest ===")

    print("\n[1/3] Fetching papers...")
    papers = fetch_papers()

    total = sum(len(papers[s]) for s in ['today', 'week', 'month'])
    counts = {s: len(papers[s]) for s in ['today', 'week', 'month']}
    print(f"  Total: {total} papers (today: {counts['today']}, week: {counts['week']}, month: {counts['month']})")

    if total == 0:
        print("No new papers. Skipping digest.")
        return

    active = [s for s, c in counts.items() if c > 0]
    print(f"\n[2/3] Writing sections: {', '.join(active)}...")
    sections = write_sections(papers)
    sections['paper_count'] = total

    print("\n[3/3] Sending email...")
    assemble_and_send(sections)

    print("\nDone.")


if __name__ == '__main__':
    main()
