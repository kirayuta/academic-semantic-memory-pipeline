---
name: manuscript_preprocessor
description: Preprocess raw manuscripts into chunked, review-ready Markdown with lightweight quality validators and pre-flight checks
---

# Manuscript Preprocessor v3.1

> Raw manuscript → Structured chunks + Quality validators + Pre-flight checks → Ready for /research v5.2 iteration

---

## Overview

This skill converts a raw manuscript (pasted from Word/Docs) into **review-ready chunks** optimized for LLM token budgets, plus 3 lightweight quality validators and pre-flight checks that guide the review process.

### Design Principles

- **Token-budget aware**: Each chunk ≤ 4,000 tokens of manuscript text
- **Context-preserving**: Every chunk carries a context header summarizing other sections
- **Sequential iteration**: Results → Discussion → Introduction → Abstract (dependencies flow upward)
- **Lightweight validation**: Markdown tables, not JSON schemas

---

## Phase 1: Format Cleanup

### Step 1: Metadata Extraction
Extract from first ~15 lines → YAML front matter:
- `title`, `authors`, `affiliations`, `keywords`, `journal`

### Step 2: Structure Normalization
- Title → `# Title`
- Major sections → `## Section`
- Subsections → `### Subsection`

### Step 3: Equation Conversion
- Inline: `E_z`, `|E/E_0|^4` → `$E_z$`, `$|E/E_0|^4$`
- Display: standalone → `$$...\quad\text{(Eq. N)}$$`

### Step 4: Cleanup
- Delete `<!-- ACTION ITEM -->` comments
- Clean figure regions → `> **[Figure N]**: caption`
- Mark SI references → `[SI: Fig. SX — not reviewed]`
- Remove excessive empty lines
- Normalize references

**Output:** `draft_v1.md` (full preprocessed manuscript)

---

## Phase 2: Chunk & Freeze

### Freeze List (不迭代)
These sections are extracted and saved separately. They do NOT enter the review loop:
- `frozen/metadata.yaml` — authors, affiliations, acknowledgements
- `frozen/methods.md` — Methods section (optional R6 review)
- `frozen/references.md` — Reference list (**REQUIRED** for Reference Coverage Audit in Phase 3b)
- `frozen/si_references.md` — SI reference inventory

> ⚠️ **v3.1**: `frozen/references.md` MUST contain the complete reference list. If the manuscript does not have a parseable reference section, generate a stub file listing all in-text citation numbers and warn: "Reference audit will be partial — full list needed."

### Chunk Strategy

**Target: each chunk ≤ 4,000 tokens** (to fit within ~8K total review budget)

Split the manuscript into review chunks:

| Chunk | Content | Iteration Order | Figure Captions |
| :--- | :--- | :--- | :--- |
| `chunk_A.md` | Title + Abstract | 5th (last) | None |
| `chunk_B.md` | Introduction | 4th | None |
| `chunk_C.md` | Results §1 (by Figure grouping) | 1st | **Include in chunk body** |
| `chunk_D.md` | Results §2 (by Figure grouping) | 2nd | **Include in chunk body** |
| `chunk_E.md` | Discussion | 3rd | Referenced figures' captions |

> **v3 change**: Figure captions are now included **in the chunk body** (not just as references). This ensures captions are reviewed alongside the text that references them.

**Adaptive splitting for Results**: Group by `###` subsection headings or by Figure discussion. If a single group > 4,000 tokens, split at paragraph boundaries.

### Context Header

**Every chunk** gets a context header (adds ~200-500 tokens):

```yaml
---
chunk: "[section name]"
parent: "[paper title]"
iteration_order: N of 5
preceding_sections_summary: |
  [2-3 sentence summary of sections that come BEFORE this one in the paper]
following_sections_summary: |
  [2-3 sentence summary of sections that come AFTER this one in the paper]
figures_in_chunk: [Fig. X, Fig. Y]
equations_in_chunk: [Eq. X, Eq. Y]
key_claims_in_chunk: [claim_ids from claim_evidence_matrix]
---
```

**Important for Abstract (chunk_A):** Since Abstract is iterated LAST, its context header must contain the **latest summaries** of all other chunks (updated after their iterations complete).

### Iteration Order Rationale

```
Results (C,D) → Discussion (E) → Introduction (B) → Abstract (A)
```

1. **Results first**: These are facts. They change least but set the foundation.
2. **Discussion second**: Interprets Results. Must align with what Results actually show.
3. **Introduction third**: Frames the gap and claim. Must match what Results delivered.
4. **Abstract last**: Distills everything. Must reflect the final state of all sections.

---

## Phase 3: Lightweight Validators

### Validator 1: `claim_evidence_matrix.md`

Generated during Step 0. **Referenced in every review round.**

Extract every claim from the manuscript and map to evidence:

```markdown
# Claim-Evidence Matrix

| # | Claim (verbatim quote) | Section | Evidence | Evidence Type | Strength | Flag |
|---|---|---|---|---|---|---|
| C1 | "20 dB suppression of side-lobes" | Results | Fig. 3b | Direct | ✅ Strong | — |
| C2 | "transforms TERS from luck-based art" | Abstract | None | Assertion | ⚠️ Unsupported | Soften |
| C3 | "~15-fold enhancement" | Abstract | Fig. 4b shows 17× | Direct | ⚠️ Inconsistent | Check |
| C4 | "fundamental LSP mode" | Results | FDTD field map | Simulation | ✅ Moderate | Needs modal decomp |

## Evidence Type (NEW in v3)
- **Direct**: Experimental measurement with quantified result
- **Simulation**: FDTD, FEM, or other computational result
- **Theoretical**: Derived from theory/equations without direct measurement
- **Assertion**: No supporting evidence provided (opinion, rhetoric)

> ⚠️ **Auto-flag rule**: Any claim where `Evidence Type = Assertion` or `Theoretical` that supports a **core finding** → auto-flag as P1 during R1.

## Strength Levels
- ✅ **Strong**: Direct experimental data, properly quantified
- ✅ **Moderate**: Supported by simulation or indirect measurement
- ⚠️ **Weak**: Logical inference without direct data
- ⚠️ **Unsupported**: No evidence provided
- ❌ **Overclaim**: Claim exceeds what data shows

## Phrasing Guide (for overclaim detection)
- ✅ Cautious: "suggests", "is consistent with", "we attribute X to Y"
- ⚠️ Strong: "demonstrates", "proves", "shows that"
- ❌ Absolute: "always", "never", "completely", "perfectly"
```

### Validator 2: `novelty_statement.md`

Extract all novelty-related sentences ("Here we show", "for the first time", "we demonstrate"):

```markdown
# Novelty Audit

## Claimed Novelty Statements
1. "[exact quote]" (Section: Introduction, Line: N)
   - **Prior art**: [relevant references that partially address this]
   - **Delta**: [what is genuinely new vs. incremental]
   - **Verdict**: ✅ Novel / ⚠️ Incremental / ❌ Already shown

## Missing Positioning
- [Areas where the paper should differentiate from prior work but doesn't]
```

### Validator 3: `consistency_checklist.md`

Generated during **Reassembly** (Step 6). Checks cross-chunk consistency:

```markdown
# Consistency Checklist

## Terminology
| Term Variant A | Term Variant B | Chosen Standard | Chunks Affected |
|---|---|---|---|
| "AO ON" | "AO-ON" | "AO ON" | C, D, E |

## Numerics
| Value in Section A | Value in Section B | Match? | Action |
|---|---|---|---|
| "~15-fold" (Abstract) | "17×" (Results) | ❌ | Reconcile |

## Cross-References
| Reference | Target Exists? | Correct? |
|---|---|---|
| "as shown in Fig. 2c" | Fig. 2c caption exists | ✅ |
```

---

## Phase 3b: Pre-Flight Checks (NEW in v3)

Run BEFORE iteration starts:

### Check 1: Global Overclaim Scan
Scan all chunks for absolute language:
- Keywords: "transforms", "proves", "perfectly", "first-ever", "unique", "always", "never"
- For each occurrence: flag + require explicit evidence type
- Output: append flags to `claim_evidence_matrix.md`

### Check 2: Discussion Structure Skeleton
Verify `chunk_E` contains (or pre-populate skeleton for):
1. ¶1 — Summary of key findings
2. ¶2 — Significance and broader impact
3. ¶3 — Limitations
4. ¶4 — Future directions

If any missing → pre-populate skeleton text marked `<!-- AUTHOR: fill this section -->`

### Check 3: Limitations Pre-check
If chunk_E has no limitations content → flag as **P0 before iteration starts**.

### Check 4: Target Journal Calibration
Record target journal in metadata YAML:
```yaml
target_journal: "Nature Photonics"
impact_tone: "paradigm-shifting but precise"
```
This affects impact tone during R5 (Nature-Level Final Pass).

### Check 5: Reference Coverage Audit
Scan reference list (`frozen/references.md`) and manuscript body:
- For each `###` subsection: are key references in that sub-field cited?
- Year distribution: flag if <30% of references are from the last 3 years
- Self-citation ratio: flag if >25% are from the same group
- Missing competing groups: identify uncited groups working in the same area
- Output: `reference_audit.md` with gaps and suggestions

### Check 6: Required Sections Audit (NEW in v3.1)
Verify the following exist in the manuscript or `frozen/` sections:
- ✅ Data Availability Statement (Nature Photonics **requires** it)
- ✅ Code Availability Statement (if computational work present)
- ✅ Author Contributions
- ✅ Competing Interests Declaration
- If ANY missing → flag as **P0**, add to `author_queries.md` with exact wording template

---

## Phase 3c: Chunk Complexity Estimator (v3.1)

For each chunk, compute a complexity score with **section-type multiplier**:

```
Base score = word_count/500 + equations×2 + figures×1.5 + claims_weighted

Claims weighting by section type:
  Discussion:    claims × 1.5 × 0.5  (overclaim risk is higher)
  Abstract:      claims × 1.2 × 0.5  (each word carries more weight)
  Introduction:  claims × 1.0 × 0.5  (standard)
  Results:       claims × 0.8 × 0.5  (fact-dense, lower overclaim risk)

Score → min_rounds mapping:
  < 3  → min_rounds = 3  (e.g., Abstract)
  3-6  → min_rounds = 5  (e.g., Introduction, Discussion)
  > 6  → min_rounds = 6  (e.g., Results with equations)
```

Record in each chunk's context header as `complexity_score` and `min_rounds`.

---

## Complete Pipeline Summary

```
Raw Manuscript
    │
    ▼ Phase 1: Format Cleanup
    ├── draft_v1.md (full preprocessed)
    │
    ▼ Phase 2: Chunk & Freeze
    ├── frozen/ (metadata, methods, references[required], SI)
    ├── chunk_A.md through chunk_E.md (with context headers + figure captions)
    │
    ▼ Phase 3: Validators
    ├── claim_evidence_matrix.md (with evidence_type column)
    ├── novelty_statement.md
    │
    ▼ Phase 3b: Pre-Flight Checks
    ├── Global overclaim scan → flags in claim_evidence_matrix
    ├── Discussion structure skeleton → chunk_E validation
    ├── Limitations pre-check → P0 if missing
    ├── Target journal calibration → metadata
    ├── Reference coverage audit → reference_audit.md
    ├── Required sections audit → P0 if Data Availability missing (v3.1)
    │
    ▼ Phase 3c: Chunk Complexity Estimator (section-type multiplier, v3.1)
    ├── Complexity score per chunk → dynamic min_rounds
    │
    ▼ /research v5.2 workflow takes over
    │   R0: Non-Expert Readability pre-screen (chunk_A only)
    │   Per-chunk iteration: C → D → E → B → A
    │   Dynamic rounds (min per complexity, max 10)
    │   R2: Structured diff output + [PLACEHOLDER:AQ-N] format
    │   R3: Missing Controls + Suggested Protocols + Alt. Methodology
    │   R3 sub-rounds don't count toward main round
    │   Early acceptance (≥3 approvals + R3 + min-1 rounds)
    │   revision_history compression at round 7+ (R3 never compressed)
    │   Auto-collects DEFERRED + Missing Controls → author_queries.md
    │
    ▼ Global Quality Gate + Reviewer Risk Score (v5.2)
    │   Claim-Evidence audit, Novelty, Reference coverage, Missing Controls
    │   Risk score per chunk: HIGH/MED/LOW
    │
    ▼ Reassembly
    ├── consistency_checklist.md (+ equation numbering check, v5.2)
    ├── final_manuscript.md (with transition sentences)
    ├── author_queries.md (auto-collected)
    │
    ▼ Post-processing
    ├── Figure-Text Alignment check (+ panel format verification)
    ├── Adversarial Reviewer (Reviewer #3)
    ├── Cover Letter + Significance Statement
    └── Methods Audit
```
