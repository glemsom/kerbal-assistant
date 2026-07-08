# Self-Improvement Task

Use the **self-improve** skill. Execute the task below, evaluate yourself against the success criteria, improve `.pi/skills/*` if needed, then output FINAL SUMMARY.

---

## Task

Use the stock `Kerbal 1-5` rocket to get into about a 80km orbit around Kerbin.

## Success Criteria
- [ ] Reach an orbit between 75km and 100km
- [ ] Land the Mk1 command pod again in Kerbin
- [ ] Make efficient use of the different stages on the rocket
- [ ] Make use of RCS and SAS if needed (Optional)

## Self-Evaluation

Score 0–10 against the success criteria above. Use the **self-improve** skill for evaluation and improvement.

Be critical. If a knowledge gap hurt your score, edit the relevant `.pi/skills/*.md` to prevent it next iteration.

## Output

Print a FINAL SUMMARY line as the last line of output:

```
FINAL SUMMARY: SCORE=8 SUMMARY="Reached orbit at XXX km"

## Feedback

Run Pi with streaming output visible. Without `-p` flag, or use `tee`:

```
pi --session-id improve -p 'Execute improve-task.md' 2>&1 | tee /tmp/pi-improve.log
```

Watch the terminal — Pi prints all reasoning, commands, and results live.
Interrupt if it goes off-course, but let it finish normally for full evaluation.
