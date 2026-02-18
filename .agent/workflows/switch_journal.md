---
description: How to adapt the pipeline for different target journals (Nature, Science, PRL, etc.)
---
# Multi-Journal Adaptation Workflow

## Architecture: What Changes vs What Stays

```
                    STAYS THE SAME                    CHANGES PER JOURNAL
                    ─────────────                    ──────────────────
                    extract_semantic_core             scrape_nphoton.py --journal
                    imo_abstract_polish (Moves)       selected_20.yaml (20 articles)
                    cover_letter_generator            abstract_analysis.json (stats)
                    Source Lock                       writing_brief.md (constraints)
                    Red Team                          editorial_dna_fallback.md
```

> The Semantic Core, Move structure, and verification logic are **journal-agnostic**.
> Only the **editorial DNA** (word frequencies, opening/closing patterns, hedging density) changes.

---

## Step 1: Scrape Target Journal

The scraper already supports multiple journals:

```bash
# Nature Photonics (default)
python scripts/scrape_nphoton.py --months 6 --output ./trend_data/ --journal nphoton

# Nature (main journal)
python scripts/scrape_nphoton.py --months 6 --output ./trend_data/ --journal nature

# Nature Communications
python scripts/scrape_nphoton.py --months 6 --output ./trend_data/ --journal ncomms

# Light: Science & Applications
python scripts/scrape_nphoton.py --months 6 --output ./trend_data/ --journal lsa
```

**For journals NOT on nature.com** (Science, PRL, Optica, etc.) — you need to:
1. Manually collect 20 abstracts from the target journal
2. Save them in `knowledge_base/abstracts_20.yaml` in this format:

```yaml
- doi: "10.1126/science.xxx"
  title: "Paper title"
  abstract: "Full abstract text here..."
  type: "Article"
- doi: "..."
  ...
```

// turbo
## Step 2: Select 20 Learning Articles

After scraping, let the AI select 20 representative articles:

```
Use /polish_abstract Step 2b-2 (AI selection)
```

Or manually curate `knowledge_base/selected_20.yaml`:

```yaml
topic_relevant:    # 10 articles in your paper's subfield
  - doi: "10.xxxx/..."
    why: "Directly related to your topic"
  - ...

archetype_relevant:  # 10 well-written articles (Reviews, Articles)
  - doi: "10.xxxx/..."
    why: "Excellent narrative structure"
  - ...
```

> **Key insight**: `topic_relevant` teaches the pipeline WHAT your field talks about.
> `archetype_relevant` teaches HOW the best papers in this journal are written.

// turbo
## Step 3: Fetch Full Abstracts

```bash
python scripts/fetch_learning_abstracts.py
```

This reads `selected_20.yaml`, fetches full abstracts from nature.com, saves to `knowledge_base/abstracts_20.yaml`.

// turbo
## Step 4: Analyze Editorial DNA

```bash
python scripts/analyze_abstracts.py
```

This produces `knowledge_base/abstract_analysis.json` with:
- Verb frequency → which verbs the journal prefers
- Opening patterns → object-first vs problem-first %
- Closing patterns → promise vs summary %
- Hedging density → how cautious the journal is
- Information density → IU per sentence shape
- Sentence statistics → word count distribution

// turbo
## Step 5: Generate Writing Brief

Run `/polish_abstract` Step 2e to convert `abstract_analysis.json` → `writing_brief.md`.

The writing brief automatically adapts to whatever journal's stats are in `abstract_analysis.json`.

---

## Quick Reference: Journal Profiles

| Journal | Opening | Closing | Avg Words | Hedging | Notes |
|:--|:--|:--|:--|:--|:--|
| **Nature Photonics** | 68% object-first | 32% promise | 151±42 | 0.3/sentence | "Here we show/demonstrate" pivot |
| **Nature** | ~60% object-first | ~40% promise | 160±50 | 0.4/sentence | Broader audience → simpler jargon |
| **Science** | ~50% impact-first | ~50% summary | 130±30 | 0.2/sentence | Shorter, more declarative |
| **PRL** | ~70% problem-first | ~30% outlook | 100±20 | 0.3/sentence | Very dense, more equations |
| **Optica** | ~60% object-first | ~35% enabling | 140±35 | 0.3/sentence | Technical precision valued |

> ⚠️ These are rough estimates. **Always run the analyzer** on 20 actual articles from your target journal to get precise stats.

---

## Example: Switching from Nature Photonics → Science

```bash
# 1. Scrape Science articles (manual — Science is not on nature.com)
#    Collect 20 abstracts from science.org and save to abstracts_20.yaml

# 2. Run analyzer
python scripts/analyze_abstracts.py

# 3. Generate new writing brief
#    Run /polish_abstract Step 2e

# 4. Run abstract pipeline as normal
#    The pipeline will automatically use the new writing_brief.md constraints
```

That's it. The Move structure (M1-M6) stays the same — only the word budgets, verb choices, and hedging targets change automatically.

---

## Adding a New Journal to the Scraper

If you want automated scraping for a new Nature sub-journal, add it to `scrape_nphoton.py` line 39:

```python
JOURNAL_PATHS = {
    "nphoton": "/nphoton",           # Nature Photonics
    "ncomms": "/ncomms",             # Nature Communications
    "nature": "/nature",             # Nature
    "lsa": "/lsa",                   # Light: Science & Applications
    # Add new journals here:
    "nphys": "/nphys",               # Nature Physics
    "nmat": "/nmat",                 # Nature Materials
    "nnano": "/nnano",               # Nature Nanotechnology
}
```

For non-Springer/Nature journals (Science, ACS, Optica), you'll need a different scraper or manual collection.
