#!/bin/bash
# Pre-hook: warn if neither resvg nor cairosvg is available before
# svg_convert.py render/resize-render commands.
# The info subcommand uses only stdlib XML parsing — no renderer needed.

INPUT=$(cat)

# Only check commands that invoke svg_convert.py with render subcommands
case "$INPUT" in
  *svg_convert*render*|*svg_convert*resize-render*)
    ;;
  *)
    exit 0
    ;;
esac

# Check for resvg binary
if command -v resvg &>/dev/null; then
  exit 0
fi

# Check for cairosvg Python package (import test via uv)
if command -v uv &>/dev/null; then
  if uv run python3 -c "import cairosvg" &>/dev/null; then
    exit 0
  fi
fi

# Neither available — deny with install instructions
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"No SVG renderer available. svg-convert render/resize-render requires one of:\\n\\n  1. resvg (recommended) — install the CLI binary:\\n     macOS:  brew install resvg\\n     other:  https://github.com/RazrFalcon/resvg/releases\\n\\n  2. cairosvg (fallback) — requires system libcairo2:\\n     macOS:  brew install cairo && uv pip install cairosvg\\n     Linux:  sudo apt install libcairo2-dev && uv pip install cairosvg\\n\\nThe info subcommand works without a renderer."}}\n'
exit 0
