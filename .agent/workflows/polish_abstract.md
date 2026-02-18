---
description: IMO-style iterative abstract generation with solver-verifier loop
---

# IMO-style Abstract Polishing Workflow

**Goal**: Transform a technical draft into a high-impact narrative (e.g., Nature Photonics standard) using a "Solver-Verifier" architecture.

// turbo-all

## Step 0: Extract Original Abstract

**Objective**: Isolate the abstract from the manuscript for polishing.


1. Read the manuscript file and locate the `## Abstract` section
2. Copy the abstract text **verbatim** (no edits) into `draft_abstract.md`
3. Record the word count of the original abstract

> [!CAUTION]
> You **MUST** use the `write_to_file` tool to save `draft_abstract.md`.
> This file is required by:
> - Step 2e (Source Lock baseline)
> - Step 4 (5-gram overlap check in Verifier)
> - Step 5c (Diff Analysis)
> If this file doesn't exist, those steps will fail.

---

## Step 1: Semantic Compression (The Ground Truth)

**Objective**: Build the hallucination-proof foundation.


> [!IMPORTANT]
> Apply the **`extract_semantic_core`** skill (`.agent/skills/extract_semantic_core/SKILL.md`).
> Read the skill file first, then follow its instructions exactly.

**Input**: The full manuscript file.
**Output**: `manuscript_semantic_core.md` (must be saved as a file — the skill enforces this).

**Verification**: Confirm the output contains:
- [ ] `## 1. Fact Base` with ★★★/★★/★ priorities and at least one fact per Results paragraph
- [ ] `## 2. Logic Graph` with Gap, Mechanism, Key Result, Impact, Novelty
- [ ] `## 3. Claims Inventory` with strength ratings (STRONG/MODERATE/WEAK)

If any section is incomplete, re-run the skill before proceeding.

---

## Step 2: Editorial DNA (The Target)

**Objective**: Load or build the journal's "Hidden Curriculum".

### 2a: Check for existing brief

Look for `writing_brief.md` in the **project root directory** (use file search to verify — do NOT assume).

**If `writing_brief.md` EXISTS** → Read it and extract:
- **Golden Sequence**: The move-by-move structure (e.g., Promise → Gap → "Here we" → Mechanism → Result → Impact)
- **Anti-Patterns**: What NOT to do (e.g., "Don't start with the problem")
- **Power Vocabulary**: Journal-preferred terms and framing

**If `writing_brief.md` does NOT exist** → Generate it with the full Retriever pipeline:

### 2b: Auto-run Trend Scraping Pipeline

**Pre-flight: Conda environment check**

// turbo
**Step 2b-0**: Verify the `fifm` conda environment exists:

```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" env list | Select-String "fifm"
```

> [!CAUTION]
> **If this command fails or `fifm` is not listed → STOP the workflow immediately.**
> Report this error to the user:
> ```
> ❌ Python environment not found: conda env 'fifm' is required but not detected.
>    Please set up the environment using Antigravity:
>    "Help me create a conda environment called fifm with packages: requests, beautifulsoup4, pyyaml, lxml"
> ```
> **Do NOT proceed to Step 2b-1. Do NOT fall back to the template.**
> The user must fix the environment first.

// turbo
**Step 2b-1**: Run `scrape_nphoton.py` to scrape journal TOC and analyze trends:


```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" run -n fifm python scripts/scrape_nphoton.py --months 6 --output ./trend_data/
```

This produces: `trend_data/articles_raw.yaml` (all article metadata) + `trend_data/trend_report.md` (keyword trends, framing patterns, editorial signals).

**Step 2b-2**: **AI selects 20 most relevant articles** for learning.


> [!IMPORTANT]
> This step is performed by the AI, NOT by a script. The AI must read the manuscript and the scraped articles, then make an intelligent selection.

> [!CAUTION]
> **Corpus Re-selection Guard**: If the manuscript has changed since the last run (different paper, different topic), you **MUST** re-run this selection step. Do NOT reuse a `selected_20.yaml` built for a different manuscript — topic alignment will be wrong and the brief will be noisy.
> Compare the manuscript title/keywords against existing `selected_20.yaml` entries. If <50% overlap → re-select.

1. **Read** `manuscript_semantic_core.md` — extract the paper's core topics, methods, and keywords (e.g., TERS, adaptive optics, near-field, wavefront shaping, MoSSe)
2. **Read** `trend_data/articles_raw.yaml` — scan all scraped article titles. For each article, check:
   - Does the title/abstract contain related keywords?
   - Is the article type useful for learning writing patterns?
3. **Select 20 articles** in two groups:
   - **10 topic-relevant**: Articles closest to the manuscript's subject matter (same techniques, materials, applications). These teach domain-specific vocabulary and result framing.
   - **10 archetype-relevant**: High-quality Reviews, Perspectives, or Articles from adjacent fields. These teach narrative structure, opening hooks, and impact framing — even if the topic differs.
4. **Save** the selection to `knowledge_base/selected_20.yaml` in this format:

```yaml
topic_relevant:
  - doi: "10.1038/s41566-..."
    why: "Uses adaptive optics for nanoscale spectroscopy — directly related technique"
  # ... 10 entries

archetype_relevant:
  - doi: "10.1038/s41566-..."
    why: "Review article with excellent Hook→Gap→Impact structure"
  # ... 10 entries
```

> [!CAUTION]
> **Selection criteria**:
> - Prefer articles from the **same journal** as the target (Nature Photonics)
> - For topic-relevant: prioritize keyword overlap with manuscript (TERS, sSNOM, AO, plasmonics, near-field, tip-enhanced, Zernike, MoSSe, 2D materials)
> - For archetype-relevant: prioritize articles with clear, well-structured abstracts regardless of topic

// turbo
**Step 2b-3**: Run `fetch_learning_abstracts.py` to fetch full abstracts of the 20 selected articles:


```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" run -n fifm python scripts/fetch_learning_abstracts.py
```

This produces: `knowledge_base/abstracts_20.yaml` (20 full abstracts structured for Move analysis).

> [!WARNING]
> If the fetch script fails (network error, missing packages), skip to **Step 2d** (fallback template).
> The auto-select function inside the script is a **legacy fallback only** — the AI selection in Step 2b-2 is the preferred path.

// turbo
**Step 2b-4**: Run `analyze_abstracts.py` to produce **programmatic statistics** from the fetched abstracts:


```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" run -n fifm python scripts/analyze_abstracts.py
```

This produces: `knowledge_base/abstract_analysis.json` — machine-verified verb counts, n-gram frequencies, sentence statistics, opening/closing pattern classification, and topic alignment score.

> [!IMPORTANT]
> This script replaces LLM estimation with exact, reproducible metrics.
> All counts in `abstract_analysis.json` are regex-based — not LLM guesses.

### 2c: Generate `writing_brief.md` (2-Tier: Data-Driven + AI-Interpreted)

**This step combines script output with AI interpretation to produce a high-signal writing brief.**

> [!CAUTION]
> **Rule**: Never override script numbers with your own estimates.
> If the script says "demonstrate" appears 5 times, write **5** — not your impression of "about 12".

**Inputs** (read all three):
1. `knowledge_base/abstract_analysis.json` — **exact statistics** from Step 2b-4
2. `trend_data/trend_report.md` — editorial signals, trending keywords
3. `knowledge_base/abstracts_20.yaml` — raw abstracts (for AI interpretation only)

**Generate `writing_brief.md`** using this 2-tier template:

```markdown
# Writing Brief — [Journal Name]
> Auto-generated on [date] | Data: [N] abstracts | Script: analyze_abstracts.py v1.0

---

## §1 — Exact Statistics ⚙️ [DATA-DRIVEN]
> Source: `abstract_analysis.json` — all numbers are script-verified, not estimated.

### Verb Frequency (exact regex counts)
| Rank | Verb | Count (n=N) | Signal |
|:--|:--|:--|:--|
[Copy top 10 verbs from abstract_analysis.json → verb_frequency]

### "Here we" Pivot
- [X]% of abstracts contain "Here we" (N/N)
- Most common verb after "Here we": [verb] ([count])
[Copy from abstract_analysis.json → here_we_pivot]

### Sentence Statistics
| Metric | Value |
|:--|:--|
| Mean word count | [X] ± [std] |
| Median word count | [X] |
| Range | [min]–[max] |
| Mean sentences | [X] |
| Words per sentence | [X] |
[Copy from abstract_analysis.json → sentence_statistics]

### Opening & Closing Patterns (regex-classified)
**Opening**: [distribution from abstract_analysis.json → opening_patterns]
**Closing**: [distribution from abstract_analysis.json → closing_patterns]

### Domain Terminology (top n-grams)
**Bigrams**: [top 10 from abstract_analysis.json → domain_terminology.bigrams]
**Trigrams**: [top 5 from abstract_analysis.json → domain_terminology.trigrams]

---

## §2 — Topic Alignment Score ⚙️ [DATA-DRIVEN]
> Source: `abstract_analysis.json` — TF-IDF overlap between manuscript keywords and abstract corpus.

**Overall alignment**: [X]%

| Manuscript Keyword | Coverage | Total Mentions | TF-IDF |
|:--|:--|:--|:--|
[Copy from abstract_analysis.json → topic_alignment.keyword_detail]

**Interpretation**: [AI interprets what high/low alignment means for framing strategy]

---

## §3 — Editorial Signals 📡 [DATA-DRIVEN]
> Source: `trend_report.md` — information LLM training data does NOT contain.

### Trending Keywords (Sep 2025 – Feb 2026)
[Copy relevant trending keywords from trend_report.md]

### N&V / Editorial Signals
[Copy relevant News & Views and editorial themes from trend_report.md]

### Alignment Opportunities
[AI identifies where manuscript theme intersects with editorial priorities]

---

## §3b — Discourse Statistics 🔬 [DATA-DRIVEN]
> Source: `abstract_analysis.json` — discourse_hedging, discourse_info_density, discourse_domain_shift sections.

### Hedging Density
- **Corpus mean**: [X] hedges/sentence
- **Category breakdown**: [copy from abstract_analysis.json → discourse_hedging.category_totals]
- **Target for Solver**: Match corpus hedging density. Use ≥1 hedge in closing half (e.g., "able to", "permitting", "promising").

### Information Density Profile
- **Corpus mean**: [X] IU/sentence
- **Max IU observed**: [X]
- **Shape distribution**: [copy from abstract_analysis.json → discourse_info_density.shape_distribution]
- **Target for Solver**: Bell-shaped density curve. No sentence >6 IU. Peak at mechanism sentence.

### Domain-Shift Markers
- **Corpus frequency**: [X]% of abstracts use domain-shift markers
- **Target for Solver**: If manuscript has fundamental+applied results, use a domain-shift marker sentence.

---

## §4 — Golden Sequence 🧠 [AI-INTERPRETED]
> Source: AI analysis of raw abstracts. These are interpretive observations, not exact counts.

### Move Sequence
[AI tags sentences in the abstracts and identifies the dominant narrative arc]
M1 (Context) → M2 (Gap) → M3 ("Here we") → M4 (Mechanism+Result) → M5 (Impact)

### Framing Nuances
[AI observations about HOW the best abstracts handle transitions, emphasis, and pacing]

> [!IMPORTANT]
> **Enabling-not-Avoiding Principle**: When describing an advantage of the technique, frame it as **enabling** a new capability rather than merely **avoiding** a problem.
> - ❌ "immune to fluorescence" (describes absence)
> - ✅ "naturally supporting simultaneous fluorescence detection" (describes enabled capability)
> Apply this to every advantage mentioned in the abstract.

---

## §5 — Solver Constraints 🎯 [MERGED RULES]

1. **Must open object-first** ([X]% per script — dominant pattern)
2. **Must include "Here we [verb]"** — prefer top verb from §1 verb frequency
3. **Must include ≥2 quantitative results** from Fact Base (★★★ facts)
4. **Must close with [dominant closing type]** ([X]% per script). If the dominant type is "promise", use forward-looking language ("promising", "paving the way", "opening new avenues") — do NOT substitute assertive present-tense claims ("provides", "establishes") which belong to the "paradigm" closing type.
5. **Target**: [mean]±[std] words, [mean] sentences (from §1 statistics)
6. **Use domain terms from §1** n-gram list; avoid terms absent from corpus
7. **Lean into §3 trending keywords** where they naturally fit the manuscript
8. **M1 and M2 MUST be separate sentences with concession rhetoric** — Context ≠ Gap. M2 should FIRST acknowledge the incumbent's value ("While still serving as…" / "Although X enables Y…"), THEN pivot to the limitation ("…it suffers from…"). This concession-then-limitation pattern builds credibility before tension. Do NOT write M2 as a blunt negative ("No existing technique…").
9. **Standalone Impact Sentence**: The single most impressive quantitative result (typically the headline achievement, e.g. ">100× speed") **must get its own dedicated sentence** — do NOT bury it inside a multi-result compound sentence.
10. **Frame advantages as enabling OR supporting** (from §4 Enabling-not-Avoiding Principle) — when an advantage opens a genuinely new capability, use "enabling" framing. But when the advantage is a natural property of the technique (not an explicit design goal), use "naturally supporting" or "permitting" — do NOT force every advantage into an enabling claim.
11. **Follow Golden Sequence** from §4
12. **M3 pivot must lead with OUTCOMES first** — at Nature level, the "Here we report" sentence should immediately tell the reader WHAT the technique achieves (outcome + speed + key advantage), then a SEPARATE sentence (M3b) explains HOW (mechanism). Do NOT front-load technical mechanism in the pivot sentence.
13. **Domain-shift marker**: If the manuscript has BOTH fundamental AND clinical/applied results, they MUST be in separate sentences. The application sentence should open with a domain-shift marker ("As a medical application," / "For clinical validation,"). Do NOT pack fundamental and clinical results into the same sentence.
```

> [!CAUTION]
> You **MUST** use the `write_to_file` tool to save `writing_brief.md` **to the project root**.
> This file is the **direct input** to the Solver in Step 3. Do NOT just print the analysis in chat.

**After generating**: Read `writing_brief.md` and extract all 6 dimensions for use in Step 3.

### 2d: Fallback (if scripts fail or no abstracts available)

1. Ask user: **"Target journal?"** (default: Nature Photonics)
2. Based on journal name, apply built-in Golden Sequence template:

| Journal | Golden Sequence |
|:--|:--|
| Nature / Nature Photonics | Context Hook → Gap → "Here we show" → Mechanism → Key Result → Broader Impact |
| ACS Nano / Nano Letters | Problem → Significance → Method → Key Finding → Application |
| Physical Review Letters | Physics Question → Approach → Key Result → Implications |
| Advanced Materials | Challenge → Strategy → "Herein" → Method → Performance → Outlook |

3. Anti-Patterns (universal): ❌ Don't start with problem statement. ❌ Don't use >2 acronyms. ❌ Don't list methods before results.
4. Generate a minimal `editorial_dna_fallback.md` (≤500 tokens) and save it.

**Output**: `writing_brief.md` (from learning pipeline) or `editorial_dna_fallback.md` (from template).

---

## Step 2e: Data Washing (Token Budget & Source Lock)

**Objective**: Ensure the Solver rebuilds from Fact Base, not paraphrases the original abstract.

> [!CAUTION]
> This step prevents the #1 failure mode: AI copying the original abstract's phrasing instead of generating fresh prose from structured facts.

1. **Set Token Budget**: Hard cap at **180 words** for the abstract (adjust per journal requirements).

2. **Allocate Moves**:

| Move | Word Budget | Source (generate from) |
|:--|:--|:--|
| Hook (1-2 sentences) | ~30 words | Logic Graph: Gap + Impact |
| "Here we" (1 sentence) | ~25 words | Logic Graph: Mechanism — OUTCOMES first, mechanism second |
| Mechanism (1-2 sentences) | ~40 words | ★★★ facts from Fact Base |
| Key Result (1 sentence) | ~25 words | ★★★ facts — STANDALONE headline number |
| Application Result (1 sentence) | ~30 words | ★★★ facts with clinical/applied context — open with domain-shift marker |
| Impact (1 sentence) | ~30 words | Logic Graph: Impact + Novelty — use promise/hedge language |

3. **Source Lock Rules** (enforced in BOTH Solver and Verifier):
   - Solver may ONLY read `manuscript_semantic_core.md` and the Editorial DNA (`writing_brief.md` or `editorial_dna_fallback.md`). **Do NOT read the original manuscript's Abstract during generation.**
   - `draft_abstract.md` is used ONLY by the Verifier for 5-gram overlap checking — NOT by the Solver for generation.
   - Each Move may contain at most **1 technical term/acronym**. If a Move has >1 term, keep only the most essential one.
   - Numbers must come directly from Fact Base with the same precision (e.g., "173 nm" not "~170 nm").

---

## Step 3 + 4: Move-by-Move Solver-Verifier Loop

**Objective**: Generate abstract one sentence at a time, with per-Move verification and Theme-Rheme chaining.

> [!IMPORTANT]
> Apply the **`imo_abstract_polish`** skill (`.agent/skills/imo_abstract_polish/SKILL.md`) — **v3.0.0 Move-by-Move architecture**.
> Read the skill file first, then follow its instructions exactly.

**Inputs** (pass to the skill):
- `manuscript_semantic_core.md` from Step 1
- `writing_brief.md` or `editorial_dna_fallback.md` from Step 2
- The **Data Washing** constraints from **Step 2e** (token budget + source lock)
- `draft_abstract.md` from Step 0 (for Verifier's 5-gram overlap check ONLY — NOT for Solver generation)

The skill will:
1. Generate 7 Moves sequentially (M1 Context → M2 Gap → M3 Pivot → M3b Mechanism → M4 Key Result → M5 Application → M6 Impact)
2. For each Move: produce 2 candidates, micro-verify, select winner, extract Rheme for next Move
3. Assemble all winners → smoothing pass → global 5-dim scoring
4. Iterate (re-generate failing Moves) until score ≥ 8.0 AND Coverage ≥ 7
5. Save `abstract_candidates.md` and `abstract_scoring_matrix.md`

**Verification**: Confirm BOTH output files exist and contain:
- [ ] A **Move Workbench** table showing all 7 Moves with winner selections and Theme-Rheme chains
- [ ] A **Smoothing Log** showing only connective/article changes (no factual changes)
- [ ] A scoring matrix with per-dimension rationales (5 dimensions)
- [ ] **Theme-Rheme chain score** ≥5/6 pairs
- [ ] **Information density** shape = bell (no sentence >6 IU)
- [ ] **Hedge density** ≥1 hedge in closing half (M4–M6)
- [ ] A **Source Lock table** (5-gram overlap): max n-gram < 6 words
- [ ] A winning assembled abstract marked with 🏆
- [ ] An iteration log showing which Moves were revised
- [ ] No WEAK claims from Claims Inventory used unqualified

---

## Step 5: Assembly, Polish & Safety Checks

**Objective**: Final quality pass on the winning abstract.

### 5a: Fact & Flow Check

1. Read the 🏆 winner from `abstract_candidates.md`
2. **Fact Check**: Cross-reference EVERY number against `manuscript_semantic_core.md`
   - If any number is wrong or missing → fix it
   - All ★★★ facts must be present
3. **Flow Check**: Read the abstract aloud (mentally). Are transitions smooth?
4. **Word Count**: Must be ≤ 200 words (or per journal requirement)
5. **Golden Sequence Check**: Does it follow the sequence from Step 2?
6. **Linguistic Polish**: Apply journal-specific vocabulary

### 5b: Editorial Red Flag Checklist

Answer each question. If **ANY** answer is YES → revise the abstract before finalizing.

| # | Red Flag | YES/NO | Fix |
|:--|:--|:--|:--|
| RF1 | Does the Title promise "quantitative" / "novel" but the paper lacks calibration / prior art comparison? | __ | Soften title or add qualification in abstract |
| RF2 | Does the abstract claim "first" without citing closest prior work? | __ | Add "to our knowledge" or remove |
| RF3 | Does it claim "generalizable" / "universal" with only one demonstration? | __ | Qualify: "potentially generalizable" or remove |
| RF4 | Does it use "novel" / "unique" more than once? | __ | Replace with specific descriptors |
| RF5 | Word count > journal limit? | __ | Cut the longest Move |
| RF6 | Are there > 2 technical acronyms? | __ | Spell out or remove least essential |
| RF7 | Any WEAK claim from Claims Inventory used without qualification? | __ | Soften or remove |

### 5c: Diff Analysis

Generate a comparison between the **original abstract** (`draft_abstract.md`) and the **winning abstract**:

```markdown
## Original vs Polished Abstract

### Key Changes
- **Word count**: [original] → [polished] words
- **Framing**: [original framing] → [new framing]
- **Added facts**: [list facts added, e.g., F5: >60-fold sSNOM]
- **Removed jargon**: [list terms removed or simplified]
- **Softened claims**: [list claims qualified]
- **Structure**: [original sequence] → [Golden Sequence]
```

Append this to `abstract_candidates.md`.

### 5d: Title Check (W5)

**Objective**: Detect mismatches between the paper title's promises and the abstract's claims.

1. Read the manuscript **title** and extract all "strong signal" words:
   - Look for: "quantitative", "deterministic", "novel", "universal", "first", "generalizable", "breakthrough"
2. For each signal word found in the title, check the abstract:

| Title word | In abstract? | How is it handled? | Risk |
|:--|:--|:--|:--|
| [word] | YES/NO | exact / hedged / avoided | 🔴 HIGH / 🟡 MEDIUM / 🟢 OK |

3. **If any 🔴 HIGH risk** (title promises X, abstract contradicts or avoids X entirely):
   - Generate a **co-author advisory note** appended to `abstract_candidates.md`:
   ```
   ⚠️ TITLE-ABSTRACT MISMATCH
   The title claims "[word]" but the abstract [hedges/avoids] it.
   Options: (a) Soften the title, (b) Strengthen the evidence, (c) Add qualification in abstract.
   ```

4. **If all 🟢 OK**: No action needed.

**Output**: Updated `abstract_candidates.md` with final polished version + diff analysis + title check (if applicable).

### 5e: LaTeX Conversion (Submission-Ready)

**Objective**: Produce a plain-text version for submission systems that don't render LaTeX.

1. Copy the winning abstract
2. Replace all `$...$` LaTeX notation with plain-text equivalents:
   - `$E_z$` → `E_z`
   - `$A_1^1$` → `A₁¹` or `A_1^1`
   - Greek: `$\lambda$` → `λ`
3. Save as `abstract_plain.txt` (plain text, no markdown)

### 5f: Blind Co-author Review

**Objective**: Present variants without labels for unbiased co-author feedback.

1. Create `abstract_blind_review.md` containing **only** the 3 variant texts
2. Label them **Abstract 1, 2, 3** (randomly shuffled, NOT matching A/B/C order)
3. Include a " mapping key" at the end (collapsed/hidden) for the workflow operator
4. Ask co-authors: "Which abstract do you prefer and why?"

> [!TIP]
> This step is optional for solo authors. Skip if no co-author review is needed.

---

## Final Verification Checklist

Before marking the workflow as complete, confirm:

- [ ] `draft_abstract.md` exists (Step 0)
- [ ] `manuscript_semantic_core.md` exists with ★★★ priorities (Step 1)
- [ ] `writing_brief.md` OR `editorial_dna_fallback.md` exists (Step 2)
- [ ] 3 abstract variants with **different structures** (W1) (Steps 3-4)
- [ ] 5-dimension scoring with per-dimension rationale (Step 4)
- [ ] ★★★ facts present in all variants
- [ ] No WEAK claims used unqualified (Claim Safety)
- [ ] **Hedge Diversity** (W2): each variant uses different hedges for MODERATE claims
- [ ] **5-gram overlap check** (W4): max shared n-gram < 6 words for all variants
- [ ] Red Flag checklist completed (Step 5b)
- [ ] Diff Analysis generated (Step 5c)
- [ ] **Title Check** (W5): no 🔴 mismatches, or advisory note generated (Step 5d)
- [ ] **LaTeX converted** to plain text if needed (Step 5e)
- [ ] `abstract_candidates.md` saved
- [ ] `abstract_scoring_matrix.md` saved

---

## Step 6: Output Summary

Final deliverables:
- `manuscript_semantic_core.md` — the ground truth (from Step 1)
- `abstract_candidates.md` — 3 variants + 🏆 winning polished abstract + diff analysis
- `abstract_scoring_matrix.md` — full scoring breakdown (5 dimensions) with rationales

// turbo
## Completion Notification

When ALL steps above are finished, notify the user:

**"✅ Abstract polishing complete. Please review `abstract_candidates.md` and `abstract_scoring_matrix.md`."**
