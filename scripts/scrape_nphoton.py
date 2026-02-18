#!/usr/bin/env python3
"""
Nature Photonics Trend Scraper v2.0
===================================
Scrapes TOC pages from Nature Photonics, extracts structured metadata,
and generates a trend_report.md for use with the /story workflow.

Usage:
    python scrape_nphoton.py --months 6 --output ./trend_data/
    python scrape_nphoton.py --months 6 --output ./trend_data/ --keywords "sSNOM,TERS,near-field"
    python scrape_nphoton.py --read-local ./editorials/   # read locally saved editorial PDFs/HTML

Output:
    - articles_raw.yaml    : structured metadata for all articles
    - editorials.yaml      : editorial metadata + DOIs for manual download
    - trend_report.md      : compressed trend analysis (< 5000 tokens)
"""

import json

import argparse
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import yaml
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://www.nature.com"
JOURNAL_PATHS = {
    "nphoton": "/nphoton",           # Nature Photonics
    "ncomms": "/ncomms",             # Nature Communications
    "nature": "/nature",             # Nature
    "lsa": "/lsa",                   # Light: Science & Applications
    "nphys": "/nphys",               # Nature Physics
    "nmat": "/nmat",                 # Nature Materials
    "nnano": "/nnano",               # Nature Nanotechnology
    "nmeth": "/nmeth",               # Nature Methods
    "nchem": "/nchem",               # Nature Chemistry
    "natelectron": "/natelectron",   # Nature Electronics
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
RATE_LIMIT_SECONDS = 2.0
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"

# Nature Photonics: Volume = year - 2006, Issue = month number
VOLUME_YEAR_OFFSET = 2006

# Fix #3: Broadened editorial-type detection — covers Editorial, Comment, etc.
EDITORIAL_TYPES = {"editorial", "comment", "world view", "correspondence",
                   "news feature", "research highlight"}

# Stopwords for keyword extraction (minimal set for scientific titles)
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "for", "to", "with", "on",
    "at", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "that", "this", "its", "via", "using", "based", "under", "through",
    "between", "into", "as", "not", "can", "has", "have", "their", "more",
    "than", "both", "each", "all", "also", "but", "if", "it", "we", "our",
    "how", "new", "non", "high", "low", "large", "small", "two", "single",
    "very", "here", "show", "use", "may", "about", "which", "up", "out",
    "no", "over", "such", "first", "second", "do", "does", "did", "only",
}

# Fix #1: Structural noise — keywords that appear every issue regardless of trends.
# These are filtered from the "Hot Keywords" table to surface real signals.
DEFAULT_STRUCTURAL_NOISE = {
    "optical", "light", "photonic", "photonics", "laser", "device", "devices",
    "performance", "efficiency", "demonstrated", "enables", "enabling",
    "design", "researchers", "approach", "results", "shows", "report",
    "method", "study", "system", "systems", "measurement", "measurements",
    "structure", "structures", "application", "applications", "properties",
    "material", "materials", "energy", "surface", "wavelength", "emission",
    "spectrum", "fabrication", "resolution", "detection", "operation",
    "correction", "author", "publisher",  # corrigendum noise
}


# ---------------------------------------------------------------------------
# URL Generation
# ---------------------------------------------------------------------------
def compute_volume_issue(year: int, month: int) -> Tuple[int, int]:
    """Convert year/month to Nature Photonics volume/issue numbers."""
    volume = year - VOLUME_YEAR_OFFSET
    issue = month
    return volume, issue


def generate_issue_urls(journal: str, months: int, ref_date: datetime = None):
    """Generate (url, volume, issue, year, month) tuples for the last N months."""
    if ref_date is None:
        ref_date = datetime.now()
    
    journal_path = JOURNAL_PATHS.get(journal, f"/{journal}")
    urls = []
    
    for i in range(months):
        dt = ref_date - timedelta(days=i * 30)  # approximate
        # Correct to actual month
        y = ref_date.year
        m = ref_date.month - i
        while m <= 0:
            m += 12
            y -= 1
        
        vol, iss = compute_volume_issue(y, m)
        url = f"{BASE_URL}{journal_path}/volumes/{vol}/issues/{iss}"
        urls.append({
            "url": url,
            "volume": vol,
            "issue": iss,
            "year": y,
            "month": m,
        })
    
    return urls


# ---------------------------------------------------------------------------
# TOC Scraping
# ---------------------------------------------------------------------------
def fetch_page(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    """Fetch a page and return parsed BeautifulSoup, or None on failure."""
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  ⚠ Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def extract_articles_from_toc(soup: BeautifulSoup, issue_meta: dict) -> list[dict]:
    """Extract article metadata from a TOC page."""
    articles = []
    
    # Nature uses <article> tags for each entry
    article_tags = soup.find_all("article")
    
    for tag in article_tags:
        entry = {}
        
        # Title + URL
        title_link = tag.find("a", {"data-track-action": "view article"})
        if not title_link:
            # Fallback: look for h3 > a
            h3 = tag.find("h3")
            title_link = h3.find("a") if h3 else None
        
        if not title_link:
            continue
        
        entry["title"] = title_link.get_text(strip=True)
        href = title_link.get("href", "")
        entry["url"] = BASE_URL + href if href.startswith("/") else href
        
        # DOI (extract from URL: /articles/s41566-... → 10.1038/s41566-...)
        doi_match = re.search(r"/articles/(s\d+[-\w]+)", href)
        if doi_match:
            entry["doi"] = f"10.1038/{doi_match.group(1)}"
        
        # Article type — Nature uses <span class="c-meta__type">
        type_span = tag.find("span", class_="c-meta__type")
        entry["article_type"] = type_span.get_text(strip=True) if type_span else "Article"
        
        # Abstract snippet — Nature uses <div class="c-card__summary" itemprop="description">
        summary_div = tag.find("div", class_="c-card__summary")
        if summary_div:
            p = summary_div.find("p")
            entry["abstract_snippet"] = p.get_text(strip=True) if p else summary_div.get_text(strip=True)
        else:
            entry["abstract_snippet"] = ""
        
        # Authors — Nature uses <span itemprop="name"> inside <li itemprop="creator">
        author_spans = tag.find_all("span", attrs={"itemprop": "name"})
        entry["authors"] = [s.get_text(strip=True) for s in author_spans]
        
        # Date
        date_tag = tag.find("time")
        if date_tag:
            entry["date"] = date_tag.get("datetime", date_tag.get_text(strip=True))
        else:
            date_span = tag.find("span", class_=re.compile(r"date"))
            entry["date"] = date_span.get_text(strip=True) if date_span else ""
        
        # Open Access?
        oa_tag = tag.find("span", class_=re.compile(r"open-access|oa-label"))
        if not oa_tag:
            oa_tag = tag.find("span", string=re.compile(r"Open Access", re.I))
        entry["open_access"] = bool(oa_tag)
        
        # Issue metadata
        entry["volume"] = issue_meta["volume"]
        entry["issue"] = issue_meta["issue"]
        entry["year"] = issue_meta["year"]
        entry["month"] = issue_meta["month"]
        
        articles.append(entry)
    
    return articles


# ---------------------------------------------------------------------------
# Editorial Handling (hybrid: scrape public + provide DOI for manual)
# ---------------------------------------------------------------------------
def extract_editorial_public(article_url: str, session: requests.Session) -> dict:
    """Try to extract publicly visible editorial content."""
    soup = fetch_page(article_url, session)
    if not soup:
        return {}
    
    result = {}
    
    # Title
    h1 = soup.find("h1", class_=re.compile(r"article-title|ArticleTitle"))
    if not h1:
        h1 = soup.find("h1")
    result["title"] = h1.get_text(strip=True) if h1 else ""
    
    # First paragraph (usually visible even behind paywall)
    body = soup.find("div", class_=re.compile(r"article-body|body"))
    if body:
        first_p = body.find("p")
        result["first_paragraph"] = first_p.get_text(strip=True) if first_p else ""
    
    # If full text is visible, grab it
    paragraphs = body.find_all("p") if body else []
    if len(paragraphs) > 1:
        result["full_text"] = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        result["access"] = "full"
    else:
        result["access"] = "partial"
    
    return result


# ---------------------------------------------------------------------------
# Local Editorial Reader (for manually downloaded files)
# ---------------------------------------------------------------------------
def read_local_editorials(directory: str) -> list[dict]:
    """Read locally saved editorial files (.txt, .md, .html) from a directory."""
    editorials = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"  ℹ Editorial directory '{directory}' not found. Skipping local read.")
        return editorials
    
    for f in sorted(dir_path.iterdir()):
        if f.suffix in (".txt", ".md", ".html"):
            content = f.read_text(encoding="utf-8", errors="replace")
            
            if f.suffix == ".html":
                soup = BeautifulSoup(content, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
            else:
                text = content
            
            editorials.append({
                "filename": f.name,
                "full_text": text,
                "access": "local",
            })
            print(f"  ✓ Read local editorial: {f.name}")
    
    return editorials


# ---------------------------------------------------------------------------
# Keyword Extraction & Trend Analysis
# ---------------------------------------------------------------------------
def extract_keywords_from_text(text: str) -> list[str]:
    """Extract meaningful words/phrases from title/abstract text.
    
    Preserves hyphenated compounds (e.g. 'light-emitting', 'tip-enhanced').
    Minimum 4 characters to avoid fragment noise ('tin', 'per', 'mit', 'gan').
    """
    # First extract hyphenated compounds as single tokens
    compounds = re.findall(r'[a-zA-Z]{3,}(?:-[a-zA-Z]{3,})+', text.lower())
    # Then extract single words (≥4 chars, letter-bounded)
    words = re.findall(r'\b[a-zA-Z][a-zA-Z]{3,}\b', text.lower())
    tokens = compounds + [w for w in words if w not in STOPWORDS and len(w) >= 4]
    return tokens


def classify_framing(snippet: str) -> str:
    """Fix #2: Expanded framing pattern classification.
    
    Nature's TOC snippets are often editor-written in third person, so we need
    broader patterns than just 'We demonstrate...' to avoid 73% 'other'.
    """
    if not snippet:
        return ""
    first_sentence = snippet.split(".")[0].strip() if "." in snippet else snippet
    
    # Problem-first: opens with a challenge or gap
    if re.match(
        r"(The inability|A major challenge|Despite|Although|However|The lack|"
        r"Limitations|The difficulty|Current|Existing|Challenges|While)",
        first_sentence, re.I,
    ):
        return "problem-first"
    
    # Result-first (first person): "We demonstrate / show / report..."
    if re.match(
        r"(We demonstrate|We show|We report|We present|We develop|We achieve)",
        first_sentence, re.I,
    ):
        return "result-first"
    
    # Passive-demonstrated: "...is demonstrated / are reported / is achieved"
    if re.search(
        r"(is|are|was|were)\s+(demonstrated|reported|shown|achieved|realized|presented|enabled|obtained)",
        first_sentence, re.I,
    ):
        return "passive-demonstrated"
    
    # Method-first: "By combining / Using / Through"
    if re.match(
        r"(By |Using |Through |Via |Combining )",
        first_sentence, re.I,
    ):
        return "method-first"
    
    # Vision-first: "X promises / offers"
    if re.match(
        r"(\w+\s+(promises|offers|allows|paves|opens))",
        first_sentence, re.I,
    ):
        return "vision-first"
    
    # FALLBACK: object-first (default for Nature editor snippets)
    return "object-first"


def analyze_trends(
    articles: list[dict],
    user_keywords: list[str] = None,
    exclude_keywords: Optional[set] = None,
):
    """Analyze keyword trends and framing patterns from scraped articles.
    
    Fix #1: exclude_keywords filters out structural noise (keywords that always
    appear because the journal has persistent topic biases, e.g. 'perovskite'
    in Nature Photonics).
    """
    noise = exclude_keywords or set()
    keyword_counter = Counter()
    type_counter = Counter()
    opening_patterns = Counter()
    
    # Separate by half-period for trend detection
    mid_date = datetime.now()
    if articles:
        dates = []
        for a in articles:
            try:
                d = datetime.fromisoformat(a.get("date", "").replace("Z", "+00:00"))
                dates.append(d)
            except (ValueError, TypeError):
                pass
        if dates:
            mid_date = min(dates) + (max(dates) - min(dates)) / 2
    
    recent_keywords = Counter()
    older_keywords = Counter()
    
    for article in articles:
        # Article type distribution
        atype = article.get("article_type", "Article")
        type_counter[atype] += 1
        
        # Keywords from title + abstract
        text = article.get("title", "") + " " + article.get("abstract_snippet", "")
        kws = extract_keywords_from_text(text)
        keyword_counter.update(kws)
        
        # Trend detection: recent vs older
        try:
            d = datetime.fromisoformat(article.get("date", "").replace("Z", "+00:00"))
            if d > mid_date:
                recent_keywords.update(kws)
            else:
                older_keywords.update(kws)
        except (ValueError, TypeError):
            pass
        
        # Fix #2: Expanded framing classification
        snippet = article.get("abstract_snippet", "")
        pattern = classify_framing(snippet)
        if pattern:
            opening_patterns[pattern] += 1
    
    # Trend scoring: rising vs declining
    # Fix #1: filter out structural noise from trending
    trending = {}
    all_kws = set(recent_keywords.keys()) | set(older_keywords.keys())
    for kw in all_kws:
        if kw in noise:
            continue
        r = recent_keywords.get(kw, 0)
        o = older_keywords.get(kw, 0)
        if o == 0 and r > 0:
            trend = "▴ new"
        elif r > o * 1.3:
            trend = "▴ rising"
        elif r < o * 0.7:
            trend = "▾ declining"
        else:
            trend = "▸ stable"
        trending[kw] = {"recent": r, "older": o, "trend": trend, "total": r + o}
    
    # User keyword gap analysis
    user_kw_status = {}
    if user_keywords:
        for ukw in user_keywords:
            ukw_lower = ukw.lower().strip()
            total = keyword_counter.get(ukw_lower, 0)
            user_kw_status[ukw] = "✅ present" if total > 0 else "❌ absent"
    
    return {
        "keyword_counts": keyword_counter.most_common(30),
        "type_distribution": dict(type_counter),
        "opening_patterns": dict(opening_patterns),
        "trending": trending,
        "user_keyword_status": user_kw_status,
    }


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------
def generate_trend_report(
    articles: list[dict],
    editorials: list[dict],
    analysis: dict,
    user_keywords: list[str],
    months: int,
    journal: str,
    output_dir: str,
    seed_network: list[dict] = None,
    cross_journal_results: list[dict] = None,
):
    """Generate trend_report.md from analyzed data."""
    now = datetime.now()
    journal_name = {
        "nphoton": "Nature Photonics",
        "ncomms": "Nature Communications",
        "nature": "Nature",
    }.get(journal, journal)
    
    lines = [
        f"# {journal_name} Trend Report",
        f"## Period: last {months} months (generated {now.strftime('%Y-%m-%d')})",
        f"## Total articles scraped: {len(articles)}",
        "",
        "---",
        "",
    ]
    
    # Section 1: Editorial signals (Fix #3: broadened matching)
    editorial_articles = [
        a for a in articles
        if a.get("article_type", "").lower() in EDITORIAL_TYPES
    ]
    if editorial_articles or editorials:
        lines.append("## 1. Editorial Signals")
        lines.append("")
        lines.append("| Date | Title | Type |")
        lines.append("|:--|:--|:--|")
        for ea in editorial_articles:
            lines.append(f"| {ea.get('date', 'N/A')} | {ea.get('title', 'N/A')} | {ea.get('article_type', 'Editorial')} |")
        lines.append("")
        
        # If we have full-text editorials (local or scraped)
        if editorials:
            lines.append("### Editorial Full-Text Excerpts")
            lines.append("")
            for ed in editorials:
                lines.append(f"**{ed.get('title', ed.get('filename', 'Unknown'))}**")
                text = ed.get("full_text", ed.get("first_paragraph", ""))
                # Truncate to ~300 words to save tokens
                words = text.split()
                if len(words) > 300:
                    text = " ".join(words[:300]) + " [...]"
                lines.append(f"> {text}")
                lines.append("")
    
    # Section 2: Hot keywords
    lines.append("## 2. Hot Keywords (Top 20)")
    lines.append("")
    lines.append("| Keyword | Count | Trend | Your Manuscript |")
    lines.append("|:--|:--|:--|:--|")
    
    trending = analysis.get("trending", {})
    top_kws = sorted(trending.items(), key=lambda x: x[1]["total"], reverse=True)[:20]
    user_kw_set = {k.lower().strip() for k in (user_keywords or [])}
    
    for kw, info in top_kws:
        in_ms = "✅" if kw in user_kw_set else ""
        lines.append(f"| {kw} | {info['total']} | {info['trend']} | {in_ms} |")
    
    lines.append("")
    
    # User keyword gap
    if analysis.get("user_keyword_status"):
        lines.append("### Your Keywords vs Trend")
        lines.append("")
        for kw, status in analysis["user_keyword_status"].items():
            lines.append(f"- **{kw}**: {status}")
        lines.append("")
    
    # Section 3: Framing patterns
    lines.append("## 3. Abstract Framing Patterns")
    lines.append("")
    op = analysis.get("opening_patterns", {})
    total_op = sum(op.values()) or 1
    for pattern, count in sorted(op.items(), key=lambda x: -x[1]):
        pct = int(100 * count / total_op)
        lines.append(f"- **{pattern}**: {count} ({pct}%)")
    lines.append("")
    
    # Section 4: Article type distribution
    lines.append("## 4. Article Type Distribution")
    lines.append("")
    for atype, count in sorted(analysis.get("type_distribution", {}).items(), key=lambda x: -x[1]):
        lines.append(f"- {atype}: {count}")
    lines.append("")
    
    # Section 5: Editorial DOIs for manual download
    editorials_needing_download = [
        a for a in editorial_articles
        if not any(e.get("title") == a.get("title") for e in editorials)
    ]
    if editorials_needing_download:
        lines.append("## 5. Editorials — Manual Download Needed")
        lines.append("")
        lines.append("These editorials could not be fully scraped. Download them locally")
        lines.append(f"and save to `editorials/` folder, then re-run with `--read-local editorials/`.")
        lines.append("")
        lines.append("| Title | DOI | URL |")
        lines.append("|:--|:--|:--|")
        for ea in editorials_needing_download:
            doi = ea.get("doi", "N/A")
            url = ea.get("url", "N/A")
            lines.append(f"| {ea.get('title', 'N/A')} | {doi} | [link]({url}) |")
        lines.append("")
    
    # Section 6: News & Views Analysis (Fix #4)
    nv_articles = [a for a in articles if "news & views" in a.get("article_type", "").lower()]
    if nv_articles:
        lines.append("## 6. News & Views Analysis")
        lines.append("")
        lines.append("> N&V pieces are editor-commissioned — they signal what the editorial")
        lines.append("> team considers the most impactful work in each issue.")
        lines.append("")
        lines.append("| N&V Title | Snippet | Date |")
        lines.append("|:--|:--|:--|")
        for nv in nv_articles:
            snippet = nv.get("abstract_snippet", "")
            # Truncate snippet for table readability
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            lines.append(f"| {nv.get('title', 'N/A')} | {snippet} | {nv.get('date', '')} |")
        lines.append("")
        
        # Extract future-looking statements (tightened: removed 'enabl' false positives)
        future_signals = []
        for nv in nv_articles:
            snippet = nv.get("abstract_snippet", "")
            for sent in re.split(r'[.!]', snippet):
                sent = sent.strip()
                if re.search(r'(future|potential|promise|paving|toward|prospect|outlook|could\s+lead|will\s+allow)', sent, re.I) and len(sent) > 20:
                    future_signals.append((nv.get("title", ""), sent))
        
        if future_signals:
            lines.append("### N&V Future Directions")
            lines.append("")
            for title, signal in future_signals:
                lines.append(f"- **{title}**: \"{signal}\"")
            lines.append("")
    
    # Section 7: Most Relevant Articles (if relevance scores available)
    relevant = [a for a in articles if a.get("relevance_score", 0) > 0]
    if relevant:
        relevant_sorted = sorted(relevant, key=lambda x: x.get("relevance_score", 0), reverse=True)[:15]
        lines.append("## 7. Most Relevant to Your Research")
        lines.append("")
        lines.append("> Ranked by keyword overlap with your `--keywords`.")
        lines.append("> Articles marked ★ have full abstracts fetched below.")
        lines.append("")
        lines.append("| Score | Title | Type | Date |")
        lines.append("|:--|:--|:--|:--|")
        for a in relevant_sorted:
            star = "★" if a.get("full_abstract") else ""
            lines.append(f"| {a['relevance_score']} {star} | {a.get('title', 'N/A')} | {a.get('article_type', 'N/A')} | {a.get('date', 'N/A')} |")
        lines.append("")
        
        # Show full abstracts for articles that have them
        with_abs = [a for a in relevant_sorted if a.get("full_abstract")]
        if with_abs:
            lines.append("### Full Abstracts (Top Relevant)")
            lines.append("")
            for a in with_abs:
                lines.append(f"**{a.get('title', 'N/A')}** ({a.get('date', '')})")
                lines.append(f"> {a['full_abstract']}")
                lines.append("")
    
    # Section 8: Citation Context (if Semantic Scholar data available)
    cited_articles = [a for a in articles if a.get("citation_count") is not None]
    if cited_articles:
        lines.append("## 8. Citation Context (Semantic Scholar)")
        lines.append("")
        lines.append("| Title | Citations | Key References |")
        lines.append("|:--|:--|:--|")
        for a in sorted(cited_articles, key=lambda x: x.get("citation_count", 0), reverse=True)[:10]:
            refs = a.get("top_references", [])
            ref_str = "; ".join(refs[:3]) if refs else "—"
            lines.append(f"| {a.get('title', 'N/A')} | {a.get('citation_count', 0)} | {ref_str} |")
        lines.append("")
    
    # Section 9: Niche-Relevant Keywords
    if user_keywords:
        niche_kws = []
        user_kw_lower = {k.lower().strip() for k in user_keywords}
        trending = analysis.get("trending", {})
        for kw, info in trending.items():
            cooccur = 0
            for a in articles:
                text = (a.get("title", "") + " " + a.get("abstract_snippet", "")).lower()
                if kw in text and any(uk in text for uk in user_kw_lower):
                    cooccur += 1
            if cooccur > 0:
                niche_kws.append((kw, info["total"], info["trend"], cooccur))
        
        if niche_kws:
            niche_kws.sort(key=lambda x: x[3], reverse=True)
            lines.append("## 9. Niche-Relevant Keywords")
            lines.append("")
            lines.append("> Keywords that co-occur with your manuscript keywords in the same article.")
            lines.append("")
            lines.append("| Keyword | Total | Trend | Co-occurrence |")
            lines.append("|:--|:--|:--|:--|")
            for kw, total, trend, cooccur in niche_kws[:15]:
                lines.append(f"| {kw} | {total} | {trend} | {cooccur} |")
            lines.append("")
    
    # Section 11: Seed Citation Network
    if seed_network:
        lines.append("## 11. Benchmark Citation Network")
        lines.append("")
        lines.append("> Citation landscape of your seed (benchmark) papers via Semantic Scholar.")
        lines.append("")
        for seed in seed_network:
            lines.append(f"### {seed['title']} ({seed.get('year', '?')})")
            lines.append(f"**Venue**: {seed.get('venue', 'N/A')} | **Citations**: {seed.get('citation_count', 0)}")
            lines.append("")
            if seed.get('top_citing'):
                lines.append("**Top Citing Papers** (who builds on this work):")
                lines.append("")
                lines.append("| Title | Year | Venue |")
                lines.append("|:--|:--|:--|")
                for c in seed['top_citing']:
                    lines.append(f"| {c['title']} | {c.get('year', '')} | {c.get('venue', '')} |")
                lines.append("")
            if seed.get('key_references'):
                lines.append("**Key References** (what this work builds on):")
                lines.append("")
                lines.append("| Title | Year | Venue |")
                lines.append("|:--|:--|:--|")
                for r in seed['key_references']:
                    lines.append(f"| {r['title']} | {r.get('year', '')} | {r.get('venue', '')} |")
                lines.append("")
    
    # Section 12: Cross-Journal Results
    if cross_journal_results:
        lines.append("## 12. Cross-Journal Keyword Matches")
        lines.append("")
        lines.append("> Recent articles matching your keywords in other journals.")
        lines.append("")
        lines.append("| Title | Journal | Date |")
        lines.append("|:--|:--|:--|")
        for r in cross_journal_results:
            lines.append(f"| {r.get('title', 'N/A')} | {r.get('journal', 'N/A')} | {r.get('date', '')} |")
        lines.append("")
    
    # Section 13: Full Article List
    lines.append("## 13. Full Article List")
    lines.append("")
    lines.append("| # | Title | Type | Date |")
    lines.append("|:--|:--|:--|:--|")
    for i, a in enumerate(articles, 1):
        lines.append(f"| {i} | {a.get('title', 'N/A')} | {a.get('article_type', 'N/A')} | {a.get('date', 'N/A')} |")
    lines.append("")
    
    report_text = "\n".join(lines)
    report_path = Path(output_dir) / "trend_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n✓ Trend report saved: {report_path}")
    print(f"  Report size: ~{len(report_text.split())} words / ~{len(report_text) // 4} tokens (est.)")
    
    return report_text


# ---------------------------------------------------------------------------
# Full Abstract Fetcher
# ---------------------------------------------------------------------------
def fetch_full_abstract(url: str, session: requests.Session) -> Optional[str]:
    """Fetch the full abstract from a Nature article page.
    
    Nature publicly displays abstracts even for paywalled articles.
    """
    try:
        soup = fetch_page(url, session)
        if not soup:
            return None
        
        # Primary: structured abstract div
        abs_div = soup.find("div", id="Abs1-content")
        if abs_div:
            return abs_div.get_text(separator=" ", strip=True)
        
        # Fallback: section with data-title="Abstract"
        abs_section = soup.find("section", attrs={"data-title": "Abstract"})
        if abs_section:
            content = abs_section.find("div", class_="c-article-section__content")
            if content:
                return content.get_text(separator=" ", strip=True)
        
        # Last resort: meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"]
        
        return None
    except Exception as e:
        print(f"  ⚠ Abstract fetch failed for {url}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Relevance Scoring
# ---------------------------------------------------------------------------
def compute_relevance_score(article: dict, user_keywords: list) -> int:
    """Score article relevance: +2 for keyword in title, +1 for keyword in snippet."""
    if not user_keywords:
        return 0
    
    title = article.get("title", "").lower()
    snippet = article.get("abstract_snippet", "").lower()
    score = 0
    
    for kw in user_keywords:
        kw_lower = kw.lower().strip()
        if kw_lower in title:
            score += 2
        if kw_lower in snippet:
            score += 1
    
    return score


# ---------------------------------------------------------------------------
# Semantic Scholar Citation Context
# ---------------------------------------------------------------------------
def fetch_citation_context(doi: str, session: requests.Session) -> Optional[dict]:
    """Query Semantic Scholar API for citation count and key references.
    
    Free API, no key needed, rate limit ~100 req/5 min.
    """
    if not doi:
        return None
    
    try:
        url = f"{SEMANTIC_SCHOLAR_API}/DOI:{doi}?fields=title,citationCount,references.title"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            refs = data.get("references", []) or []
            return {
                "citation_count": data.get("citationCount", 0),
                "top_references": [r["title"] for r in refs[:5] if r.get("title")],
            }
        elif resp.status_code == 429:
            print("  ⚠ Semantic Scholar rate limit hit. Pausing 30s...", file=sys.stderr)
            time.sleep(30)
            return None
        else:
            return None
    except Exception as e:
        print(f"  ⚠ Semantic Scholar query failed for {doi}: {e}", file=sys.stderr)
        return None


def fetch_seed_citation_network(doi: str, session: requests.Session) -> Optional[dict]:
    """Fetch full citation network for a benchmark (seed) DOI.
    
    Returns the paper's title, citation count, top citing papers, and references.
    Used with --seed-dois to map your competitive landscape.
    """
    if not doi:
        return None
    
    try:
        # Get paper info + citations (who cites it) + references (what it cites)
        url = (f"{SEMANTIC_SCHOLAR_API}/DOI:{doi}"
               f"?fields=title,citationCount,year,venue,"
               f"citations.title,citations.year,citations.venue,citations.citationCount,"
               f"references.title,references.year,references.venue")
        resp = session.get(url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            citations = data.get("citations", []) or []
            references = data.get("references", []) or []
            # Sort citing papers by their own citation count (most impactful first)
            citations_sorted = sorted(
                [c for c in citations if c.get("title")],
                key=lambda x: x.get("citationCount", 0), reverse=True
            )
            return {
                "title": data.get("title", ""),
                "year": data.get("year"),
                "venue": data.get("venue", ""),
                "citation_count": data.get("citationCount", 0),
                "top_citing": [
                    {"title": c["title"], "year": c.get("year"), "venue": c.get("venue", "")}
                    for c in citations_sorted[:10]
                ],
                "key_references": [
                    {"title": r["title"], "year": r.get("year"), "venue": r.get("venue", "")}
                    for r in references[:10] if r.get("title")
                ],
            }
        elif resp.status_code == 429:
            print("  ⚠ Rate limit hit. Pausing 30s...", file=sys.stderr)
            time.sleep(30)
            return None
        else:
            return None
    except Exception as e:
        print(f"  ⚠ Seed DOI query failed for {doi}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Cross-Journal Keyword Search (via Nature search)
# ---------------------------------------------------------------------------
def search_nature_keywords(
    keywords: list[str],
    journals: list[str],
    session: requests.Session,
    max_results: int = 20,
) -> list[dict]:
    """Search nature.com across multiple journals for keyword-matching articles.
    
    Uses the nature.com search page to find recent articles matching
    user keywords in specified journals (e.g. ACS Nano via nature search,
    Nano Letters, Optica, etc.).
    """
    results = []
    query = " OR ".join(f'"{kw}"' for kw in keywords[:5])  # top 5 keywords as query
    
    for journal_filter in journals:
        try:
            # Nature.com search supports journal filtering
            search_url = (f"{BASE_URL}/search?q={query}"
                         f"&journal={journal_filter}&order=relevance&date_range=last_1_year")
            soup = fetch_page(search_url, session)
            if not soup:
                continue
            
            # Parse search results
            items = soup.find_all("article", class_="c-card")
            if not items:
                items = soup.find_all("li", class_="app-article-list-row__item")
            
            for item in items[:max_results]:
                title_tag = item.find(["h3", "h2"])
                if not title_tag:
                    continue
                link_tag = title_tag.find("a")
                title = title_tag.get_text(strip=True)
                url = ""
                if link_tag and link_tag.get("href"):
                    href = link_tag["href"]
                    url = href if href.startswith("http") else BASE_URL + href
                
                # Date
                date_tag = item.find("time")
                date_str = date_tag.get("datetime", "") if date_tag else ""
                
                # Journal name
                journal_tag = item.find("span", {"data-test": "journal-title"})
                if not journal_tag:
                    journal_tag = item.find("p", class_="c-card__journal-title")
                journal_name = journal_tag.get_text(strip=True) if journal_tag else journal_filter
                
                results.append({
                    "title": title,
                    "url": url,
                    "date": date_str[:10] if date_str else "",
                    "journal": journal_name,
                    "source": "cross-journal-search",
                })
            
            time.sleep(RATE_LIMIT_SECONDS)
        except Exception as e:
            print(f"  ⚠ Cross-journal search failed for {journal_filter}: {e}", file=sys.stderr)
    
    return results


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Nature Photonics Trend Scraper — extracts article metadata and generates trend analysis"
    )
    parser.add_argument(
        "--months", type=int, default=6,
        help="Number of months to look back (default: 6)"
    )
    parser.add_argument(
        "--output", type=str, default="./trend_data/",
        help="Output directory for YAML and report files"
    )
    parser.add_argument(
        "--keywords", type=str, default="",
        help="Comma-separated list of your manuscript keywords for gap analysis"
    )
    parser.add_argument(
        "--journal", type=str, default="nphoton",
        help="Journal key: nphoton, ncomms, nature, lsa (default: nphoton)"
    )
    parser.add_argument(
        "--read-local", type=str, default="",
        help="Path to directory with locally saved editorial files (.txt/.md/.html)"
    )
    parser.add_argument(
        "--scrape-editorials", action="store_true",
        help="Attempt to scrape editorial article pages for full text"
    )
    parser.add_argument(
        "--exclude", type=str, default="",
        help="Comma-separated keywords to exclude from trend analysis (structural noise)"
    )
    parser.add_argument(
        "--no-default-exclude", action="store_true",
        help="Disable the built-in structural noise filter"
    )
    parser.add_argument(
        "--fetch-abstracts", type=int, default=0, metavar="N",
        help="Fetch full abstracts for top N most relevant articles (default: 0 = off)"
    )
    parser.add_argument(
        "--citation-context", action="store_true",
        help="Query Semantic Scholar API for citation counts and references"
    )
    parser.add_argument(
        "--seed-dois", type=str, default="",
        help="Comma-separated DOIs of benchmark papers to map citation networks"
    )
    parser.add_argument(
        "--cross-journal", type=str, default="",
        help="Comma-separated Nature journal codes for cross-journal keyword search (e.g. 'nnano,nmat')"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    user_keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    
    # Fix #1: Build exclusion set (structural noise)
    exclude_keywords = set() if args.no_default_exclude else set(DEFAULT_STRUCTURAL_NOISE)
    if args.exclude:
        exclude_keywords.update(k.strip().lower() for k in args.exclude.split(",") if k.strip())
    
    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║  Nature Photonics Trend Scraper v2.0            ║")
    print(f"╠══════════════════════════════════════════════════╣")
    print(f"║  Journal:  {args.journal:<37s} ║")
    print(f"║  Months:   {args.months:<37d} ║")
    print(f"║  Output:   {str(output_dir):<37s} ║")
    if user_keywords:
        kw_str = ", ".join(user_keywords[:5])
        print(f"║  Keywords: {kw_str:<37s} ║")
    if args.fetch_abstracts:
        print(f"║  Abstracts: top {args.fetch_abstracts:<32d} ║")
    if args.citation_context:
        print(f"║  Citations: Semantic Scholar          ║")
    if args.seed_dois:
        print(f"║  Seed DOIs: {len(args.seed_dois.split(',')):<36d} ║")
    if args.cross_journal:
        print(f"║  Cross-J:   {args.cross_journal:<36s} ║")
    print(f"╚══════════════════════════════════════════════════╝")
    print()
    
    # --- Step 1: Generate issue URLs ---
    issue_urls = generate_issue_urls(args.journal, args.months)
    print(f"📋 Will scrape {len(issue_urls)} issues:")
    for iu in issue_urls:
        print(f"   Vol {iu['volume']} Issue {iu['issue']} ({iu['year']}-{iu['month']:02d})")
    print()
    
    # --- Step 2: Scrape TOC pages ---
    session = requests.Session()
    all_articles = []
    
    for i, iu in enumerate(issue_urls):
        print(f"🔍 [{i+1}/{len(issue_urls)}] Scraping Vol {iu['volume']} Issue {iu['issue']}...")
        soup = fetch_page(iu["url"], session)
        if soup:
            articles = extract_articles_from_toc(soup, iu)
            all_articles.extend(articles)
            print(f"   ✓ Found {len(articles)} articles")
        else:
            print(f"   ✗ Failed to load page")
        
        if i < len(issue_urls) - 1:
            time.sleep(RATE_LIMIT_SECONDS)
    
    print(f"\n📊 Total articles scraped: {len(all_articles)}")
    
    # --- Step 3: Save raw YAML ---
    articles_yaml_path = output_dir / "articles_raw.yaml"
    with open(articles_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(all_articles, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"✓ Raw data saved: {articles_yaml_path}")
    
    # --- Step 4: Handle Editorials ---
    editorials = []
    
    # 4a: Try scraping editorial pages
    if args.scrape_editorials:
        # Fix #3: broadened editorial detection
        editorial_articles = [
            a for a in all_articles
            if a.get("article_type", "").lower() in EDITORIAL_TYPES
        ]
        print(f"\n📝 Attempting to scrape {len(editorial_articles)} editorial(s)...")
        for ea in editorial_articles:
            print(f"   Fetching: {ea.get('title', 'N/A')}")
            ed_content = extract_editorial_public(ea["url"], session)
            if ed_content:
                ed_content["doi"] = ea.get("doi", "")
                editorials.append(ed_content)
                print(f"   ✓ Access: {ed_content.get('access', 'unknown')}")
            time.sleep(RATE_LIMIT_SECONDS)
    
    # 4b: Read locally saved editorials
    if args.read_local:
        print(f"\n📂 Reading local editorials from: {args.read_local}")
        local_eds = read_local_editorials(args.read_local)
        editorials.extend(local_eds)
    
    # Save editorials YAML
    if editorials:
        ed_yaml_path = output_dir / "editorials.yaml"
        with open(ed_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(editorials, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"✓ Editorial data saved: {ed_yaml_path}")
    
    # --- Step 5: Relevance scoring ---
    if user_keywords:
        print(f"\n🎯 Computing relevance scores...")
        for a in all_articles:
            a["relevance_score"] = compute_relevance_score(a, user_keywords)
        relevant_count = sum(1 for a in all_articles if a["relevance_score"] > 0)
        print(f"   ✓ {relevant_count} articles have relevance > 0")
    
    # --- Step 6: Fetch full abstracts for top relevant ---
    if args.fetch_abstracts > 0 and user_keywords:
        ranked = sorted(all_articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
        to_fetch = [a for a in ranked if a.get("relevance_score", 0) > 0][:args.fetch_abstracts]
        print(f"\n📖 Fetching full abstracts for top {len(to_fetch)} relevant articles...")
        for i, a in enumerate(to_fetch):
            print(f"   [{i+1}/{len(to_fetch)}] {a.get('title', 'N/A')[:60]}...")
            abstract = fetch_full_abstract(a["url"], session)
            if abstract:
                a["full_abstract"] = abstract
                print(f"   ✓ {len(abstract)} chars")
            else:
                print(f"   ✗ Could not fetch")
            time.sleep(RATE_LIMIT_SECONDS)
    
    # --- Step 7: Citation context via Semantic Scholar ---
    if args.citation_context:
        relevant_for_cite = sorted(
            [a for a in all_articles if a.get("relevance_score", 0) > 0],
            key=lambda x: x.get("relevance_score", 0), reverse=True
        )[:15]
        if not relevant_for_cite:
            relevant_for_cite = all_articles[:10]
        
        print(f"\n🔗 Querying Semantic Scholar for {len(relevant_for_cite)} articles...")
        for i, a in enumerate(relevant_for_cite):
            doi = a.get("doi", "")
            if not doi:
                continue
            print(f"   [{i+1}/{len(relevant_for_cite)}] {a.get('title', 'N/A')[:50]}...")
            ctx = fetch_citation_context(doi, session)
            if ctx:
                a["citation_count"] = ctx["citation_count"]
                a["top_references"] = ctx["top_references"]
                print(f"   ✓ {ctx['citation_count']} citations, {len(ctx['top_references'])} refs")
            time.sleep(1.0)
    
    # --- Step 7b: Seed-DOI citation network ---
    seed_network = []
    if args.seed_dois:
        seed_dois = [d.strip() for d in args.seed_dois.split(",") if d.strip()]
        print(f"\n📚 Querying Semantic Scholar for {len(seed_dois)} seed/benchmark DOIs...")
        for i, doi in enumerate(seed_dois):
            print(f"   [{i+1}/{len(seed_dois)}] {doi}")
            result = fetch_seed_citation_network(doi, session)
            if result:
                seed_network.append(result)
                print(f"   ✓ {result['title'][:50]}... ({result['citation_count']} citations)")
            else:
                print(f"   ✗ Not found")
            time.sleep(1.5)
    
    # --- Step 7c: Cross-journal keyword search ---
    cross_journal_results = []
    if args.cross_journal and user_keywords:
        cj_journals = [j.strip() for j in args.cross_journal.split(",") if j.strip()]
        print(f"\n🌐 Cross-journal search for your keywords in {cj_journals}...")
        cross_journal_results = search_nature_keywords(user_keywords, cj_journals, session)
        print(f"   ✓ Found {len(cross_journal_results)} articles across journals")
    
    # --- Step 8: Analyze trends ---
    print(f"\n🔬 Analyzing trends...")
    analysis = analyze_trends(all_articles, user_keywords, exclude_keywords)
    
    # --- Step 9: Generate report ---
    generate_trend_report(
        articles=all_articles,
        editorials=editorials,
        analysis=analysis,
        user_keywords=user_keywords,
        months=args.months,
        journal=args.journal,
        output_dir=str(output_dir),
        seed_network=seed_network,
        cross_journal_results=cross_journal_results,
    )
    
    # --- Step 9b: Save updated YAML with new fields ---
    articles_yaml_path = output_dir / "articles_raw.yaml"
    with open(articles_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(all_articles, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"✓ Updated data saved: {articles_yaml_path}")
    
    # --- Summary ---
    print(f"\n{'='*50}")
    print(f"✅ Done! Files saved to: {output_dir}/")
    print(f"   📄 articles_raw.yaml   — raw metadata ({len(all_articles)} articles)")
    if editorials:
        print(f"   📝 editorials.yaml     — editorial content ({len(editorials)} items)")
    print(f"   📊 trend_report.md     — trend analysis for /story workflow")
    
    # Check for editorials that need manual download (Fix #3: broadened)
    ed_types = [
        a for a in all_articles
        if a.get("article_type", "").lower() in EDITORIAL_TYPES
    ]
    unscraped = [a for a in ed_types if not any(
        e.get("title") == a.get("title") for e in editorials
    )]
    if unscraped:
        print(f"\n⚠  {len(unscraped)} editorial(s) need manual download:")
        for a in unscraped:
            print(f"   → {a.get('title', 'N/A')}")
            print(f"     DOI: {a.get('doi', 'N/A')}")
            print(f"     URL: {a.get('url', 'N/A')}")
        print(f"   Save them to a folder and re-run with: --read-local <folder>")


if __name__ == "__main__":
    main()
