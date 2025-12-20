#!/bin/bash
# SPDX-License-Identifier: MIT
# Claude Code SessionStart hook - injects lessons context

set -euo pipefail

MANAGER="$HOME/.config/coding-agent-lessons/lessons-manager.sh"

# Check if enabled
is_enabled() {
    local config="$HOME/.claude/settings.json"
    [[ -f "$config" ]] && {
        local enabled=$(jq -r '.lessonsSystem.enabled // true' "$config" 2>/dev/null || echo "true")
        [[ "$enabled" == "true" ]]
    } || return 0
}

main() {
    is_enabled || exit 0
    
    local input=$(cat)
    local cwd=$(echo "$input" | jq -r '.cwd // "."' 2>/dev/null || echo ".")
    
    # Generate lessons context
    local summary=$(PROJECT_DIR="$cwd" "$MANAGER" inject 5 2>/dev/null || true)
    
    if [[ -n "$summary" ]]; then
        # Add lesson duty reminder
        summary="$summary

LESSON DUTY: When user corrects you, something fails, or you discover a pattern:
  ASK: \"Should I record this as a lesson? [category]: title - content\""
        
        local escaped=$(printf '%s' "$summary" | jq -Rs .)
        cat << EOF
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":$escaped}}
EOF
    fi
    exit 0
}

main
