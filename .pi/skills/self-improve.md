---
name: self-improve
description: Self-evaluation and skill improvement. Use when running in a self-improvement loop — evaluate output against success criteria, identify skill gaps, and improve .pi/skills/* files.
---

# Self-Improvement Protocol

## When to Use

You are in a self-improvement loop. You have been given a task with:
1. A KSP-related task to execute
2. **Success criteria** — what "done" looks like
3. **Evaluation instructions** — how to score yourself

## Process

### 1. Execute the Task

Complete the task. Use any `.pi/skills/*` files available. Read rocket designs, run scripts if needed (e.g., `python scripts/dv-calc.py`).

### 2. Self-Evaluate

Compare your output against the success criteria. Be honest and critical — overestimating helps no one.

| Score | Meaning |
|-------|---------|
| 0-3 | Failed most criteria |
| 4-6 | Partial success, significant gaps |
| 7-9 | Met all criteria, minor gaps |
| 10 | Exceeded all criteria |

### 3. Improve Skills

If a knowledge gap hurt your score:
- Find the relevant `.pi/skills/<skill>.md` file
- Edit it to add the missing information concisely
- Do NOT break existing content or formatting
- If no existing skill fits, add to the most relevant one

### 4. Report

Print a **single FINAL SUMMARY line** as the last line of your output:

```
FINAL SUMMARY: SCORE=7 SUMMARY="Reached orbit but TWR was borderline" CHANGES="added TWR margin formula to delta-v-planning.md"
```

The string after each `=` is freeform except `SCORE` which BASH parses as a number. Keep `CHANGES` brief — it becomes the git commit body.

## Examples

### Good summary
```
FINAL SUMMARY: SCORE=8 SUMMARY="Rocket design met dV and TWR targets, staging plan correct" CHANGES="none needed"
```

### Summary after improvement
```
FINAL SUMMARY: SCORE=9 SUMMARY="Fixed lift/drag confusion. Ascent profile now targets proper max-q" CHANGES="added Eve ascent profile to ascent-profiles.md"
```

## Notes

- Only edit `.pi/skills/*` files. Do not edit the task file or BASH script.
- If score >= 9 and no improvement needed, set CHANGES to "none needed".
- The loop runs multiple iterations — improvements compound.
