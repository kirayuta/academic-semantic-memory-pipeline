# Academic Semantic Memory Pipeline

An AI-powered academic writing toolkit that generates Nature-tier abstracts and cover letters from raw manuscripts. Built on a **Move-by-Move Solver-Verifier architecture** inspired by IMO math problem solvers — each sentence is generated independently, micro-verified, and chained via Theme-Rheme flow control.

> **Validated**: Pipeline independently reproduced a published Nature Photonics abstract **word-for-word** from manuscript text alone, without seeing the original abstract.

## Requirements

- [Antigravity](https://www.antigravity.dev/) (VS Code AI agent)
- Python 3.10+ with `requests`, `beautifulsoup4`, `pyyaml`

```bash
pip install requests beautifulsoup4 pyyaml
```

## Quick Start (3 Steps)

### 1. Prepare your manuscript

Save your manuscript as a `.md` file in the project root. Include all sections (Introduction, Methods, Results, Discussion). The abstract can be a rough draft or even empty — the pipeline will generate one from scratch.

### 2. Scrape target journal editorial DNA

```bash
# Scrape recent articles from your target journal
python scripts/scrape_nphoton.py --months 6 --output ./trend_data/ --journal nphoton

# Fetch full abstracts for 20 selected articles
python scripts/fetch_learning_abstracts.py

# Analyze editorial patterns (verb frequency, opening/closing types, hedging)
python scripts/analyze_abstracts.py
```

Supported journals: `nphoton` · `nature` · `ncomms` · `nphys` · `nmat` · `nnano` · `nmeth` · `nchem` · `natelectron` · `lsa`

### 3. Run the pipeline

Use the `/polish_abstract` workflow in Antigravity. It will:
1. Extract a **Semantic Core** (facts, logic graph, claims) from your manuscript
2. Generate a **Writing Brief** from the journal's editorial DNA
3. Run the **Move-by-Move Solver** (7 Moves, Best-of-4 candidates per Move)
4. Verify with **5-dimension scoring** + **Source Lock** + **Adversarial Red Team**
5. Output `abstract_candidates.md` and `abstract_scoring_matrix.md`

For cover letters: use the `cover_letter_generator` skill after generating an abstract.

## Architecture

```
Your Manuscript
      │
      ▼
┌─────────────┐     ┌──────────────┐
│  Semantic    │     │  Scraper +   │
│  Core        │     │  Analyzer    │
│  (Facts,     │     │  (Editorial  │
│   Logic,     │     │   DNA)       │
│   Claims)    │     │              │
└──────┬───────┘     └──────┬───────┘
       │                    │
       ▼                    ▼
┌──────────────────────────────────┐
│  Move-by-Move Solver (Best-of-4)│
│  M1→M2→M3→M3b→M4→M5→M6        │
│  Each: 4 candidates → verify →  │
│        rank → select → chain    │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Global Verifier                 │
│  5-dim scoring + Source Lock     │
│  + Theme-Rheme chain check      │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Adversarial Red Team            │
│  "As a Nature reviewer, attack   │
│   the weakest sentence"          │
└──────────────┬───────────────────┘
               │
               ▼
         Nature-tier Abstract
```

## Project Structure

```
.agent/
├── skills/
│   ├── extract_semantic_core/    # Manuscript → Fact Base + Logic Graph
│   ├── imo_abstract_polish/      # Move-by-Move abstract generator (v4.0)
│   ├── cover_letter_generator/   # 5-Move cover letter generator
│   ├── academic-reviewer/        # PhD advisor-style manuscript review
│   ├── academic-writer/          # IMRaD + scientific prose standards
│   ├── academic-editor/          # Physics-aware editing layers
│   ├── academic-analyst/         # Experimental physics analysis
│   ├── academic-interviewer/     # Socratic defense preparation
│   └── manuscript-preprocessor/  # Chunk manuscripts for review
├── workflows/
│   ├── polish_abstract.md        # Main abstract polishing pipeline
│   ├── research.md               # Full manuscript review pipeline
│   ├── story.md                  # Narrative reframing with journal trends
│   ├── switch_journal.md         # Multi-journal adaptation guide
│   └── imo.md                    # IMO math solving pipeline
scripts/
├── scrape_nphoton.py             # Journal TOC scraper (10 Nature journals)
├── fetch_learning_abstracts.py   # Full abstract fetcher
└── analyze_abstracts.py          # NLP editorial DNA analyzer
```

## Key Features

| Feature | What it does |
|:--|:--|
| **Semantic Core** | Compresses manuscript into facts + logic graph — prevents AI hallucination |
| **Move-by-Move** | Generates each sentence independently with micro-verification |
| **Best-of-4** | 4 candidates per sentence, ranked by checks passed + conciseness |
| **Theme-Rheme** | Enforces information flow between sentences (100% chain score) |
| **Source Lock** | Ensures output is original — no 5-gram overlap with input abstract |
| **Red Team** | AI attacks its own output as a hostile reviewer, fixes weaknesses |
| **Loop Closure** | Final sentence echoes opening keywords for narrative satisfaction |
| **Multi-journal** | Switch target journal by re-running scraper + analyzer |

## Workflows

| Command | Purpose |
|:--|:--|
| `/polish_abstract` | Full abstract generation pipeline |
| `/research` | Complete manuscript review (chunked, iterative) |
| `/story` | Reframe narrative using journal trend data |
| `/switch_journal` | Adapt pipeline for a different journal |

## License

MIT
