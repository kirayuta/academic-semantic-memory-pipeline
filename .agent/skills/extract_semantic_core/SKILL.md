---
name: extract_semantic_core
description: Compress a full academic manuscript into a 'Fact Base' (JSON-like Markdown) to prevent hallucinations.
version: 2.0.0
---

# Extract Semantic Core (Encoder Skill)

This skill acts as the "Encoder" in the AI Architecture. It reads a raw manuscript and losslessly compresses it into a structured Fact Base, Logic Graph, and Claims inventory.

## Inputs
*   `manuscript` (Required): The full text of the paper (md/txt/pdf).

> [!IMPORTANT]
> **Read ONLY these sections**: Abstract, Introduction, Results, Discussion.
> **Skip**: Methods, Acknowledgements, Author Contributions, References, Supplementary Information.
> This saves tokens — Methods/References do not contain claims or findings that belong in an abstract.

## Process (The "Compression" Logic)

### Step 1: Extract Hard Numbers (The "Fact Freeze")
Scan **Abstract, Introduction, Results, and Discussion** sections and extract **every** quantitative result:
- Enhancement factors (e.g., "17-fold improvement")
- Resolution / sensitivity metrics (e.g., "173 nm", "20 dB")
- Performance comparisons (e.g., "3× faster than state-of-the-art")
- Sample sizes, statistical significance (e.g., "n=50, p<0.01")
- Any other measurable outcomes

> [!IMPORTANT]
> **Enabling Capabilities Rule**: For each technical advantage, extract BOTH:
> 1. What it **avoids/suppresses** (e.g., "immune to fluorescence")
> 2. What it **enables/makes possible** (e.g., "enables simultaneous multiplexed fluorescence detection")
>
> Many advantages have a dual nature — the abstract should frame them as enabling, not just avoiding.
> Record both aspects in the Context column of the Fact Base.

> [!IMPORTANT]
> **Application Specificity Rule**: When the paper demonstrates an application, the Context column MUST include domain-specific details:
> - **Clinical/Biomedical**: Specific disease categories or organ systems (e.g., "liver, kidney, cardiovascular") + clinical standard compared against
> - **Materials/Devices**: Specific material systems, substrates, or device architectures (e.g., "silicon photonic waveguides", "MoS₂ monolayers") + characterization technique used
> - **Environmental/Industrial**: Specific analytes, matrices, or process conditions
>
> Generic phrases like "11 biomarkers" or "multiple samples" without domain context fail editorial scrutiny.

**Completeness Rule**: You MUST extract **at least one fact per Results paragraph/figure**. If a Results paragraph has data but you extracted nothing from it, go back and extract.

For each fact, record:
- The value
- The source (Figure/Table/Page number)
- The context (what was measured)
- **Priority**:
  - ★★★ = Must appear in Abstract (headline findings that match the Key Result in Logic Graph)
  - ★★ = Should appear if word count allows (strong supporting data)
  - ★ = For Verifier cross-check only (not expected in Abstract)

### Step 2: Map the Logic (The "Graph")
Identify the narrative chain:
- **Gap**: What problem does this paper solve? (one sentence)
- **Mechanism**: How does it solve it? (one sentence, technical)
- **Key Result**: What is the headline finding? (one sentence with numbers)
- **Impact**: Why does it matter? (one sentence, broader significance)
- **Novelty**: What is new compared to prior work? (one sentence)

### Step 3: Inventory Claims
List **every claim** made in the Abstract, Introduction ("Here we show..."), and Discussion. For each:
- The claim text (verbatim or paraphrased)
- Supporting evidence (which fact from Step 1 supports it, or "NO DATA SUPPORT")
- Claim strength: STRONG (direct data) / MODERATE (indirect) / WEAK (no evidence)

### Step 4: Save Output

> [!CAUTION]
> You **MUST** use the `write_to_file` tool to save the output to `manuscript_semantic_core.md`.
> Do NOT just print it in chat. The downstream skills (`imo_abstract_polish`, `/polish_abstract` workflow) depend on this file existing.

## Output Template

The output `manuscript_semantic_core.md` must follow this structure:

```markdown
# Manuscript Semantic Core

## 1. Fact Base (The Constraints)

| # | Priority | Metric | Value | Source | Context |
|:--|:--|:--|:--|:--|:--|
| F1 | ★★★ | [metric name] | [value] | Fig X / Table Y | [what was measured] |
| F2 | ★★ | ... | ... | ... | ... |
| F3 | ★ | ... | ... | ... | ... |

**Coverage check**: [N] facts from [M] Results paragraphs/figures.

## 2. Logic Graph (The Narrative)

- **Gap**: [One sentence]
- **Mechanism**: [One sentence]
- **Key Result**: [One sentence with numbers from Fact Base]
- **Impact**: [One sentence]
- **Novelty**: [One sentence]

## 3. Claims Inventory

| # | Claim | Source Section | Supporting Fact(s) | Strength |
|:--|:--|:--|:--|:--|
| C1 | [claim text] | Abstract / Intro / Discussion | F1, F3 | STRONG |
| C2 | [claim text] | Abstract | NO DATA SUPPORT | WEAK |
| ... | ... | ... | ... | ... |

**⚠ Unsupported claims**: [list any claims marked WEAK — these need attention]
```
