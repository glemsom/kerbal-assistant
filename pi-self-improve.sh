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
#   ./pi-self-improve.sh --task <task.md> [--iterations N] [--session-base <name>]

set -euo pipefail

# ---- defaults ----
ITERATIONS=10
TASK_FILE=""
SESSION_BASE="selfimprove"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- helpers ----
usage() {
  echo "Usage: $0 [--iterations|-n N] [--session-base <name>] --task|-t <task.md>"
  echo ""
  echo "Options:"
  echo "  -t, --task <file>       Task file (markdown, required)"
  echo "  -n, --iterations <N>    Iteration count (default: 10)"
  echo "  --session-base <name>   Prefix for pi session IDs (default: selfimprove)"
  echo "  -h, --help              Show this message"
  exit 1
}

# ---- parse args ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --iterations|-n) ITERATIONS="$2"; shift 2 ;;
    --task|-t)       TASK_FILE="$2"; shift 2 ;;
    --session-base)  SESSION_BASE="$2"; shift 2 ;;
    --help|-h)       usage ;;
    *)               echo "ERROR: Unknown argument '$1'"; usage ;;
  esac
done

# ---- validate ----
[[ -f "$TASK_FILE" ]] || { echo "ERROR: Task file not found: $TASK_FILE"; exit 1; }
[[ "$ITERATIONS" =~ ^[0-9]+$ ]] && [[ "$ITERATIONS" -gt 0 ]] || { echo "ERROR: Iterations must be positive integer, got '$ITERATIONS'"; exit 1; }
command -v pi &>/dev/null || { echo "ERROR: 'pi' command not found. Install Pi agent first."; exit 1; }

# ---- setup ----
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
cd "$REPO_ROOT"

# Verify it's a git repo
git rev-parse --git-dir &>/dev/null || { echo "ERROR: Not a git repository"; exit 1; }

# Check for unstaged changes before starting
if [[ -n "$(git status --porcelain)" ]]; then
  echo "WARNING: Uncommitted changes detected. Stashing..."
  git stash --include-untracked || true
fi

RESULTS_FILE="${SCRIPT_DIR}/self-improve-results-$(date +%Y%m%d-%H%M%S).log"
TASK_CONTENT="$(cat "$TASK_FILE")"
TASK_BASENAME="$(basename "$TASK_FILE")"

# ---- header ----
echo "==========================================="
echo "  Pi Self-Improve Loop"
echo "  Repo:      $REPO_ROOT"
echo "  Task:      $TASK_FILE"
echo "  Iterations: $ITERATIONS"
echo "  Results:   $RESULTS_FILE"
echo "==========================================="
echo ""

# ---- loop ----
for ((i=1; i<=ITERATIONS; i++)); do
  echo "--- Iteration $i/$ITERATIONS ---"

  SESSION_ID="${SESSION_BASE}-iter${i}"
  START_AT="$(date +%s)"

  # Run pi with task (fresh context per iteration)
  OUTPUT="$(pi --session-id "$SESSION_ID" -p "$TASK_CONTENT" 2>&1)"
  EXIT_CODE=$?
  DURATION=$(( $(date +%s) - START_AT ))

  # Parse FINAL SUMMARY line
  SUMMARY="$(echo "$OUTPUT" | grep "^FINAL SUMMARY:" | tail -1)"
  if [[ -z "$SUMMARY" ]]; then
    SCORE="??"
    CHANGES="no-summary-line"
    echo "  WARN: No FINAL SUMMARY line in output (exit=$EXIT_CODE)"
    echo "  -- Last 5 lines of output --"
    echo "$OUTPUT" | tail -5
  else
    SCORE="$(echo "$SUMMARY" | sed 's/.*SCORE=//' | sed 's/[[:space:]].*//' || echo "parse-error")"
    CHANGES="$(echo "$SUMMARY" | sed 's/.*CHANGES=//' || echo "parse-error")"
  fi

  LOG_LINE="$(date +%Y-%m-%d\ %H:%M:%S) | iter=$i | dur=${DURATION}s | exit=$EXIT_CODE | score=$SCORE | changes=$CHANGES"
  echo "  $LOG_LINE"
  echo "$LOG_LINE" >> "$RESULTS_FILE"

  # Git commit any changes
  if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    git add -A 2>/dev/null || true
    git commit -m "self-improve: iter $i/$ITERATIONS score=$SCORE" \
               -m "Task: $TASK_BASENAME" \
               -m "Duration: ${DURATION}s | Changes: $CHANGES" \
               2>/dev/null || echo "  (nothing to commit)"
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
