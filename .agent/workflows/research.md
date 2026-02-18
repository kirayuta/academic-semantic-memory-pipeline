---
description: Academic research pipeline with chunked iteration, rotating review, lightweight validators, and reassembly
---

# /research — Academic Physics Research & Writing Pipeline v5.3

This workflow simulates the **advisor-student manuscript revision process** targeting **Nature / Nature Photonics** quality. It combines: chunked iteration (token-optimized), cumulative memory (`revision_history.md`), rotating review perspectives with **dynamic round count**, lightweight validators (claim matrix, novelty audit, consistency), new validators (overclaim scanner, statistics checker, discussion structure, comparison gap, missing controls), automatic reassembly, `author_queries.md` generation, **Reviewer Prediction**, and **readability trend tracking**.

// turbo-all

## How to Use

The user provides either:
- **A physics topic** → Antigravity generates `draft_v1.md` from scratch (Step 1), then reviews as a single chunk
- **A raw manuscript file** → Antigravity preprocesses + chunks it (Step 0), then iterates per-chunk

---

## Step 0: Preprocess + Chunk + Validate

**Trigger**: When the input is an existing manuscript file.

Apply the **Manuscript Preprocessor v3** skill (`.agent/skills/manuscript-preprocessor/SKILL.md`):

### Phase 1: Format Cleanup
1. Extract metadata → YAML front matter
2. Add Markdown headings (`##`, `###`)
3. Convert plain-text equations → LaTeX
4. Delete all `<!-- ACTION ITEM -->` comments
5. Clean figure regions → `> **[Figure N]**: caption`
6. Mark SI references → `[SI: ... — not reviewed]`
7. Normalize references
8. Save as `draft_v1.md`

### Phase 2: Chunk & Freeze
9. **Freeze** non-review sections → `frozen/` directory (metadata, methods, references, SI)
   > ⚠️ **v5.2**: `frozen/references.md` MUST contain complete reference list. If not found → generate from manuscript + warn "Reference audit will be partial". (I-14)
10. **Split** reviewable content into chunks (≤ 4,000 tokens each):
    - `chunk_A.md` — Title + Abstract (iterated **last**)
    - `chunk_B.md` — Introduction (iterated 4th)
    - `chunk_C.md` — Results §1 with Figure captions (iterated **1st**)
    - `chunk_D.md` — Results §2 with Figure captions (iterated 2nd)
    - `chunk_E.md` — Discussion (iterated 3rd)
11. Add **context header** to each chunk (summary of other sections, figures/equations referenced)
12. **Include figure captions** in the chunk body (not just references) for each figure mentioned in that chunk

### Phase 3: Generate Validators
13. Extract all claims → `claim_evidence_matrix.md`
    - Include `evidence_type` column: `Direct` / `Simulation` / `Theoretical` / `Assertion`
    - Pre-flag any claim where `evidence_type = Assertion` or `Theoretical` supports a core finding
14. Extract novelty statements → `novelty_statement.md`

### Phase 3b: Pre-Flight Checks
15. **Global Overclaim Scan**: Scan all chunks for absolute language ("transforms", "proves", "perfectly", "first-ever", "unique"). Flag each occurrence. Require explicit evidence type for each.
16. **Discussion Structure Skeleton**: Verify `chunk_E` contains (or pre-populate skeleton for):
    1. ¶1 — Summary of key findings
    2. ¶2 — Significance and broader impact
    3. ¶3 — Limitations
    4. ¶4 — Future directions
17. **Limitations Pre-check**: If chunk_E has no `## Limitations` content, flag as P0 before iteration starts.
18. **Target Journal Calibration**: Record target journal (Nature Photonics / Nature Comms / etc.) in metadata. This affects impact tone across all reviews.
19. **Reference Coverage Audit**: Scan reference list (`frozen/references.md`) and manuscript body:
    - For each `###` subsection: are key references in that sub-field cited?
    - Year distribution: flag if <30% of references are from the last 3 years (Nature Photonics expects recency)
    - Self-citation ratio: flag if >25% are from the same group
    - Missing competing groups: identify uncited groups working in the same area → append to `reviewer_conflict_matrix.md`
    - Output: `reference_audit.md` with gaps and suggestions
20. **Required Sections Audit** (NEW in v5.2): Verify the following exist in the manuscript or `frozen/` sections:
    - ✅ Data Availability Statement (Nature Photonics **requires** it)
    - ✅ Code Availability Statement (if computational work present)
    - ✅ Author Contributions
    - ✅ Competing Interests Declaration
    - If ANY missing → flag as P0, add to `author_queries.md`

### Phase 3b Output Format (v5.2)

Pre-flight results SHOULD be recorded as structured YAML when possible, to enable downstream querying:

```yaml
preflight_results:
  overclaim_scan:
    status: FLAG  # PASS / FLAG / FAIL
    flags_count: 3
    p0_count: 0
  discussion_structure:
    status: PASS
    paragraphs_present: [summary, significance, limitations, future]
  limitations_precheck:
    status: PASS
  reference_audit:
    status: FLAG
    missing_groups: ["Booth (Oxford)"]
    self_citation_ratio: 0.07
    recent_ratio: 0.30
  required_sections:
    status: FAIL
    missing: ["Data Availability Statement"]
```

> Narrative commentary can accompany the YAML but the structured output is the primary record.

### Phase 3c: Chunk Complexity Estimator
21. For each chunk, compute a **complexity score** with section-type multiplier (v5.2):

```
Base score = word_count/500 + equations×2 + figures×1.5 + claims_weighted

Claims weighting by section type (v5.2):
  Discussion:    claims × 1.5 × 0.5  (overclaim risk is higher)
  Abstract:      claims × 1.2 × 0.5  (each word carries more weight)
  Introduction:  claims × 1.0 × 0.5  (standard)
  Results:       claims × 0.8 × 0.5  (fact-dense, lower overclaim risk)

Score → min_rounds mapping:
  Score < 3  → min_rounds = 3  (e.g., Abstract)
  Score 3-6  → min_rounds = 5  (e.g., Introduction, Discussion)
  Score > 6  → min_rounds = 6  (e.g., Results with equations)
```

Record in each chunk's context header:
```yaml
complexity_score: 7.5
min_rounds: 6
max_rounds: 10
```

> **SI Handling Rule (ALL review rounds):**
> Claims depending on SI → tag as `[SI-dependent: not verified]`, do NOT mark as errors.

---

## Step 1: Initial Draft (if generating from topic)

> Skip this step when processing an existing manuscript.

Adopt PI persona. Generate complete IMRaD draft → `draft_v1.md`. Then proceed to Step 0 Phase 2-3 for chunking.

---

## Step 2: Self-Improvement

> Skip this step when processing an existing manuscript (the author's draft IS the v1).

Re-read `draft_v1.md`. Apply Academic Writer checklist. Save as `draft_v2.md`.

---

## Step 3: Per-Chunk Iterative Review

**Iteration order**: `chunk_C → chunk_D → chunk_E → chunk_B → chunk_A`

For each chunk, run **dynamic review rounds** (minimum = chunk's `min_rounds` from complexity estimator, maximum 10):

### R0: Non-Expert Readability Pre-Screen (v5.3 — chunk_A + chunk_B final ¶)

> **Trigger**: Runs for chunk_A (Abstract) **and** the final paragraph of chunk_B (Introduction's "Here we show..." paragraph). Runs BEFORE R1.
> **Rationale (v5.3 I-3)**: The Introduction's closing paragraph is a mini-abstract that editors read in tandem with the Abstract. Its readability matters equally for first-impression.

Adopt a **non-specialist physicist persona** (e.g., condensed matter, not optics):

```
Scoring (per sentence):
  ✅ = fully accessible to non-specialist physicist  → +1
  ⚠️ = understandable with some effort               → +0.5
  ❌ = requires domain expertise to parse             → +0
  
  Score = (sum / total_sentences) × 10

Thresholds:
  ≥ 7/10 → PASS (proceed to R1)
  4-6/10 → P1 (flag jargon, proceed to R1)
  ≤ 3/10 → P0 (REWRITE for accessibility before R1)

For chunk_B: only score the FINAL paragraph. Record score separately as
  `intro_closing_readability: X/10`
```

If P0 (chunk_A): rewrite Abstract with these rules:
1. Open with WHY (problem significance), not HOW (technique)
2. Define all specialist terms in parentheticals
3. Close with quantitative impact + broad "so what"
4. Re-run R0 on rewritten version (max 2 R0 attempts)

If P0 (chunk_B final ¶): flag jargon and suggest rewording. Do NOT rewrite the full Introduction.

> R0 does NOT count toward the main round count.

### Review Angle Rotation (5-round cycle)

| Round | Perspective | Skill | Focus |
| :--- | :--- | :--- | :--- |
| R1 | 🔬✍️ Advisor Dual-Track | Academic Reviewer | Physics + Writing, P0/P1 |
| R2 | 🔄 Fix + Verify (diff output) | Academic Reviewer | Apply R1 fixes as **structured diffs**, verify no regressions, confirm claim_evidence_matrix alignment. All placeholder values use `[PLACEHOLDER:AQ-N]` format. |
| R3 | 🎭 Devil's Advocate + Missing Controls + Alt. Method | Academic Interviewer | Attack assumptions, challenge core claims, **Missing Controls Checklist** with Suggested Protocols, **Alternative Methodology Challenge** (max 1 — v5.3). **ITERABLE**: if R3 finds ≥2 P1, fix and re-run R3 (max 3 sub-rounds: R3a→R3b→R3c). Sub-rounds do **NOT** count toward main round count. |
| R4 | 📐 Numerical & Statistical Audit | Academic Analyst | **If equations exist**: re-derive, dimensional analysis, **derivation chain check** (verify Eq. N → Eq. N+1 assumptions). **For ALL chunks**: verify all numerical claims have N, mean±SD or range definition, appropriate statistical test. Flag any range without explicit sample size. |
| R5 | 📝 Nature-Level Final Pass + Readability Re-score | Academic Editor | Journal-specific style, impact calibration, sentence-level polish. **Figure panel reference format**: must use journal-standard format (e.g., "Fig. 1a" for Nature Photonics). Verify R3 issues resolved. **Readability trend** (v5.3 I-8): for chunk_A, re-run R0 scoring → output `readability_delta`. |

### R1 Sub-Checks

During R1, apply these additional validators:

1. **Overclaim Scanner**: Cross-reference chunk text against `claim_evidence_matrix.md`. For each claim:
   - If `evidence_type = Assertion` → flag as P1 unless hedged
   - If `evidence_type = Theoretical` + claim is "core finding" → flag as P1, require additional justification or hedge
   - Flag absolute language: "first", "unique", "proves", "transforms"

2. **N/Statistics Check**: Scan for numerical ranges (e.g., "60 to 85", "4-6 orders"). For each:
   - Is sample size (N) stated? If not → P1
   - Are error bars or confidence intervals provided? If not → P1
   - **Nature Photonics requires explicit N and error bars for ALL quantitative claims**

3. **Discussion Structure Check** (chunk_E only): Verify 4-paragraph structure:
   - ¶1: Summary of findings → present?
   - ¶2: Significance/broader impact → present?
   - ¶3: Limitations → present?
   - ¶4: Future directions → present?
   - If any missing → P0

4. **Comparison Gap Check** (chunk_E only): Verify Discussion includes:
   - Quantitative comparison with ≥1 competing method/prior work
   - If absent → P1

5. **Model-Experiment Reconciliation** (where applicable): If FDTD/simulation and experiment disagree by >2×:
   - Flag as P1
   - Require explanation as a **structured reconciliation table** (v5.3 I-4):

   | Factor | Estimated Contribution | Basis |
   |:--|:--|:--|
   | [omitted physics 1] | ~N× | [reference or reasoning] |
   | [omitted physics 2] | ~M× | [reference or reasoning] |
   | **Product** | **X–Y×** | Must bracket the observed discrepancy |

   > The table makes reconciliation actionable and directly reviewer-addressable, replacing prose-only explanations.

### R2 Structured Diff Output (v5.2)

R2 MUST output all fixes as **structured diff blocks**:

```diff
- enhancement factors ranging between 60 and 85 at glass/air interfaces
+ enhancement factors of [PLACEHOLDER:AQ-3 | 72±8, N=6] at glass/air interfaces
```

All placeholder values MUST use the format: `[PLACEHOLDER:AQ-N | value | VERIFY WITH AUTHOR]`
- `AQ-N` links to the specific entry in `author_queries.md`
- `value` is the best-estimate placeholder
- Tag ensures author knows this needs verification

After each diff block, verify:
```
Regression check:
  - New claim introduced? YES/NO
  - Existing claim weakened? YES/NO  
  - Figure/equation reference changed? YES/NO
  - claim_evidence_matrix entry affected? → update
```

### R3 Iteration Protocol (v5.2)

R3 (Devil's Advocate + Missing Controls + Alternative Methodology) is the most valuable round:

```
R3a: Initial attack — challenge core assumptions + Missing Controls + Alternative Methodology
  → Missing Controls Checklist: for each causal claim, check:
     1. Is there a control experiment that rules out alternative explanations?
     2. Has the result been reproduced on a second sample/tip/condition?
     3. If not → append to author_queries.md as "Missing Control" WITH Suggested Protocol:
        | Missing Control | Suggested Protocol | Effort Estimate |
        |:--|:--|:--|
        | [description] | [step-by-step protocol, marked [SUGGESTED — verify with PI]] | [hours/days] |

  → Alternative Methodology Challenge (max 1 per chunk — v5.3 I-1):
     "Could this result be achieved with a simpler/different approach?"
     - Pick the SINGLE most impactful alternative. 2/chunk caused scope creep in v5.2 testing.
     - Example: "Why 3f₀ and not 4f₀?", "Why RPB and not linear polarization?"
     - If a simpler approach would work → P1 (justify the chosen method)

  → If R3a finds ≥2 P1: fix issues in chunk text
R3b: Re-attack the fixed version — verify fixes don't introduce new vulnerabilities
  → If R3b finds ≥1 P1: fix again
R3c: Final verification (max sub-round)
  → Accept regardless of findings, but document unresolved items
```

> ⚠️ **Counting rule**: R3 sub-rounds (R3a/R3b/R3c) count as **ONE main round** total. Max 10 main rounds = 2 full cycles of R1-R5.

### Dynamic Acceptance Logic (v5.3)

```
Per main round (R1, R2, R3-as-one, R4, R5):
  - No P0 issues found → APPROVE (increment approval_counter)
  - Any P0 found → REJECT (reset approval_counter to 0)

Chunk acceptance:
  - approval_counter reaches 3 consecutive approvals
  - AND at least ONE R3 (Devil's Advocate) round has APPROVED
  - → Chunk ACCEPTED

Early acceptance:
  IF approval_counter ≥ 3
     AND R3_approved = true
     AND rounds_completed ≥ min_rounds - 1
     AND no unresolved Missing Controls with P0 severity
  → ACCEPT EARLY (skip remaining rounds to reach min_rounds)

Minimum rounds: chunk's min_rounds (from Complexity Estimator, default 5)
Maximum rounds: 10

Round counting:
  - R0 (readability pre-screen) → NOT counted
  - R3 sub-rounds (R3a/b/c) → counted as 1 main round
  - So one full cycle = R1 + R2 + R3(with subs) + R4 + R5 = 5 main rounds
  - Max 10 main rounds = 2 full cycles guaranteed

If max rounds reached without acceptance:
  - Accept chunk WITH CAVEATS
  - Document all unresolved P1 in author_queries.md
  - Tag chunk as "conditionally accepted"
```

### YAML Verdict per Round (v5.3 I-6)

After EACH main round, append a structured YAML block to `revision_history.md`:

```yaml
round_verdict:
  chunk: chunk_C
  round: R1
  verdict: REJECT  # APPROVE / REJECT
  p0_count: 2
  p1_count: 3
  p2_count: 1
  approval_counter: 0  # reset to 0 on REJECT
  new_placeholders: [AQ-6, AQ-7]
  key_issue: "sSNOM EF statistics missing (N, error bars)"
```

> This enables programmatic tracking of `approval_counter`, `P0_count`, and early-acceptance eligibility across rounds. Narrative commentary accompanies but the YAML is the primary record.

### Revision History Rolling Compression (v5.2)

To prevent token budget overflow as rounds accumulate:

```
revision_history.md management:
  Rounds 1-6: keep ALL rounds in full detail
  Round 7+: compress rounds older than 3 into a 1-2 line summary each:
    "Round N: R[type], found X P0 / Y P1, key fix: [one-liner]"
  
  EXCEPTION: R3 (Devil's Advocate) rounds are NEVER compressed.
  R3 findings are the most valuable and must remain accessible to all future rounds.
  
  Total revision_history.md budget after compression: ~3,000 tokens max
  Apply compression BEFORE each new round starts (only at round 7+)
```

This ensures total review input stays within token budget:
`chunk (~4,000) + context header (~500) + revision_history (~3,000) + validators (~1,000) = ~8,500 tokens`

### Backward Propagation Check (depth-limited)

When a chunk iteration changes a key number or claim:
1. Identify all other chunks that reference this number/claim
2. If any already-finalized chunk is affected → re-open that chunk for a targeted mini-review (R1 only, focused on the changed item)
3. Document propagation in `revision_history.md`

> ⚠️ **Propagation depth limit = 1**: Only propagate ONE level. If the mini-review of the re-opened chunk causes a further change that would affect yet another chunk, do NOT cascade. Instead, document the remaining inconsistency in `author_queries.md` for manual resolution. This prevents infinite cascading re-reviews.

### After completing a chunk:
- Update the context headers of remaining chunks with the latest summary of this chunk
- Auto-collect all `DEFERRED` tags from the chunk's review → append to `author_queries.md`
- Move to the next chunk in iteration order

---

## Step 4: Global Quality Gate (v5.3)

Before reassembly, verify:

1. **Claim-Evidence Matrix Final Audit**: Are any claims still flagged ⚠️? 
   - If any P0-level flags remain → STOP, do not reassemble
   - P1-level flags → document in `author_queries.md`
2. **Novelty Audit Confirmation**: All novelty statements adequately supported?
3. **All chunks accepted**: No chunk is "conditionally accepted" with unresolved P0
4. **Reference Coverage**: Verify `reference_audit.md` gaps have been addressed or documented
5. **Missing Controls**: Verify all "Missing Control" items from R3 are in `author_queries.md`

### Reviewer Risk Score

After quality gate, generate a **risk score per chunk**:

```
For each chunk:
  Count: unresolved Missing Controls, PLACEHOLDER values, hedged core claims
  
  Risk levels:
    HIGH  = ≥2 unresolved items OR any conditionally-accepted chunk
    MED   = 1 unresolved item OR ≥3 PLACEHOLDERs
    LOW   = 0 unresolved items, ≤1 PLACEHOLDER

Output:
  chunk_A: RISK = HIGH (readability rewrite needed, 1 PLACEHOLDER)
  chunk_C: RISK = HIGH (MC-2 unresolved, 2 PLACEHOLDERs)
  chunk_D: RISK = MED  (1 PLACEHOLDER: FDTD comparison)
  chunk_B: RISK = LOW
  chunk_E: RISK = MED  (OC-2 "new paradigm" hedged but not resolved)
```

This helps authors prioritize which sections need the most attention.

### Reviewer Prediction (v5.3 I-5)

After Risk Score, predict **2-3 most likely reviewer archetypes** and pre-check the manuscript:

```
For each archetype (pick 2-3 from: Theory Purist, Experimentalist, Methods Skeptic,
  Competing Group PI, Interdisciplinary Generalist, Statistics Hawk):

  1. Name the archetype
  2. List their TOP 3 likely critical questions
  3. For each question: is it pre-addressed in the manuscript? YES/NO/PARTIAL
  4. If NO → add to author_queries.md as "Reviewer Prediction: [archetype] will likely ask..."

Output format:
  reviewer_prediction:
    - archetype: "Experimentalist"
      critical_questions:
        - question: "What is N for the 17-fold enhancement?"
          pre_addressed: PARTIAL  # PLACEHOLDER exists
        - question: "Why no error bars on FWHM?"
          pre_addressed: NO
        - question: "How many tips were tested?"
          pre_addressed: PARTIAL
    - archetype: "Theory Purist"
      critical_questions:
        - question: "Is classical FDTD valid at 0.5 nm gap?"
          pre_addressed: YES  # addressed in R3b fix
        ...
```

> The goal is to convert "potential surprises" into "known items with mitigation plans" before submission.

### Readability Trend Summary (v5.3 I-8)

After all chunks accepted, output the readability trend for chunk_A:

```
readability_trend:
  chunk_A:
    R0_initial: 4.3/10
    R5_final: X/10  # re-scored after R5 edits
    delta: +Y
    verdict: IMPROVED / UNCHANGED / DEGRADED
  chunk_B_final_para:
    R0_initial: Z/10
    R5_final: W/10
    delta: +V
```

> This provides an objective metric for whether the review iteration improved accessibility.

If gate fails → return to Step 3 for the failing chunk(s).

---

## Step 5: Reassembly + Consistency Check

After all 5 chunks pass the Quality Gate:

1. **Merge** all final chunk versions back into `final_draft.md`
2. Re-attach frozen sections (metadata, methods, references)
3. **Auto-generate transition sentences** at chunk boundaries:
   - Between Results §1 → §2: connect the last finding of §1 to the first topic of §2
   - Between Results §2 → Discussion: bridge experimental findings to interpretation
4. Generate `consistency_checklist.md`:
   - **Terminology**: scan for variant spellings (s-SNOM/sSNOM, etc.) → standardize
   - **Numerics**: cross-check all numbers (Abstract vs Results vs Discussion)
   - **Cross-references**: verify all Figure/Equation references exist and are correct
   - **Equation numbering**: verify sequential numbering across all sections (no duplicates from separate chunks) (v5.2)
   - **Narrative flow**: check transitions between sections
   - **Style audit**: sSNOM vs s-SNOM, equation formatting, citation style
5. Fix any inconsistencies found
6. Save as `final_manuscript.md`

---

## Step 6: Figure-Text Alignment Check

Review each Figure caption against all text references to that Figure:

> For each Figure N:
> 1. Find all text passages that reference "Fig. N"
> 2. Check: does the text accurately describe what the caption says?
> 3. Check: are scale bars, axis labels, panel labels (a,b,c) referenced correctly?
> 4. Check: **panel reference format** matches journal style (e.g., "Fig. 1a" not "Fig. 1(a)" for Nature Photonics) (v5.2)
> 5. Flag any mismatches

**Action:** Append findings to `consistency_checklist.md`. Fix mismatches in `final_manuscript.md`.

---

## Step 7: Adversarial Reviewer (Recommended for Nature/Nature Photonics)

Simulate the harshest possible reviewer:

> "I am Reviewer #3 at Nature Photonics. I am skeptical of this work and looking for
> reasons to reject. I will challenge every core assumption, question every data point,
> and demand additional experiments or controls. I will check if the claimed novelty is
> truly novel by comparing to the 5 most relevant recent papers in the field.
> I will specifically check: (1) are enhancement factors measured correctly and not
> cherry-picked? (2) does the simulation match experiment? (3) are statistical claims
> valid? (4) is the mechanism fully explained or only asserted?"

**Action:**
1. Write adversarial review to `adversarial_review.md`
2. If any P0 issues found → fix in `final_manuscript.md`, loop back to Step 5
3. If only P1/P2 → add to `author_queries.md` and note as "potential reviewer concerns"

---

## Step 8: Cover Letter + Significance Statement

Generate `cover_letter_draft.md` containing:

1. **Significance Statement** (~100 words, distinct from Abstract):
   > Formula: "**We show** [novelty] **which enables** [impact] **unlike** [prior art] **because** [mechanism]."
   - Must be understandable by a physicist outside optics
   - Must not repeat the Abstract verbatim
2. **One-sentence novelty statement**: What makes this work different from everything before?
3. **Why this journal**: Why Nature Photonics (not ACS Photonics or Optica)?
4. **Broader significance**: Impact beyond the specific field
5. **Suggested reviewers** (from `reference_audit.md` + `reviewer_conflict_matrix.md`):
   - 3 suggested reviewers (cited favorably, non-competing)
   - 2 excluded reviewers (competing groups, potentially biased)
   - 2 uncited-but-relevant reviewers (editors often pick from these)
6. **Key figures**: Which figure best demonstrates the novelty (for potential cover art)?

---

## Step 9: Methods Audit (Optional)

Apply Academic Analyst to the Methods section:

> Check:
> - Are all experimental parameters specified (wavelength, power, NA, sample prep)?
> - Are all equipment models/manufacturers listed?
> - Could another group reproduce this experiment from these Methods alone?
> - Are statistical methods appropriate (N, error bars, p-values)?

**Action:** Write findings to `methods_audit.md`. Fix critical issues in `final_manuscript.md`.

---

## Final Output

When complete:
1. `final_manuscript.md` — ready for submission
2. `author_queries.md` — auto-collected from DEFERRED + Missing Controls (with Suggested Protocols)
3. `revision_history.md` — rolling-compressed record (R3 rounds never compressed)
4. `claim_evidence_matrix.md` — verified claim-evidence mapping with evidence types
5. `consistency_checklist.md` — cross-chunk consistency + equation numbering verification
6. `novelty_statement.md` — confirmed novelty positioning
7. `adversarial_review.md` — simulated harshest reviewer attack
8. `cover_letter_draft.md` — with Significance Statement, reviewer suggestions from conflict matrix
9. `reference_audit.md` — coverage gaps, recency analysis, self-citation ratio
10. `reviewer_conflict_matrix.md` — suggested/excluded/uncited-but-relevant reviewers

// turbo
## Completion Notification

When ALL steps above are finished, run this command to alert the user:

```powershell
[console]::beep(800,300); Start-Sleep -Milliseconds 200; [console]::beep(1000,300); Start-Sleep -Milliseconds 200; [console]::beep(1200,500)
```

Then tell the user: **"✅ 审稿流程已完成。请先查看 `author_queries.md`。"**
