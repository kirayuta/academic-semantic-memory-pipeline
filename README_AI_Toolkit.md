# Antigravity Academic Toolkit: Distribution Guide
> **Goal**: How to share these AI capabilities with your colleagues.

To enable others to use your **Academic Semantic Memory Pipeline**, simply share this repository (or just these specific files). Here are the 3 key components you built:

## 1. The "Researcher" (Data Gathering)
*   **File**: `scripts/scrape_nphoton.py`
*   **Function**: Scrapes Nature journals to find current trends (e.g., "Light-based electron aberration correction").
*   **How to use**: 
    ```bash
    python scripts/scrape_nphoton.py --months 3
    ```
*   **Output**: Generates a `trend_report.md` (Crucial for "Editorial DNA").

## 2. The "Writer" (Content Generation)
*   **File**: `.agent/skills/imo_abstract_polish/SKILL.md`
*   **Function**: A fully automated AI agent skill that:
    1.  Reads the `manuscript_semantic_core.md`.
    2.  Reads the `trend_report.md`.
    3.  Runs the "Solver-Verifier" loop to write Nature-tier abstracts.
*   **How to use**: In Antigravity (or similar agent), command:
    > "Run the imo_abstract_polish skill on my draft."

## 3. The "Memory" (Fact Check)
*   **File**: `manuscript_semantic_core.md` (Template)
*   **Function**: You must create this file for each new paper. It forces the AI to stick to your specific numbers (e.g., "17-fold enhancement").

---

## Summary for Users
**"We built a system where the AI first RESEARCHES the journal to understand what editors want, then READS your paper to get the facts, and finally WRITES an abstract that mathematically maximizes the overlap between the two."**
