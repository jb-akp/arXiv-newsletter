import re
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TOPIC_TERMS, CAT_FILTER, DATE_WINDOWS, date_str

ARXIV_API = 'https://export.arxiv.org/api/query'
NS = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}


def _build_url(window: dict) -> str:
    d_from = date_str(window['days_back_from'])
    d_to = date_str(window['days_back_to'])
    query = f"{TOPIC_TERMS} AND {CAT_FILTER} AND submittedDate:[{d_from} TO {d_to}]"
    params = urllib.parse.urlencode({
        'search_query': query,
        'start': 0,
        'max_results': window['max'],
        'sortBy': 'submittedDate',
        'sortOrder': 'descending',
    })
    return f"{ARXIV_API}?{params}"


def _fetch_url(url: str) -> str:
    result = subprocess.run(
        ['curl', '-s', '--max-time', '60', '-A', 'arxiv-digest/1.0', url],
        capture_output=True, timeout=65
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr.decode()[:100]}")
    return result.stdout.decode('utf-8', errors='replace')


def _parse_papers(xml_text: str, brief: bool) -> list:
    papers = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return papers

    for entry in root.findall('atom:entry', NS):
        def tag(name):
            el = entry.find(f'atom:{name}', NS)
            return el.text.strip() if el is not None and el.text else ''

        arxiv_id_raw = tag('id')
        if not arxiv_id_raw or 'arxiv.org' not in arxiv_id_raw:
            continue

        arxiv_link = arxiv_id_raw.replace('http://', 'https://')
        pdf_link = arxiv_link.replace('/abs/', '/pdf/')

        id_match = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', arxiv_id_raw)
        num_id = id_match.group(1) if id_match else ''
        version = id_match.group(2) if id_match and id_match.group(2) else 'v1'
        versioned_id = num_id + version if num_id else ''

        title = re.sub(r'\s+', ' ', tag('title'))
        abstract = re.sub(r'\s+', ' ', tag('summary'))
        published = tag('published')[:10]

        author_els = entry.findall('atom:author', NS)
        names = []
        for a in author_els[:4]:
            n = a.find('atom:name', NS)
            if n is not None and n.text:
                names.append(n.text.strip())
        authors = ', '.join(names)
        if len(author_els) > 4:
            authors += ' et al.'

        project_page = 'No Project Page Found'
        comment_el = entry.find('arxiv:comment', NS)
        if comment_el is not None and comment_el.text:
            c = comment_el.text
            m = (re.search(r'(?:project\s*page|homepage|demo)\s*[:\s]*(https?://\S+)', c, re.I)
                 or re.search(r'(https?://[\w.-]+\.github\.io/\S*)', c, re.I)
                 or re.search(r'(https?://github\.com/\S+)', c, re.I))
            if m:
                project_page = m.group(1).rstrip('.,;)')

        teaser_images = ''
        if versioned_id:
            base = f'https://arxiv.org/html/{versioned_id}'
            teaser_images = f'{base}/x1.png, {base}/x2.png'

        papers.append({
            'title': title,
            'authors': authors,
            'published': published,
            'arxiv_link': arxiv_link,
            'pdf_link': pdf_link,
            'project_page': project_page,
            'abstract': abstract[:500] + '...' if brief and len(abstract) > 500 else abstract,
            'teaser_images': teaser_images,
            'versioned_id': versioned_id,
        })

    return papers


def _extract_images_for_paper(pid: str) -> tuple[str, str]:
    try:
        html = _fetch_url(f'https://arxiv.org/html/{pid}')
        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.I)
        urls = []
        for src in imgs:
            if len(urls) >= 2:
                break
            filename = src.split('/')[-1].split('?')[0]
            stem = re.sub(r'\.(png|jpg|jpeg)$', '', filename, flags=re.I)
            if re.search(r'ltx_|logo|icon|badge|pixel|spacer', src, re.I):
                continue
            if not re.search(r'\.(png|jpg|jpeg)$', src, re.I):
                continue
            if len(stem) <= 3:
                continue
            # Skip diagrams, flowcharts, tables, and non-teaser figures
            if re.search(r'uml|deploy|architec|flowchart|table|diagram|pipeline[_-]?fig|system[_-]?fig', stem, re.I):
                continue
            if not src.startswith('http'):
                if src.startswith('./'):
                    src = src[2:]
                if src.startswith(pid):
                    src = f'https://arxiv.org/html/{src}'
                else:
                    src = f'https://arxiv.org/html/{pid}/{src}'
            urls.append(src)
        return pid, ', '.join(urls)
    except Exception as e:
        print(f"    {pid}: image fetch failed ({str(e)[:50]})")
        return pid, ''


def _validate_images(papers_by_section: dict) -> dict:
    all_ids = set()
    for section_papers in papers_by_section.values():
        for p in section_papers:
            if p['versioned_id']:
                all_ids.add(p['versioned_id'])

    print(f"  Validating images for {len(all_ids)} papers...")
    image_map = {}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_extract_images_for_paper, pid): pid for pid in all_ids}
        for future in as_completed(futures):
            pid, urls = future.result()
            image_map[pid] = urls

    for section_papers in papers_by_section.values():
        for p in section_papers:
            pid = p['versioned_id']
            if pid and pid in image_map:
                p['teaser_images'] = image_map[pid]

    return papers_by_section


def fetch_papers() -> dict:
    result = {}
    for i, window in enumerate(DATE_WINDOWS):
        label = window['label']
        if i > 0:
            time.sleep(3)  # arXiv API rate limit: 1 req/3s
        print(f"  Fetching {label}...")
        url = _build_url(window)
        brief = label != 'today'
        try:
            xml_text = _fetch_url(url)
            result[label] = _parse_papers(xml_text, brief)
            print(f"    {len(result[label])} papers")
        except Exception as e:
            print(f"    ERROR: {e}")
            result[label] = []

    result = _validate_images(result)
    return result


def format_paper_text(p: dict) -> str:
    lines = [
        f"Title: {p['title']}",
        f"Authors: {p['authors']}",
        f"Date: {p['published']}",
        f"arXiv: {p['arxiv_link']}",
        f"PDF: {p['pdf_link']}",
        f"Project Page: {p['project_page']}",
        f"Teaser Images: {p['teaser_images']}",
        f"Abstract: {p['abstract']}",
    ]
    return '\n'.join(lines)


if __name__ == '__main__':
    print("Fetching arXiv papers...")
    papers = fetch_papers()
    for section in ['today', 'week', 'month']:
        print(f"\n=== {section.upper()} ({len(papers[section])} papers) ===")
        for p in papers[section]:
            print(f"  - {p['title'][:80]}")
            print(f"    images: {p['teaser_images'][:100]}")
