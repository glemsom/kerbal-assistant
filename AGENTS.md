## Agent skills

### Rocket designs

Rocket reference data in `rockets/`. Each `.md` file documents a design:
part list, dV budget, staging order, ascent profile. New designs go here.

- `orbit-test-1.md` — 2-stage liquid rocket for 200 km Kerbin orbit

### Issue tracker

GitHub Issues (repo `glemsom/kerbal-assistant`). External PRs are NOT a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

All five canonical roles use their default label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo — one `CONTEXT.md` at root, one `docs/adr/`. See `docs/agents/domain.md`.

### Spawning Pi subagents in tmux

For parallel work on multiple issues, spawn Pi subagents in separate tmux windows.
Each subagent gets its own session and works independently.

**Pattern**:
```bash
# Create a shared session
tmux new-session -d -s kerbal-agents -n main "echo 'Agent swarm'"

# Spawn a subagent per issue
tmux new-window -t kerbal-agents -n issue-17 \
  "cd /home/glemsom/Documents/git/kerbal-assistant && \
   pi --session-id issue-17 -p \
   'Look at GitHub issue #17. Create branch. Implement. Commit. Push. PR.' 2>&1 | tee /tmp/pi-issue-17.log"
```

**Flags**:
- `--session-id <id>` — unique session to avoid conflicts
- `-p` — non-interactive mode (process and exit)
- `--model ...` — specify model

**Monitor**: `tmux attach -t kerbal-agents` or `cat /tmp/pi-issue-*.log`

**Caveats**:
- Subagents share the filesystem + git working tree. Use separate branches to avoid conflicts.
- Each subagent needs its own `--session-id` to avoid session file collisions.
- The `-p` flag makes Pi non-interactive — it processes the prompt and exits.
- Long-running subagents may take 30-90s depending on provider latency.

**Proof it works**: During initial implementation, a subagent for #17 discovered and fixed 12 `MirrorSymmetry`→`Mirror` values in `build-craft.py` that the primary agent missed (commit `2da8164`). The subagent verified the existing work, identified the gap, committed the fix, and pushed — all autonomously.
