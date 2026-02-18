---
name: imo_abstract_polish
description: Generate Nature-tier abstracts using Move-by-Move Solver with per-sentence verification.
version: 4.0.0
---

# IMO Abstract Polishing Skill (Move-by-Move Architecture)

This skill generates academic abstracts **one sentence at a time**, with per-Move verification and Theme-Rheme chaining injected at generation time. It prevents hallucination by grounding each Move in the Semantic Core and ensures coherence through explicit information-flow control.

## Inputs
*   `manuscript_semantic_core.md` (Required): Fact Base + Logic Graph + Claims from `extract_semantic_core` skill.
*   Editorial DNA (Required): Either `writing_brief.md` (from Retriever pipeline) or `editorial_dna_fallback.md`.
*   `draft_abstract.md` (Required for Verifier): Original abstract — used ONLY in Phase 2 for Source Lock checks.

## Architecture Overview

```
Phase 1: Move-by-Move Generation (7 micro Solver-Verifier loops, Best-of-4)
  M1 → ✓ → M2 → ✓ → M3 → ✓ → M3b → ✓ → M4 → ✓ → M5 → ✓ → M6 → ✓
  Each Move: 4 candidates → micro-verify → rank → select → annotate confidence

Phase 2: Assembly + Global Verification
  Concatenate 7 winners → Smoothing pass → Full 5-dim scoring → Source Lock

Phase 2.5: Adversarial Red Team
  Reviewer attack scan → HIGH severity? → re-generate targeted Moves → re-verify

Phase 3: Output
  Save abstract_candidates.md + abstract_scoring_matrix.md
```

---

## Phase 1: Move-by-Move Solver

> [!CAUTION]
> **Claim Safety Rule**: Before generating ANY Move, read `## 3. Claims Inventory` in `manuscript_semantic_core.md`.
> - Claims marked **WEAK** must NOT appear unless softened (e.g., "generalizable" → "potentially generalizable").
> - Claims marked **MODERATE** must use hedging language (e.g., "suggests", "indicates").

> [!IMPORTANT]
> **Source Lock**: Solver may ONLY read `manuscript_semantic_core.md` and `writing_brief.md`.
> Do NOT read `draft_abstract.md` during generation. Numbers must match Fact Base precision exactly.

### Move Definitions

For **each Move** below:
1. Generate **4 candidate sentences** (Candidate α, β, γ, δ)
2. Run the **Micro-Verifier** checks listed on all 4
3. **Rank candidates** by: (a) micro-verifier pass count, then (b) conciseness (fewer words wins ties)
4. **Select winner** (highest-ranked candidate)
5. **Extract Rheme** (the new information introduced) and pass it to the next Move as Theme seed
6. **Confidence annotation**: Rate the winner on 3 axes (0.0–1.0 each):
   - **Fact** — How certain the facts are correctly represented?
   - **Flow** — How well does Theme-Rheme chain from the previous Move?
   - **Style** — How well does this match Nature editorial DNA?
   Record as `[F: X.X | Fl: X.X | S: X.X]` in the Move Workbench.

---

#### Move M1 — Context (~20 words, 1 sentence)

**Role**: Set the domain stage. Name the object/field of study.

**Solver Input**:
- Logic Graph → Context/Gap (first half)
- `writing_brief.md` → §1 opening pattern (dominant type)
- §5 Constraint 1: Must open object-first

**Generate**: Write ONE sentence that names the core scientific object or capability being studied.

**Micro-Verifier**:

| Check | Rule | 
|:--|:--|
| Opening pattern | Object-first? (not "Despite…", not "The challenge…") |
| Register | Measured — prefer "a valuable tool" / "an important probe". Do NOT overclaim ("cornerstone", "indispensable", "revolutionized"). Nature prefers understatement. |
| Word count | 15–25 words |
| Technical terms | ≤1 acronym/technical term |
| Claim safety | No WEAK claims |

**Extract**: Identify the **Rheme** (new concept introduced) → pass to M2.

---

#### Move M2 — Gap (~20 words, 1 sentence)

**Role**: Build tension. Auto-detect Gap type from Logic Graph.

**Gap Type Detection** (read Logic Graph → Gap node):
- **Type A — Improvement**: An incumbent method/technique exists but has limitations. Use concession-then-limitation ("However, it suffers from..." or "While X enables Y, it remains limited by Z").
- **Type B — Exploration**: No incumbent exists; the field simply hasn't achieved X yet. Use frontier gap ("Yet no method has been able to..." or "However, [capability X] has remained elusive").

**Solver Input**:
- Logic Graph → Gap (determines Type A or B)
- M1 Rheme (Theme seed for this sentence)

**Generate**: Write ONE sentence matching the detected Gap type. **Keep it short** — a simple "However,..." is preferred over elaborate subordinate clauses.

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Theme chain | Opens with concept from M1 Rheme? |
| Gap type match | Type A → contains concession/contrast? Type B → contains frontier/exploration framing? |
| Word count | **≤20 words preferred**. Max 25 words. Nature Gap sentences are typically 12–18 words. |
| Claim safety | No WEAK claims |

**Extract**: Identify **Rheme** (the limitation/gap) → pass to M3.

> [!TIP]
> **G3 — M1+M2 Merge Option**: After generating M2, check if M1 + M2 combined ≤ 25 words.
> If so, they MAY be merged into **one sentence** using:
>   - "X demands/requires Y, **yet** Z" (context, yet gap)
>   - "X is essential for Y, **but** Z" (context, but gap)
>
> This saves ~5–10 words for later Moves. The merged sentence inherits M2's Rheme for M3.
> If merged, produce ONE candidate pair for the merged version and micro-verify:
>   - Opening: object-first ✅
>   - Contains contrast marker ("yet"/"but") ✅
>   - Word count: ≤25 ✅
>   - Theme-Rheme: gap concept is the Rheme ✅

---

#### Move M3 — Pivot (~25 words, 1 sentence)

**Role**: The "Here we" sentence — announce what the paper achieves.

> [!TIP]
> **G4 — Architecture-First Detection**: Read Fact Base for device/architecture count.
> - **≥2 distinct architectures** (e.g., two cavity designs, two fabrication methods): M3 should prioritize **listing them** (mechanism specificity) and **defer headline numbers to M4**. Pattern: "Here we demonstrate X based on Y, realized in two architectures: [arch 1] and [arch 2]."
> - **≤1 architecture**: Use default outcome-first pattern: "Here we demonstrate X, achieving [number]."

**Solver Input**:
- Logic Graph → Mechanism + Key Result
- M2 Rheme (Theme seed)
- §5 Constraint 2: Must include "Here we [verb]"
- §5 Constraint 12: Outcome-first (WHAT, not HOW) — **unless** ≥2 architectures triggers architecture-first
- `writing_brief.md` → §1 verb frequency (prefer top verb)

**Generate**: Write ONE sentence starting "Here we [verb]". If architecture-first: list architectures without numbers. Otherwise: lead with achievement.

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Theme chain | Opens with concept from M2 Rheme? |
| "Here we" | Contains "Here we [verb]"? |
| Outcome-first OR Architecture-first | Leads with achievement (default) OR lists ≥2 architectures (G4)? |
| Word count | 20–35 words (upper bound extended for architecture listing) |
| Claim safety | No WEAK claims |

**Extract**: Identify **Rheme** (the technique/achievement named) → pass to M3b.

---

#### Move M3b — Mechanism (~40 words, 1-2 sentences)

**Role**: Explain HOW the technique works. Densest information.

> [!TIP]
> **Merge Option**: If M3 + M3b combined ≤ 50 words **AND** the paper has ≤1 architecture (G4 not triggered), they MAY be merged into a single sentence. Use a participial phrase: "...which [outcome], [mechanism]-ing [details]." If merged, skip M3b's micro-verifier and move directly to M4.
> If ≥2 architectures (G4 triggered), keep M3 separate (architecture description) and use M3b for mechanism/fabrication details.

**Solver Input**:
- ★★★ facts from Fact Base (mechanism-related)
- M3 Rheme (Theme seed)
- §5 Constraint 3: Must include ≥1 quantitative result

**Generate**: Write 1-2 sentences explaining the technical mechanism, citing specific numbers from the Fact Base.

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Theme chain | Opens with concept from M3 Rheme? |
| Fact-locked | All numbers match Fact Base exactly? |
| IU count | ≤6 information units? (acronyms + numbers + proper nouns + compounds + domain NPs) |
| Word count | 30–50 words |
| Technical terms | ≤2 per sentence |

**Extract**: Identify **Rheme** (key technical detail) → pass to M4.

---

#### Move M4 — Key Result (~20–35 words, 1 sentence) ⚡ CONDITIONAL

**Role**: The headline number(s) — concentrated impact.

> [!IMPORTANT]
> **Conditional Move**: Generate M4 ONLY if there is a standalone quantitative result that was NOT already stated in M3 or M3b. If the main headline number is already in M3, and no additional independent metric justifies its own sentence, **SKIP M4** and proceed to M5.

> [!TIP]
> **G5 — Number-Packing Option**: If there are **≥2 independent headline numbers** NOT yet stated (e.g., efficiency for weak coherent + efficiency for single photons + multimode count), M4 MAY pack them using parallel structure:
>   - "A for X and B for Y"
>   - "A for X, B for Y, alongside C with D"
>
> When packing, relax the single-claim rule:
>   - Standalone check → allow up to **3 parallel quantitative claims**
>   - IU count → allow up to **5** (instead of 3)
>   - Word count → allow up to **35** (instead of 25)
>
> This matches Nature's editorial preference for concentrated impact sentences.

**Solver Input**:
- ★★★ facts → quantitative result(s) NOT yet mentioned in M3/M3b
- M3b Rheme (Theme seed)
- §5 Constraint 9: Standalone sentence for headline achievement

**Generate**: Write ONE sentence with quantitative result(s) not yet presented. If ≥2 numbers available, use parallel packing (G5). Otherwise, single-number standalone.

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Non-redundant | Number(s) NOT already stated in M3 or M3b? |
| Theme chain | Opens with concept from M3b Rheme? |
| Standalone or Packed | Single claim (default) OR ≤3 parallel claims (G5)? |
| Fact-locked | All numbers match Fact Base exactly? |
| IU count | ≤3 (default) or ≤5 (G5 packing) |
| Word count | 15–25 (default) or 15–35 (G5 packing) |

**Extract**: Identify **Rheme** (the specific achievement) → pass to M5.

---

#### Move M5 — Application / Secondary Result (~25 words, 1 sentence)

**Role**: Present the application or a secondary result that broadens the paper's impact.

**Application Type Detection** (read Fact Base + Logic Graph):
- **Type A — Clinical/Biomedical**: Paper has disease/patient/diagnostic results → use domain-shift marker "As a medical/clinical application,..." + name specific conditions/organ systems.
- **Type B — Materials/Characterization**: Paper demonstrates technique on materials, devices, or systems → use domain-shift marker "As a demonstration of [material/device] characterization,..." or "Applied to [material system],..." + name specific materials/substrates.
- **Type C — Secondary Result (no application)**: Paper is purely fundamental with no applied demonstration → present a **different ★★★ fact** not yet covered. Drop domain-shift marker. Keep Theme chain.

**Solver Input**:
- ★★★ facts with applied/secondary context
- M4 Rheme or M3b Rheme (Theme seed — depends on whether M4 was skipped)
- §5 Constraint 13: Domain-shift marker (Type A or B only)

**Generate**: Write ONE sentence. For Type A/B: open with a domain-shift marker. For Type C: open with Theme chain from previous Move.

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Theme chain | Opens with concept from previous Rheme OR domain-shift marker? |
| Domain-shift (Type A/B only) | Contains "As a [domain] application/demonstration" or equivalent? |
| Specificity | Type A: names conditions/organs. Type B: names materials/substrates. Type C: presents a concrete quantitative fact. |
| Fact-locked | Numbers match Fact Base? |
| Word count | 20–30 words |

**Extract**: Identify **Rheme** (the applied/secondary capability) → pass to M6.

---

#### Move M6 — Impact (~25 words, 1 sentence)

**Role**: Close with forward-looking promise. Measured confidence.

**Solver Input**:
- Logic Graph → Impact + Novelty
- M5 Rheme (Theme seed)
- §5 Constraint 4: Promise closing with forward-looking language
- §5 Constraint 10: Frame as enabling OR supporting (context-dependent)

**Generate**: Write ONE closing sentence that conveys broad significance with appropriate hedging.

**Micro-Verifier**:

| Check | Rule |
|:--|:--|
| Theme chain | Opens with concept from M5 Rheme? |
| Hedge present | Contains ≥1 hedge word ("promising", "paving the way", "able to", "permitting")? |
| No over-assertion | Does NOT use "proves", "establishes" for broad future claims? |
| **Loop closure** | Echoes ≥1 keyword from M1 Context sentence? (e.g., M1 "nanoscale chemical sensitivity" → M6 "quantitative near-field spectroscopy"). This creates narrative satisfaction — the abstract ends by answering its opening. |
| Word count | 20–30 words |
| Claim safety | No WEAK claims unqualified |

---

### Move Workbench (tracking table)

After completing all 7 Moves, produce this workbench:

| Move | Winner | Words | Confidence [F\|Fl\|S] | Theme ← prev | Rheme → next | Checks |
|:--|:--|:--|:--|:--|:--|:--|
| M1 Context | [α/β/γ/δ] | __ | [F: _ \| Fl: _ \| S: _] | (seed) | [extracted] | __/4 |
| M2 Gap | [α/β/γ/δ] | __ | [F: _ \| Fl: _ \| S: _] | [from M1] | [extracted] | __/4 |
| M3 Pivot | [α/β/γ/δ] | __ | [F: _ \| Fl: _ \| S: _] | [from M2] | [extracted] | __/4 |
| M3b Mechanism | [α/β/γ/δ] | __ | [F: _ \| Fl: _ \| S: _] | [from M3] | [extracted] | __/5 |
| M4 Key Result | [α/β/γ/δ] | __ | [F: _ \| Fl: _ \| S: _] | [from M3b] | [extracted] | __/5 |
| M5 Application | [α/β/γ/δ] | __ | [F: _ \| Fl: _ \| S: _] | [from M4] | [extracted] | __/5 |
| M6 Impact | [α/β/γ/δ] | __ | [F: _ \| Fl: _ \| S: _] | [from M5] | N/A | __/5 |

---

## Phase 2: Assembly + Global Verification

### Step 2a: Concatenate + Smooth

1. **Concatenate** all 7 Move winners in order (M1 → M6).
2. **Smoothing pass**: Read the full assembled text and make ONLY these changes:
   - Fix connective words (add "thereby", "thus", "crucially" if transitions are abrupt)
   - Adjust articles/prepositions for grammatical flow
   - **Do NOT** change any factual content, numbers, or core vocabulary
   - **Do NOT** merge or split sentences
   - **Do NOT** exceed 200 words total
3. Record changes made in the Smoothing Log.

### Step 2b: Global 5-Dimension Scoring

Score the assembled abstract on 5 dimensions:

| Dimension | Question | Score |
|:--|:--|:--|
| **Novelty** (0-10) | Does it avoid Problem-First opening? Does it signal a paradigm shift? | __ |
| **Accuracy** (0-10) | Are ALL numbers consistent with `manuscript_semantic_core.md`? | __ |
| **Coverage** (0-10) | Are ALL ★★★ facts present? Are ★★ facts included where space allows? | __ |
| **Flow** (0-10) | Golden Sequence followed? Transitions smooth? ≤200 words? See Flow sub-checks. | __ |
| **Impact** (0-10) | Editor would think "this changes the field"? Appropriate hedging in closing? | __ |

#### Flow Sub-checks

**Theme-Rheme chain verification** (from Move Workbench — should already be ≥80%):

| Pair | S(n) Rheme | S(n+1) Theme | Chains? |
|:--|:--|:--|:--|
| M1→M2 | [from workbench] | [from workbench] | ✅/❌ |
| M2→M3 | | | |
| M3→M3b | | | |
| M3b→M4 | | | |
| M4→M5 | | | |
| M5→M6 | | | |

**Chain Score**: __/6. If ≥5 → +1 Flow bonus. If <3 → -2 Flow penalty.

**Information density check** (IU per sentence):

| S# | Move | IU count | ≤6? |
|:--|:--|:--|:--|
| S1 | M1 | __ | ✅/❌ |
| S2 | M2 | __ | ✅/❌ |
| S3 | M3 | __ | ✅/❌ |
| S4-5 | M3b | __ | ✅/❌ |
| S6 | M4 | __ | ✅/❌ |
| S7 | M5 | __ | ✅/❌ |
| S8 | M6 | __ | ✅/❌ |

**Density shape**: [bell/flat/spiky/front-loaded/back-loaded]. Target: bell.

**Hedge density check**: Count hedges in second half (M4–M6). Target: ≥1 hedge. If 0 → deduct 1 from Impact.

### Step 2c: Source Lock Verification

**W4 — 5-gram overlap check** against `draft_abstract.md`:

| Check | Max Shared N-gram | Length | Pass? |
|:--|:--|:--|:--|
| Assembled abstract | "[longest shared phrase]" | N | ✅ (≤5) / ❌ (≥6) |

If ≥6 words shared → deduct 1 from Novelty. If ≥10 → reject and revise.

**W4b — Paraphrase Detection**: For each sentence, estimate semantic similarity to closest `draft_abstract.md` sentence. If max >0.85 → flag.

### Step 2d: Iteration

```
IF global_score ≥ 8.0 AND Coverage ≥ 7 → ACCEPT, go to Phase 3

ELSE:
    Identify lowest-scoring dimension
    Identify which Move(s) contribute to the weakness
    Re-generate ONLY those Move(s) (max 3 retries per Move)
    Re-assemble and re-score

Max 3 global iterations. Accept best available if limit reached.
```

> [!CAUTION]
> If Accuracy < 8 → identify which facts are wrong and which Move contains them.
> If Coverage < 7 → list which ★★★ facts are missing — this BLOCKS acceptance.
> If a WEAK claim appears unqualified → Coverage = 0.

---

## Phase 2.5: Adversarial Red Team

> [!CAUTION]
> **Role Switch**: You are now a **critical Nature reviewer who wants to REJECT this paper**.
> Your goal is to find the WEAKEST sentence in the abstract and attack it.
> Priority targets: sentences whose Confidence scores have any axis < 0.8.

### Step RT1: Attack Surface Scan

For each sentence S1–S(n), evaluate against 5 attack vectors:

| S# | Attack Vector | Severity | Specific Critique |
|:--|:--|:--|:--|
| S1 | [overclaim / vague / missing-context / logical-gap / unsupported] | [HIGH/MED/LOW] | [exact critique a reviewer would write] |
| ... | | | |

**Attack Vector Definitions**:

| Vector | Meaning | Example |
|:--|:--|:--|
| **Overclaim** | Claim stronger than evidence | "establishes" when C7 is MODERATE |
| **Vague** | Lacks specificity where numbers exist | "significantly improved" when F1 = 80.3% |
| **Missing context** | Reader needs info not provided | Architecture named but not explained |
| **Logical gap** | Cause-effect chain broken | Result before method is introduced |
| **Unsupported** | Fact not in Semantic Core | Number not in Fact Base |

### Step RT2: Triage and Fix

```
IF no HIGH-severity attacks → PASS. Record "Red Team: CLEAN" and go to Phase 3.

IF ≥1 HIGH-severity attack:
    1. Identify which Move(s) produced the attacked sentence(s)
    2. Re-generate ONLY those Move(s) with the critique as an ADDITIONAL constraint
       (e.g., "Reviewer says S3 overclaims — soften 'establishes' to 'suggests'")
    3. Re-assemble → re-score → re-Red-Team
    Max 2 Red Team iterations. Accept best available if limit reached.
```

### Step RT3: Red Team Log

Record in `abstract_scoring_matrix.md`:

```markdown
## Red Team Report
| S# | Attack | Severity | Action Taken | Resolved? |
|:--|:--|:--|:--|:--|
| S3 | Overclaim: "establishes" for MODERATE claim | HIGH | Changed to "suggests" | ✅ |
| S5 | Vague: "significant improvement" | MED | Acceptable — kept | N/A |
```

---

## Phase 3: Save Output

> [!CAUTION]
> You **MUST** use the `write_to_file` tool to save BOTH output files:
> 1. `abstract_candidates.md` — Move Workbench + assembled abstract
> 2. `abstract_scoring_matrix.md` — full scoring breakdown

### Traceability Table

| Rule from writing_brief.md | Applied? | Evidence |
|:--|:--|:--|
| Golden Sequence pattern | ✅/❌ | [Move order] |
| Dominant opening type | ✅/❌ | [M1 type] |
| Dominant closing type | ✅/❌ | [M6 type] |
| Top power verb | ✅/❌ | [verb in M3] |
| Hedging density target | ✅/❌ | [count in M4-M6] |
| IU density target | ✅/❌ | [shape classification] |
| Domain-shift marker | ✅/❌ | [M5 marker text] |

---

## Output Templates

### `abstract_candidates.md`
```markdown
# Abstract — Move-by-Move Generation

## Move Workbench

| Move | Role | Winner | Sentence |
|:--|:--|:--|:--|
| M1 | Context | [α/β] | [sentence text] |
| M2 | Gap | [α/β] | [sentence text] |
| M3 | Pivot | [α/β] | [sentence text] |
| M3b | Mechanism | [α/β] | [sentence text] |
| M4 | Key Result | [α/β] | [sentence text] |
| M5 | Application | [α/β] | [sentence text] |
| M6 | Impact | [α/β] | [sentence text] |

## Smoothing Log
- [list of minor changes made during smoothing pass]

---

## 🏆 Polished Abstract (Final)
[full assembled + smoothed abstract, ≤200 words]

## Iteration Log
- Round 1: Score = X.X. Weakness: [dimension]. Action: [which Moves revised].
- ...
```

### `abstract_scoring_matrix.md`
```markdown
# Abstract Scoring Matrix

| Dimension | Score | Rationale |
|:--|:--|:--|
| Novelty | X/10 | [rationale] |
| Accuracy | X/10 | [rationale] |
| Coverage | X/10 | [rationale] |
| Flow | X/10 | [rationale] |
| Impact | X/10 | [rationale] |
| **Average** | **X.X** | |

## Theme-Rheme Chain
| Pair | Chains? | Detail |
|:--|:--|:--|
| M1→M2 | ✅/❌ | [rheme] → [theme] |
| ... | | |

## Information Density
| Move | IU count | ≤6? |
|:--|:--|:--|
| M1 | __ | ✅/❌ |
| ... | | |

Shape: [bell/flat/spiky]

## Source Lock
| Check | Result | Pass? |
|:--|:--|:--|
| Max 5-gram overlap | [N] words | ✅/❌ |
| Max semantic similarity | [0.XX] | ✅/❌ |

## Fact Check
- [F1] "[metric]" → ✅ present / ❌ missing
- [F2] ...

## Traceability
[copy from Phase 3 traceability table]
```
