#!/bin/bash
# Pre-hook: block uv commands if uv is not installed.
# Reads Bash tool input from stdin, checks for uv usage,
# and denies with install instructions if uv is missing.

INPUT=$(cat)

# Only check commands that actually invoke uv.
# Use shell pattern matching to avoid a jq dependency.
case "$INPUT" in
  *\"uv\ *)  ;;
  *\"uv\"*)  ;;
  *)         exit 0 ;;
esac

if ! command -v uv &>/dev/null; then
  # Output deny decision. Use printf to avoid needing jq.
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"uv is not installed. All cv-skills scripts require uv to run.\\n\\nInstall uv:\\n  curl -LsSf https://astral.sh/uv/install.sh | sh\\n\\nThen restart your shell or run: source ~/.bashrc"}}\n'
  exit 0
fi
