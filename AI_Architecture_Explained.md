# AI-Driven Academic Writing Architecture (IMO Framework)

This document visualizes the "Modular AI Architecture" behind our workflow. By decoupling the process into distinct modules, you can optimize each step using the most suitable AI model (e.g., Gemini for context, Claude for style, o1 for logic).

## 1. The Core Architecture (IMO Framework)

```mermaid
graph TD
    subgraph "Phase 1: Knowledge Compression (The Encoder)"
        Raw[Raw Manuscript] -->|Gemini 1.5 Pro| FB[Fact Base (JSON)]
        Raw -->|Gemini 1.5 Pro| LG[Logic Graph (JSON)]
    end

    subgraph "Phase 2: Editorial Retrieval (The Planner)"
        Target[Target Journal (Nature)] -->|Search/Scrape| DNA[Editorial Pattern (Style Guide)]
    end

    subgraph "Phase 3: Generative Solve (The Writer)"
        FB -->|Claude 3.5 Sonnet / GPT-4o| Cand1[Candidate A (Safe)]
        FB -->|Claude 3.5 Sonnet / GPT-4o| Cand2[Candidate B (Physics)]
        DNA --> Cand1
        DNA --> Cand2
    end

    subgraph "Phase 4: Verification (The Critic)"
        Cand1 -->|o1 / Reasoning Model| Score1[Score Report]
        Cand2 -->|o1 / Reasoning Model| Score2[Score Report]
        FB --> Score1
    end

    Score1 -->|Selection| Final[Final Abstract]
```

## 2. Model Selection Strategy (How to Swap Models)

You can treat each module as a separate API call. Here is the recommended configuration for 2026:

| Module | Function | Recommended Model | Why? |
| :--- | :--- | :--- | :--- |
| **1. Encoder (Fact Extractor)** | **Read & Compress** | **Gemini 1.5 Pro** (2M Context) | **Best Context Window.** Can read entire thesis/codebase without "forgetting" early parts. Critical for extracting *accurate* facts. |
| **2. Retriever (Editorial DNA)** | **Trend Analysis** | **Perplexity / Search-Enabled AI** | **Best for RAG.** Needs live access to recent journal abstracts to analyze current trends. |
| **3. Solver (The Writer)** | **Draft Generation** | **Claude 3.5 Sonnet** or **GPT-4o** | **Best Stylistics.** Claude consistently outperforms others in "human-like" academic flow and vocabulary nuance. |
| **4. Verifier (The Judge)** | **Logic Check** | **OpenAI o1** or **Gemini 1.5 Pro (CoT)** | **Best Reasoning.** "Reasoning models" are less likely to hallucinate and better at strict logic checking (e.g., "Does 20dB really mean 17x?"). |

## 3. Implementation Logic (The Pseudocode)

```python
# Pseudo-code for IMO Loop

def run_imo_pipeline(manuscript, target_journal):
    # Step 1: Encoder (Fact Freeze)
    fact_base = Gemini_1_5.extract_facts(manuscript) 
    
    # Step 2: Retriever (Style)
    style_guide = WebAgent.analyze_journal(target_journal)
    
    # Step 3: Solver (Generate)
    candidates = []
    for angle in ["Safe", "Bold", "Hybrid"]:
        prompt = f"Write abstract using {style_guide} logic based on {fact_base} facts."
        draft = Claude_3_5.generate(prompt, temperature=0.7)
        candidates.append(draft)
        
    # Step 4: Verifier (Judge)
    scores = []
    for draft in candidates:
        critique = o1_Reasoning.evaluate(draft, criteria=fact_base)
        scores.append(critique.score)
        
    # Step 5: Assembly
    return max(scores, key=lambda x: x.value).draft
```

---
**Summary**: The power of this architecture lies in **Specialization**. Don't ask one model to do everything. Use the "Reader" to read, the "Writer" to write, and the "Logician" to judge.
