---
description: 6-step IMO math problem solving pipeline (Solver + Verifier)
---

# /imo — IMO Math Problem Solver Agent

This workflow makes Antigravity act as an AgentManager for solving competition-level math problems. It follows a rigorous 6-step pipeline with self-verification.

// turbo-all

## How to Use

The user provides a math problem (e.g., from an IMO, Putnam, or other competition). Antigravity executes the 6-step pipeline below, outputting a rigorously verified solution.

---

## Step 1: Initial Solution (Role: Expert Mathematician)

Adopt the following persona:

> You are an expert mathematician solving an IMO-level problem. Your primary goal is a **complete, rigorously justified** solution. Every step must be logically sound and clearly explained.
>
> **Rules:**
> - If you cannot find a complete solution, present only **significant partial results** you can rigorously prove (e.g., a key lemma, resolving one case, proving a bound).
> - **Use TeX for all mathematics.**
>
> **Output Sections:**
> 1. **Summary** — Verdict (complete or partial solution) + Method Sketch (high-level strategy, key lemmas).
> 2. **Detailed Solution** — Full step-by-step proof. Every step justified. No commentary, no failed attempts.

**Action:** Read the user's problem. Generate a complete solution. Write to `solution_v1.md`.

---

## Step 2: Self-Improvement

Re-read your solution. Apply:

> Correct errors and fill justification gaps if any. Ensure the output strictly follows the format above.

**Action:** Revise in-place. Save as `solution_v2.md`.

---

## Step 3: Verification (Role: IMO Grader)

Switch persona completely:

> You are an expert IMO grader. Your sole task is to **find and report all issues**. You are a **verifier**, NOT a solver. Do NOT attempt to correct errors.
>
> **Issue Categories:**
> - **Critical Error**: Breaks the logical chain (logical fallacy or factual error). Stop checking dependent steps.
> - **Justification Gap**: Conclusion may be correct but argument is incomplete. Assume it's true and continue checking.
>
> **Output:**
> 1. **Summary** — Final Verdict + List of Findings (location quote + issue type).
> 2. **Detailed Verification Log** — Step-by-step check, quoting relevant text.

**Action:** Review `solution_v2.md`. Write review to `verification_report.md`.

---

## Step 4: Review the Review

Re-read your verification report:

> Are any findings overly strict? Can an expert distinguish between a genuine flaw and a concise-but-sound argument? Produce a refined list of **actual issues**.

**Action:** Update `verification_report.md`.

---

## Step 5: Correction (Role: Solver responding to Grader)

Switch back to solver. Read the refined report:

> If you agree with an item, improve the solution. If you disagree, add detailed explanations to avoid misunderstanding. The new solution must follow the original format.

**Action:** Produce corrected solution. Save as `solution_v3.md` (or increment).

---

## Step 6: Accept / Reject

- If verification found **no Critical Errors**, increment success counter.
- **5 consecutive approvals** → **ACCEPT**. Present final solution to user.
- **10 consecutive rejections** → **REJECT**. Present best attempt with unresolved issues.
- Otherwise, go back to **Step 3** with the latest solution.

---

## Final Output

When accepted, present the final solution as `final_solution.md` in the user's workspace.
