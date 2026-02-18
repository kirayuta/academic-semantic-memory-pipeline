---
description: Reframe manuscript narrative using journal trend data and writing templates
---

# /story — Manuscript Story Engineering Workflow v1.0

This workflow takes a **polished manuscript** (output of `/research`) and **reframes its narrative** to align with current journal editorial trends. It changes the **story**, not the data.

// turbo-all

## How to Use

The user provides:
- **A polished manuscript** (e.g., `final_manuscript.md` from `/research`)
- **A trend report** (e.g., `trend_data/trend_report.md` from `scrape_nphoton.py`)
- Optionally: `writing_template.md` for house style reference

---

## Step 0: Pre-flight — Auto-generate Trend Data (if needed)

**Goal**: Ensure `trend_data/trend_report.md` and `knowledge_base/abstracts_20.yaml` exist before starting.

1. Check if `trend_data/trend_report.md` exists (use file search — do NOT assume).

**If it does NOT exist** → Run both scripts:

**Pre-flight: Conda environment check**

// turbo
**Step 0-pre**: Verify the `fifm` conda environment exists:

```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" env list | Select-String "fifm"
```

> [!CAUTION]
> **If `fifm` is not found → STOP and report:**
> `❌ conda env 'fifm' not detected. Ask Antigravity: "Help me create a conda env called fifm with requests, beautifulsoup4, pyyaml, lxml"`

// turbo
**Step 0a**: Scrape journal TOC and generate trend report:

```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" run -n fifm python scripts/scrape_nphoton.py --months 6 --output ./trend_data/
```

// turbo
**Step 0b**: Fetch full abstracts for learning:

```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" run -n fifm python scripts/fetch_learning_abstracts.py
```

**If both files already exist** → Check if `writing_brief.md` also exists. If yes → Skip to Step 1.

**Step 0c**: If `writing_brief.md` does NOT exist, generate it by analyzing the 20 abstracts:

1. **Read** `knowledge_base/abstracts_20.yaml` (20 full abstracts)
2. **Read** `trend_data/trend_report.md` (editorial signals + keyword trends)
3. **Analyze** all 20 abstracts across **6 dimensions**:
   - **a) Golden Sequence**: Tag each sentence's "move" (Hook → Gap → "Here we" → Mechanism → Key Result → Impact). Count the most common sequence.
   - **b) Power Verbs**: Extract main-clause verbs, classify by signal strength (🔥 strong / ⚡ medium / 😴 weak). Top 15.
   - **c) Domain Terminology**: Extract recurring 2-3 word noun phrases (e.g., "enhancement factor"). Top 20.
   - **d) Framing Pattern**: Classify opening sentence type (Context / Question / Bold claim / Problem) and closing sentence type (Paradigm shift / Impact / Application / Quantitative recap). Count %.
   - **e) Anti-Patterns**: What the top abstracts do NOT do (problem-first %, passive voice %, >2 acronyms %, "novel"/"unique" usage %).
   - **f) Sentence Statistics**: Average word count, sentences, words/sentence, quantitative values per abstract.
4. **Save** to `writing_brief.md` (see `/polish_abstract` Step 2c for full template)

> [!CAUTION]
> You MUST save `writing_brief.md` using `write_to_file`. This file is consumed by Step 1.3's Gap Analysis.

> [!WARNING]
> If scripts fail (network error, missing `pip` packages), notify the user and proceed with whatever data is available.

---

## Step 1: Landscape Scan

**Goal**: Understand where this manuscript sits relative to current journal trends.

1. Read `final_manuscript.md` → Extract:
   - Core claims (list of 3-5 main findings)
   - Current keywords used in Title + Abstract
   - Current framing angle (what "story" is the manuscript telling?)

2. Read `trend_report.md` → Extract:
   - Top trending keywords (rising / new)
   - Editorial signals and themes
   - Framing patterns (problem-first vs result-first distribution)

3. **Gap Analysis**:
   - **First, check if `writing_brief.md` exists** in the project directory or `trend_data/` folder. Use a file search or directory listing to verify — do NOT assume it doesn't exist.
   - **If `writing_brief.md` EXISTS** → You MUST read its "Diagnostic" section. This contains pre-calculated gaps based on 20 recent abstracts. Use this data directly.
   - **ONLY if `writing_brief.md` does NOT exist** → perform manual gap analysis:
     - Which trending keywords are **absent** from the manuscript but relevant?
     - Which of the manuscript's claims align with editorial themes?
     - Is the current framing pattern aligned with what the journal publishes?

4. **Competitive Positioning**:
   - Check `writing_brief.md` for "Rewrite Options" (A/B/C) to identify potential angles.
   - Identify the **white space** — what angle is NOT covered by recent publications?

**Output**: `landscape_analysis.md` containing:
```yaml
current_framing:
  story: "[one-sentence summary of current narrative]"
  keywords: [list of current keywords]
  framing_pattern: "result-first / problem-first / etc."

trending_alignment:
  matching_keywords: [keywords present in both manuscript and trends]
  missing_keywords: [trending keywords absent from manuscript but relevant]
  editorial_themes: [relevant themes from editorials]

competitive_position:
  similar_recent: 
    - title: "..."
      our_advantage: "..."
  white_space: "[angle not covered by recent papers]"

proposed_angles:
  - angle_name: "Angle A: [name]"
    one_liner: "[one sentence pitch]"
    keywords_to_add: [list]
    sections_to_modify: [Title, Abstract, Intro ¶4, Discussion ¶1-2]
    risk: "LOW / MED / HIGH (risk of overclaiming)"
  - angle_name: "Angle B: [name]"
    ...
  - angle_name: "Angle C: [name]"
    ...
```

> **Important**: Proposed angles MUST be supportable by existing data. No overclaiming.

**Action**: Present `landscape_analysis.md` to user. **PAUSE for user selection.**

---

## Step 2: Story Selection

**Goal**: User picks one framing angle (or provides feedback to refine).

The user will either:
- Select Angle A, B, or C
- Request a hybrid of multiple angles
- Provide their own direction

**Action**: Confirm selected angle. Proceed to rewrite.

---

## Step 3: Targeted Rewrite

**Goal**: Rewrite ONLY the narrative-critical sections. Data sections are untouched.

> [!IMPORTANT]
> For rewriting, apply the **`academic_writer`** skill (`.agent/skills/academic-writer/SKILL.md`) for prose generation,
> then the **`academic_editor`** skill (`.agent/skills/academic-editor/SKILL.md`) for the 6-layer editing pass.
> Read both skill files before rewriting.

Read `writing_template.md` for house style reference (if available).

### Sections to Rewrite

| Section | What changes | Constraint |
|:--|:--|:--|
| **Title** | Align with selected angle + trending keywords | Max 15 words |
| **Abstract** | Restructure to WHY→WHAT→HOW→SO WHAT | Max 200 words, must match data |
| **Introduction ¶4** | "Here we show..." must match new Abstract | Must align with Intro ¶1-3 |
| **Discussion ¶1-2** | Significance reframed for selected angle | No new data claims |

### Sections NOT Modified
- Results (data is data)
- Methods (protocols don't change)
- Figures and captions
- References
- Discussion ¶3-4 (Limitations + Future directions — unchanged unless user requests)

### Rewrite Rules
1. Every claim in the rewritten sections must be **traceable** to existing data in Results
2. Trending keywords should be added **only where natural** — no keyword stuffing
3. The "interdisciplinary hook" should appear in Abstract sentence 1 and Discussion ¶2
4. Quantitative impact statements preferred over qualitative ones
5. All placeholder values use format `[PLACEHOLDER:value]` for author verification

**Output**: `reframed_sections.md` containing:
- New Title
- New Abstract
- New Introduction ¶4
- New Discussion ¶1-2
- Diff blocks showing what changed vs the original

---

## Step 4: Alignment Check

**Goal**: Verify the reframing doesn't introduce overclaims or inconsistencies.

### 4.1 Overclaim Guard
For each claim in the reframed sections:
- Is it supported by data in Results? YES/NO
- Is the language stronger than the evidence warrants? YES/NO
- If any YES on overclaim → flag and suggest softer language

### 4.2 Internal Consistency
- Does the new Title match the new Abstract?
- Does the new Abstract sentence 2 match the new Introduction ¶4?
- Does Discussion ¶1 accurately summarize Results?
- Are all figure references still valid?

### 4.3 Keyword Verification
- List all trending keywords added → verify each appears naturally
- Check keyword density (no term appears > 3× in Abstract)

### 4.4 Cover Letter Update
If `cover_letter_draft.md` exists:
- Update Significance Statement to match new framing
- Update "Why this journal" to reference trending editorial themes
- Verify suggested reviewers still make sense for new angle

**Output**: 
- `alignment_report.md` — all checks with PASS/FLAG results
- Updated `cover_letter_draft.md` (if existed)
- Updated `reframed_sections.md` with any overclaim fixes applied

---

## Final Output

When complete:
1. `landscape_analysis.md` — competitive positioning + proposed angles
2. `reframed_sections.md` — new Title, Abstract, Intro ¶4, Discussion ¶1-2
3. `alignment_report.md` — overclaim / consistency verification
4. Updated `cover_letter_draft.md` — aligned with new framing

> ℹ **Integration**: To produce a submission-ready manuscript, manually merge `reframed_sections.md` into `final_manuscript.md`, replacing the corresponding sections.

// turbo
## Completion Notification

When ALL steps above are finished, run this command to alert the user:

```powershell
[console]::beep(800,300); Start-Sleep -Milliseconds 200; [console]::beep(1000,300); Start-Sleep -Milliseconds 200; [console]::beep(1200,500)
```

Then tell the user: **"✅ 故事工程已完成。请查看 `landscape_analysis.md` 和 `reframed_sections.md`。"**
