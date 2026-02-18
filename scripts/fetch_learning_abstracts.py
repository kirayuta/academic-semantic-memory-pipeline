"""Fetch full abstracts for the 20 selected learning articles.

Reads selected_20.yaml, pulls DOIs from articles_raw.yaml,
fetches full abstracts from nature.com, and saves to
knowledge_base/abstracts_20.yaml — structured for Move analysis.
"""
import sys, time, re, yaml, requests
from pathlib import Path
from bs4 import BeautifulSoup

BASE_URL = "https://www.nature.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
RATE_LIMIT = 2.0


def fetch_page(url, session):
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  ⚠ Failed: {url}: {e}", file=sys.stderr)
        return None


def fetch_full_abstract(url, session):
    """Fetch abstract from a Nature article page."""
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


def split_into_sentences(text):
    """Split abstract text into individual sentences."""
    # Handle common abbreviations that contain periods
    text = re.sub(r'\b(Fig|Figs|Ref|Refs|et al|i\.e|e\.g|vs|Dr|Mr|Mrs|etc)\.',
                  lambda m: m.group(0).replace('.', '<DOT>'), text)
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    # Restore dots
    sentences = [s.replace('<DOT>', '.').strip() for s in sentences if s.strip()]
    return sentences



def auto_select_20(articles, output_path):
    """Legacy fallback: auto-select 20 articles when selected_20.yaml is missing.

    DEPRECATED: The AI selection in Step 2b-2 of /polish_abstract is preferred.
    This function only runs if the AI selection step was skipped or the file
    was accidentally deleted. Its selection is purely mechanical (newest by date)
    and does not consider manuscript relevance.

    Selection strategy:
    - 10 'topic_relevant': newest Research Articles (Article type)
    - 10 'archetype_relevant': newest Reviews, Perspectives, Comments, News & Views
    If fewer than 10 in either category, fill from the other.
    """
    research_types = {"Article", "Research", "Letter", "Brief Communication"}
    archetype_types = {"Review Article", "Review", "Perspective", "Comment",
                       "News & Views", "Editorial", "Correspondence", "Analysis"}

    research = []
    archetype = []
    for a in articles:
        atype = a.get("article_type", "")
        doi = a.get("doi", "")
        if not doi:
            continue
        if any(rt.lower() in atype.lower() for rt in research_types):
            research.append(a)
        elif any(at.lower() in atype.lower() for at in archetype_types):
            archetype.append(a)
        else:
            # Default: treat as research
            research.append(a)

    # Sort by date (newest first), use title as tiebreaker
    research.sort(key=lambda x: x.get("date", ""), reverse=True)
    archetype.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Pick 10 from each, fill if needed
    topic_picks = research[:10]
    arch_picks = archetype[:10]

    # Fill shortfalls
    if len(topic_picks) < 10:
        extra = [a for a in archetype[10:] if a not in arch_picks]
        topic_picks += extra[:10 - len(topic_picks)]
    if len(arch_picks) < 10:
        extra = [a for a in research[10:] if a not in topic_picks]
        arch_picks += extra[:10 - len(arch_picks)]

    selected = {
        "topic_relevant": [
            {"doi": a["doi"], "why": f"Auto-selected: newest {a.get('article_type', 'Article')}"}
            for a in topic_picks
        ],
        "archetype_relevant": [
            {"doi": a["doi"], "why": f"Auto-selected: {a.get('article_type', 'Review/Perspective')} for style"}
            for a in arch_picks
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(selected, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)

    total = len(selected["topic_relevant"]) + len(selected["archetype_relevant"])
    print(f"✅ Auto-generated {output_path.name}: {total} articles selected")
    print(f"   → {len(selected['topic_relevant'])} topic-relevant (Research Articles)")
    print(f"   → {len(selected['archetype_relevant'])} archetype-relevant (Reviews/Perspectives)")
    return selected


def main():
    # Auto-detect project root: scripts/ is one level below project root
    base = Path(__file__).resolve().parent.parent
    articles_path = base / "trend_data" / "articles_raw.yaml"
    selected_path = base / "knowledge_base" / "selected_20.yaml"
    output_path = base / "knowledge_base" / "abstracts_20.yaml"

    # ── Pre-flight: check articles_raw.yaml exists ──
    if not articles_path.exists():
        print("❌ ERROR: trend_data/articles_raw.yaml not found!", file=sys.stderr)
        print("   Run scrape_nphoton.py first:", file=sys.stderr)
        print('   python scripts/scrape_nphoton.py --months 6 --output ./trend_data/', file=sys.stderr)
        sys.exit(1)

    # Load articles
    with open(articles_path, "r", encoding="utf-8") as f:
        articles = yaml.safe_load(f)

    if not articles:
        print("❌ ERROR: articles_raw.yaml is empty!", file=sys.stderr)
        sys.exit(1)

    print(f"📄 Loaded {len(articles)} articles from articles_raw.yaml")

    # ── Auto-select if selected_20.yaml is missing ──
    if not selected_path.exists():
        print(f"\n⚠  {selected_path.name} not found — using legacy auto-selection...")
        print(f"   ℹ  For better results, run /polish_abstract Step 2b-2 (AI selection) first.", file=sys.stderr)
        selected = auto_select_20(articles, selected_path)
    else:
        with open(selected_path, "r", encoding="utf-8") as f:
            selected = yaml.safe_load(f)
        print(f"✓ Loaded existing {selected_path.name}")

    target_dois = set()
    for group in ["topic_relevant", "archetype_relevant"]:
        for item in selected.get(group, []):
            doi = item.get("doi", "")
            if doi:
                target_dois.add(doi)

    if not target_dois:
        print("❌ ERROR: No DOIs found in selected_20.yaml!", file=sys.stderr)
        sys.exit(1)

    print(f"🎯 {len(target_dois)} target DOIs loaded")

    # Find matching articles in articles_raw.yaml
    targets = []
    for a in articles:
        if a.get("doi") in target_dois:
            targets.append(a)

    print(f"📋 {len(targets)} articles matched in articles_raw.yaml")

    if not targets:
        print("❌ ERROR: No matching articles found! DOIs in selected_20.yaml don't match articles_raw.yaml.", file=sys.stderr)
        print("   Try deleting selected_20.yaml and re-running to auto-select.", file=sys.stderr)
        sys.exit(1)

    # Fetch abstracts
    session = requests.Session()
    results = []

    for i, a in enumerate(targets):
        title = a["title"][:60]
        url = a.get("url", "")
        doi = a.get("doi", "")
        print(f"\n[{i+1}/{len(targets)}] {title}...")

        # Check if already has full_abstract
        if a.get("full_abstract"):
            abstract_text = a["full_abstract"]
            print(f"  ✓ Already cached ({len(abstract_text)} chars)")
        else:
            abstract_text = fetch_full_abstract(url, session)
            if abstract_text:
                print(f"  ✓ Fetched ({len(abstract_text)} chars)")
                # Also update the main articles_raw.yaml
                a["full_abstract"] = abstract_text
            else:
                print(f"  ✗ Could not fetch")
                abstract_text = a.get("abstract_snippet", "")
            time.sleep(RATE_LIMIT)

        # Split into sentences
        sentences = split_into_sentences(abstract_text) if abstract_text else []

        # Determine which group
        group = "unknown"
        for g in ["topic_relevant", "archetype_relevant"]:
            for item in selected.get(g, []):
                if item.get("doi") == doi:
                    group = g
                    break

        results.append({
            "doi": doi,
            "title": a["title"],
            "url": url,
            "article_type": a.get("article_type", ""),
            "date": a.get("date", ""),
            "group": group,
            "selection_reason": next(
                (item["why"] for g in ["topic_relevant", "archetype_relevant"]
                 for item in selected.get(g, []) if item.get("doi") == doi),
                ""
            ),
            "full_abstract": abstract_text or "",
            "sentences": [
                {"position": f"S{j+1}", "text": s}
                for j, s in enumerate(sentences)
            ],
            "sentence_count": len(sentences),
        })

    # Save structured output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(results, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)
    print(f"\n✓ Saved {len(results)} structured abstracts to {output_path}")

    # Also update articles_raw.yaml with fetched abstracts
    with open(articles_path, "w", encoding="utf-8") as f:
        yaml.dump(articles, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"✓ Updated articles_raw.yaml with new abstracts")

    # Summary
    fetched = sum(1 for r in results if r["full_abstract"])
    failed = len(results) - fetched
    avg_sentences = sum(r["sentence_count"] for r in results) / max(len(results), 1)
    print(f"\n{'='*50}")
    print(f"📊 Summary: {fetched}/{len(results)} abstracts fetched, avg {avg_sentences:.1f} sentences each")
    if failed:
        print(f"⚠  {failed} abstracts could not be fetched (network/paywall)")
    print(f"✅ Output: {output_path}")


if __name__ == "__main__":
    main()
