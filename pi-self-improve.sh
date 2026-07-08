#!/usr/bin/env bash
# pi-self-improve.sh — Self-improving loop for Pi Agent
#
# Runs a KSP task via `pi` for N iterations.
# Each iteration:
#   1. Executes the task (fresh session per iteration)
#   2. Parses the FINAL SUMMARY line from pi output
#   3. Commits any skill changes to git
#
# Usage:
#   ./pi-self-improve.sh --task <task.md> [--iterations N] [--session-base <name>] [--model <model>] [--timeout <sec>]

set -euo pipefail

# ---- defaults ----
ITERATIONS=10
TASK_FILE=""
SESSION_BASE="selfimprove"
MODEL="opencode-go/mimo-v2.5-pro"
ITER_TIMEOUT=300
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- trap signals ----
trap 'echo ""; echo "  ✋ Cancelled by user"; exit 130' INT TERM

# ---- helpers ----
usage() {
  echo "Usage: $0 [--iterations|-n N] [--session-base <name>] [--model <model>] [--timeout <sec>] --task|-t <task.md>"
  echo ""
  echo "Options:"
  echo "  -t, --task <file>       Task file (markdown, required)"
  echo "  -n, --iterations <N>    Iteration count (default: $ITERATIONS)"
  echo "  --session-base <name>   Prefix for pi session IDs (default: selfimprove)"
  echo "  --model <model>         Pi model to use (default: opencode-go/mimo-v2.5-pro)"
  echo "  --timeout <sec>         Per-iteration timeout in seconds (default: $ITER_TIMEOUT)"
  echo "  -h, --help              Show this message"
  exit 1
}

# ---- parse args ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --iterations|-n) ITERATIONS="$2"; shift 2 ;;
    --task|-t)       TASK_FILE="$2"; shift 2 ;;
    --session-base)  SESSION_BASE="$2"; shift 2 ;;
    --model)         MODEL="$2"; shift 2 ;;
    --timeout)       ITER_TIMEOUT="$2"; shift 2 ;;
    --help|-h)       usage ;;
    *)               echo "ERROR: Unknown argument '$1'"; usage ;;
  esac
done

# ---- validate ----
[[ -f "$TASK_FILE" ]] || { echo "ERROR: Task file not found: $TASK_FILE"; exit 1; }
[[ "$ITERATIONS" =~ ^[0-9]+$ ]] && [[ "$ITERATIONS" -gt 0 ]] || { echo "ERROR: Iterations must be positive integer, got '$ITERATIONS'"; exit 1; }
[[ "$ITER_TIMEOUT" =~ ^[0-9]+$ ]] && [[ "$ITER_TIMEOUT" -gt 0 ]] || { echo "ERROR: Timeout must be positive integer, got '$ITER_TIMEOUT'"; exit 1; }
command -v pi &>/dev/null || { echo "ERROR: 'pi' command not found. Install Pi agent first."; exit 1; }

# ---- setup ----
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
cd "$REPO_ROOT"

# Verify it's a git repo
git rev-parse --git-dir &>/dev/null || { echo "ERROR: Not a git repository"; exit 1; }

# Warn about dirty state — task file changes are read into memory
if [[ -n "$(git status --porcelain)" ]]; then
  echo "NOTE: Dirty working tree. Uncommitted changes will be included in iteration 1 commit."
  echo "      To start clean: git stash push -m 'pre-selfimprove'"
fi

RESULTS_FILE="${SCRIPT_DIR}/self-improve-results-$(date +%Y%m%d-%H%M%S).log"
TASK_BASENAME="$(basename "$TASK_FILE")"

# ---- header ----
echo "==========================================="
echo "  Pi Self-Improve Loop"
echo "  Repo:      $REPO_ROOT"
echo "  Task:      $TASK_FILE"
echo "  Iterations: $ITERATIONS"
echo "  Model:     $MODEL"
echo "  Timeout:   ${ITER_TIMEOUT}s/iter"
echo "  Results:   $RESULTS_FILE"
echo "==========================================="
echo ""

# ---- loop ----
PREV_SCORE=

for ((i=1; i<=ITERATIONS; i++)); do
  echo ""
  echo "═══════════════════════════════════════════"
  echo "  Iteration $i/$ITERATIONS"
  echo "  Session:  ${SESSION_BASE}-iter${i}"
  echo "  Time:     $(date '+%H:%M:%S')"
  echo "═══════════════════════════════════════════"

  SESSION_ID="${SESSION_BASE}-iter${i}"
  START_AT="$(date +%s)"

  # Write task to temp file for @file syntax
  TASK_TMPFILE=$(mktemp)
  cat "$TASK_FILE" > "$TASK_TMPFILE"

  # Run pi with task (fresh context per iteration) — with timeout, live output
  TMP_OUTPUT=$(mktemp)
  echo "  ▶ Starting pi (timeout=${ITER_TIMEOUT}s, model=${MODEL})..."

  timeout "$ITER_TIMEOUT" pi \
    --session-id "$SESSION_ID" \
    --model "$MODEL" \
    --print \
    --exclude-tools bash \
    @"$TASK_TMPFILE" \
    2>&1 | tee "$TMP_OUTPUT"
  EXIT_CODE=${PIPESTATUS[0]}
  DURATION=$(( $(date +%s) - START_AT ))
  rm -f "$TASK_TMPFILE"

  # Parse FINAL SUMMARY line from output
  SUMMARY="$(grep "^FINAL SUMMARY:" "$TMP_OUTPUT" | tail -1)"
  if [[ -z "$SUMMARY" ]]; then
    SCORE="??"
    CHANGES="no-summary-line"
    echo "  ⚠ WARN: No FINAL SUMMARY line (exit=$EXIT_CODE)"
    if [[ $EXIT_CODE -eq 124 ]]; then
      echo "  ── TIMEOUT after ${ITER_TIMEOUT}s ──"
    else
      echo "  ── Last 10 lines of output ──"
      tail -10 "$TMP_OUTPUT"
    fi
  else
    SCORE="$(echo "$SUMMARY" | sed 's/.*SCORE=//' | sed 's/[[:space:]].*//' || echo "parse-error")"
    CHANGES="$(echo "$SUMMARY" | sed 's/.*CHANGES=//' || echo "parse-error")"
  fi
  rm -f "$TMP_OUTPUT"

  # Score progression arrow
  DELTA=
  if [[ -n "$PREV_SCORE" && "$SCORE" != "??" && "$PREV_SCORE" != "??" ]]; then
    if (( $(echo "$SCORE > $PREV_SCORE" | bc -l 2>/dev/null || echo 0) )); then
      DELTA=" ↑"
    elif (( $(echo "$SCORE < $PREV_SCORE" | bc -l 2>/dev/null || echo 0) )); then
      DELTA=" ↓"
    else
      DELTA=" →"
    fi
  fi
  PREV_SCORE="$SCORE"

  LOG_LINE="$(date +%Y-%m-%d\ %H:%M:%S) | iter=$i | dur=${DURATION}s | exit=$EXIT_CODE | score=$SCORE$DELTA | changes=$CHANGES"
  echo ""
  echo "  ── Result ──────────────────────────────"
  echo "  Duration: ${DURATION}s  |  Exit: $EXIT_CODE"
  echo "  Score:    ${SCORE}${DELTA}  |  Changes: $CHANGES"
  echo "  ────────────────────────────────────────"
  echo "$LOG_LINE" >> "$RESULTS_FILE"

  # Git commit any changes
  if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    git add -A 2>/dev/null || true
    git commit -m "self-improve: iter $i/$ITERATIONS score=$SCORE" \
               -m "Task: $TASK_BASENAME" \
               -m "Duration: ${DURATION}s | Changes: $CHANGES" \
               2>/dev/null || echo "  (commit: nothing new)"
  else
    echo "  (no file changes)"
  fi

  echo ""
done

# ---- summary ----
echo "==========================================="
echo "  Loop Complete"
echo "==========================================="
echo ""
echo "Results log: $RESULTS_FILE"
echo ""
# Pretty print the results log
if command -v column &>/dev/null; then
  column -t -s '|' "$RESULTS_FILE"
else
  cat "$RESULTS_FILE"
fi

# Print score progression
echo ""
echo "Score progression:"
grep -oP 'score=\K[0-9.]+|score=\K\?\?' "$RESULTS_FILE" | tr '\n' ' → ' && echo ""
