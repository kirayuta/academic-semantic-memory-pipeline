---
name: cover_letter_generator
description: Generate Nature-tier cover letters from Semantic Core + polished abstract, using Move-by-Move architecture with editorial persuasion constraints.
version: 1.0.0
---

# Cover Letter Generator Skill

Generate cover letters for Nature / Nature Photonics / Science submissions. Reuses the pipeline's Semantic Core and polished abstract as input — no additional manuscript reading required.

## Inputs

*   `manuscript_semantic_core.md` (Required): Fact Base + Logic Graph + Claims from `extract_semantic_core` skill.
*   `abstract_candidates.md` (Required): The polished abstract from `imo_abstract_polish` skill.
*   Author info (Required): Corresponding author name, affiliation, email — provided by user or extracted from manuscript metadata.
*   Target journal (Required): e.g., "Nature Photonics". Determines audience framing.

## Architecture Overview

```
Phase 1: Move-by-Move Generation (5 Moves, Best-of-3)
  CL1 → ✓ → CL2 → ✓ → CL3 → ✓ → CL4 → ✓ → CL5 → ✓

Phase 2: Assembly + Tone Verification

Phase 3: Output → cover_letter.md
```

---

## Cover Letter DNA: What Editors Want

> [!IMPORTANT]
> Nature editors read 50+ cover letters per week. They scan for **3 things in 30 seconds**:
> 1. **What did you find?** (1 sentence — your headline result)
> 2. **Why does it matter broadly?** (1-2 sentences — beyond your subfield)
> 3. **Why THIS journal?** (1 sentence — audience fit, not flattery)
>
> Everything else is noise. Keep total length to **250–350 words** (¾ page).

### Anti-patterns (instant editor eye-roll)

| ❌ Don't | ✅ Do |
|:--|:--|
| "We would like to submit..." | Jump straight to the science |
| "Nature is the world's leading journal" | Name the specific readership |
| "We believe our work is suitable for..." | State why the audience benefits |
| Repeating the entire abstract | 2-3 bullet points with NEW framing |
| Listing all authors' credentials | Let the science speak |
| "We hope you will consider..." | Confident but measured close |

---

## Phase 1: Move-by-Move Solver

> [!IMPORTANT]
> **Source Lock**: CL Moves may ONLY read `manuscript_semantic_core.md` and `abstract_candidates.md`.
> The cover letter must NOT be a paraphrase of the abstract — it must REFRAME the findings for an editor, not a reader.

### Move Definitions

For **each Move** below:
1. Generate **3 candidate paragraphs** (Candidate α, β, γ)
2. Run the **Micro-Verifier** checks
3. **Rank** by: (a) checks passed, (b) conciseness, (c) persuasiveness
4. **Select winner**

---

#### Move CL1 — Hook + Headline (2–3 sentences, ~50 words)

**Role**: Open with the single most compelling result. No preamble.

**Solver Input**:
- Logic Graph → Key Result + Novelty
- Polished abstract → S3 (result sentence)

**Pattern**: Start with "We report..." / "We demonstrate..." / "Here we show..." followed by the headline finding and ONE sentence of why it matters.

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| No preamble | Does NOT start with "Dear Editor, we would like to submit..." or equivalent |
| Headline first | First sentence contains the core result? |
| Quantitative | Contains ≥1 number from Fact Base (★★★)? |
| Word count | 40–60 words |
| No abstract copy | ≤3-gram overlap with polished abstract? |

---

#### Move CL2 — Broader Significance (2–3 sentences, ~60 words)

**Role**: Explain why a physicist/chemist/biologist who is NOT in this subfield should care. This is where you sell across disciplines.

**Solver Input**:
- Logic Graph → Impact + Context
- Fact Base → ★★ and ★☆ facts (the ones abstracted away in the abstract — use them HERE)

**Pattern**: "Beyond [specific subfield], this work addresses..." or "This advance is relevant to the broader [journal] readership because..."

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Cross-discipline | Mentions ≥1 field OUTSIDE the paper's primary domain? |
| No jargon | Avoidable acronyms spelled out? |
| Concrete benefit | Names a specific application or community that benefits? |
| Word count | 50–70 words |

---

#### Move CL3 — Key Advances (bullet list, ~80 words)

**Role**: 3 bullet points summarizing the key advances. These must be DIFFERENT from the abstract — reframe as "what the editor should highlight to reviewers."

**Solver Input**:
- Fact Base → top 3 ★★★ facts NOT adjacent in abstract
- Claims Inventory → STRONG claims only

**Pattern**:
```
Key advances include:
• [Advance 1 — the "first" or "record" claim, with number]
• [Advance 2 — the mechanism insight, why it works]
• [Advance 3 — the practical implication, what it enables]
```

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Exactly 3 bullets | Not 2, not 4 |
| Each ≤30 words | Tight, scannable |
| No WEAK claims | Only STRONG claims in bullets |
| Non-redundant | No bullet repeats abstract sentence verbatim |
| Fact-locked | All numbers match Fact Base |

---

#### Move CL4 — Journal Fit (1–2 sentences, ~40 words)

**Role**: Explain why THIS journal, THIS readership. Must be specific — not "Nature is prestigious."

**Solver Input**:
- Target journal name
- Logic Graph → Impact + Context
- Which community reads this journal?

**Pattern**: "We believe this work will appeal to [journal]'s readership in [specific areas] because [specific reason]." or "This work bridges [field A] and [field B], a combination that aligns with [journal]'s recent focus on [topic]."

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Specific | Names the journal's readership or recent editorial direction? |
| No flattery | Does NOT say "leading", "prestigious", "world-renowned"? |
| Audience-centric | Framed as benefit to readers, not request from authors? |
| Word count | 30–50 words |

---

#### Move CL5 — Close (2 sentences, ~40 words)

**Role**: Professional close. Offer reviewer suggestions (optional). Confirm exclusivity.

**Pattern**: "We confirm that this manuscript is not under consideration elsewhere. We suggest [Reviewer 1] and [Reviewer 2] as potential referees, given their expertise in [area]."

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Exclusivity statement | Confirms single submission? |
| No begging | Does NOT use "we hope", "we kindly request", "we would be grateful"? |
| Professional tone | Measured confidence |
| Word count | 30–50 words |

---

## Phase 2: Assembly + Tone Verification

### Step 2a: Assemble

```
Dear Editor,

[CL1 — Hook + Headline]

[CL2 — Broader Significance]

[CL3 — Key Advances as bullets]

[CL4 — Journal Fit]

[CL5 — Close]

Sincerely,
[Corresponding Author]
[Affiliation]
[Email]
```

### Step 2b: Tone Check

| Check | Target |
|:--|:--|
| Total word count | 250–350 words |
| Tone | Confident but not arrogant; measured but not meek |
| Jargon density | ≤2 unexpanded acronyms in entire letter |
| Abstract overlap | No sentence-level paraphrase of abstract |
| "We" frequency | ≤6 instances (avoid self-referential monotony) |

### Step 2c: Persuasion Audit

Read the letter as if you are the editor. Ask:
1. "Do I know what they found?" → CL1 answers this
2. "Do I care?" → CL2 answers this
3. "What specifically is new?" → CL3 answers this
4. "Is it right for my journal?" → CL4 answers this
5. "Is this professional?" → CL5 answers this

If any answer is "no" → revise that Move. Max 2 iterations.

---

## Phase 3: Save Output

> [!CAUTION]
> Save output to `cover_letter.md` using `write_to_file`.

### Output Template

```markdown
# Cover Letter — [Paper Title]

**Target Journal**: [journal name]
**Corresponding Author**: [name, affiliation, email]
**Date**: [date]

---

Dear Editor,

[assembled letter body]

Sincerely,
[author block]

---

## Generation Metadata

| Metric | Value |
|:--|:--|
| Total words | __ |
| CL1 Hook | __w |
| CL2 Significance | __w |
| CL3 Advances | __w (3 bullets) |
| CL4 Journal Fit | __w |
| CL5 Close | __w |
| Abstract overlap (max 3-gram) | ✅/❌ |
| Persuasion audit | 5/5 |
```
