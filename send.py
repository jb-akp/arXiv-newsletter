import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import GMAIL_USER, GMAIL_APP_PASSWORD, GMAIL_TO, GMAIL_SENDER_NAME


def _count_sections(sections: dict) -> str:
    """Build a subtitle like '11 papers · 2 sections'."""
    labels = []
    for key, label in [('today_html', 'today'), ('week_html', 'this week'), ('month_html', 'this month')]:
        if sections.get(key):
            labels.append(label)
    count = sections.get('paper_count', 0)
    if count and labels:
        return f"{count} papers &middot; {', '.join(labels)}"
    return ''


def assemble_html(sections: dict) -> str:
    today_html = sections.get('today_html', '')
    week_html = sections.get('week_html', '')
    month_html = sections.get('month_html', '')

    # Build content blocks, skipping empty sections
    content_blocks = []
    if today_html:
        content_blocks.append(today_html)
    if week_html:
        content_blocks.append(week_html)
    if month_html:
        content_blocks.append(month_html)

    if not content_blocks:
        content_blocks.append('<p style="color:#372d09;font-size:16px;">No new talking avatar papers found. Check back tomorrow.</p>')

    body_html = '\n\n'.join(content_blocks)

    date_str = datetime.now().strftime('%B %-d, %Y')
    year = datetime.now().year
    subtitle = _count_sections(sections)

    # Preheader: the snippet Gmail/Outlook shows in inbox preview
    preheader_text = subtitle if subtitle else f"Talking avatar research digest for {date_str}"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /></head>
<body style="margin:0;padding:0;background-color:#f5f0e8;font-family:Arial,sans-serif;">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preheader_text}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f0e8;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="700" cellpadding="0" cellspacing="0" style="max-width:700px;background-color:#ffffff;border-radius:12px;overflow:hidden;">
<tr><td style="padding:32px 32px 0 32px;">

<table width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="font-family:Arial Black,Arial,sans-serif;font-size:28px;font-weight:900;font-style:italic;color:#372d09;line-height:1.2;">Talking Avatar Research<br/>Daily Digest</td>
<td style="text-align:right;vertical-align:top;">
<div style="font-size:14px;color:#8a7e5a;">{date_str}</div>
<div style="font-size:18px;font-weight:bold;color:#372d09;margin-top:4px;">Akapulu</div>
</td>
</tr></table>

{"<div style='font-size:14px;color:#8a7e5a;margin-top:8px;'>" + subtitle + "</div>" if subtitle else ""}

{body_html}

<div style="border-top:3px solid #372d09;margin-top:32px;padding-top:24px;text-align:center;color:#8a7e5a;font-size:13px;padding-bottom:32px;">
<div style="font-size:18px;font-weight:bold;color:#372d09;margin-bottom:8px;">Akapulu</div>
<div>Talking Avatar Research Daily Digest &mdash; powered by Akapulu</div>
<div style="margin-top:12px;"><a href="mailto:{GMAIL_USER}?subject=Unsubscribe%20arXiv%20Digest" style="color:#2294d2;text-decoration:underline;">Unsubscribe</a></div>
<div style="margin-top:8px;">&copy; {year} Akapulu. All rights reserved.</div>
</div>

</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def assemble_and_send(sections: dict):
    html = assemble_html(sections)
    date_str = datetime.now().strftime('%B %-d, %Y')
    subject = f"arXiv Digest: Talking Avatar Research \u2014 {date_str}"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'{GMAIL_SENDER_NAME} <{GMAIL_USER}>'
    msg['To'] = GMAIL_TO
    msg.attach(MIMEText(html, 'html'))

    print(f"  Sending to {GMAIL_TO}...")
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_TO, msg.as_string())
    print("  Sent.")


if __name__ == '__main__':
    # Test with placeholder sections
    test_sections = {
        'today_html': '<p>No new papers today.</p>',
        'week_html': '<p style="color:#372d09">Test week section.</p>',
        'month_html': '<p style="color:#372d09">Test month section.</p>',
    }
    html = assemble_html(test_sections)
    with open('/tmp/arxiv_test_email.html', 'w') as f:
        f.write(html)
    print("Saved preview to /tmp/arxiv_test_email.html")

    if GMAIL_USER and GMAIL_APP_PASSWORD:
        assemble_and_send(test_sections)
    else:
        print("Set GMAIL_USER and GMAIL_APP_PASSWORD env vars to test sending.")
