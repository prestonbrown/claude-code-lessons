# Development Guide

This document covers the architecture, testing, and development workflow for the coding-agent-lessons system.

## Architecture Overview

The system consists of three main layers:

```
┌─────────────────────────────────────────────────────────────┐
│                       AI Agent                               │
│  (Claude Code, OpenCode, etc.)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Adapters Layer                            │
│  ┌─────────────────────┐    ┌─────────────────────┐         │
│  │   claude-code/      │    │    opencode/        │         │
│  │   - inject-hook.sh  │    │    - plugin.ts      │         │
│  │   - stop-hook.sh    │    │    - command/       │         │
│  └─────────────────────┘    └─────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              lessons-manager.sh                          │ │
│  │  - add/remove/list lessons                               │ │
│  │  - cite (increment uses)                                 │ │
│  │  - inject (generate context)                             │ │
│  │  - decay (reduce stale lesson uses)                      │ │
│  │  - promote (project → system)                            │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer                            │
│  ~/.config/coding-agent-lessons/                             │
│  ├── LESSONS.md           # System-wide lessons              │
│  ├── .decay-last-run      # Decay timestamp                  │
│  └── .citation-state/     # Per-session checkpoints          │
│                                                              │
│  $PROJECT/.coding-agent-lessons/                             │
│  └── LESSONS.md           # Project-specific lessons         │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### lessons-manager.sh

The central script that manages all lesson operations. Located at `core/lessons-manager.sh`.

**Key Commands:**

| Command | Description |
|---------|-------------|
| `add <category> <title> <content>` | Add project lesson |
| `add-system <category> <title> <content>` | Add system lesson |
| `cite <id>` | Increment uses for a lesson |
| `inject <count>` | Generate context for AI injection |
| `list` | List all lessons |
| `decay <days>` | Reduce uses for stale lessons |
| `promote <id>` | Promote project lesson to system |

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `LESSONS_BASE` | `~/.config/coding-agent-lessons` | Base directory for system lessons |
| `PROJECT_DIR` | Current directory | Project root for project lessons |

### Citation Checkpointing

The stop hook uses timestamp-based checkpointing to process citations incrementally:

1. **First run**: Process all assistant messages, save latest timestamp
2. **Subsequent runs**: Only process messages newer than checkpoint
3. **Storage**: `~/.config/coding-agent-lessons/.citation-state/<session-id>`

This avoids the 50KB stdin limit and scales to arbitrary conversation lengths.

### Decay System

Lessons accumulate stars through citations but can become stale. The decay system addresses this:

**Activity-Aware Decay:**
- Runs automatically once per week (triggered by inject-hook)
- Only decays if coding sessions occurred since last decay
- If no sessions (vacation mode), lessons are preserved
- Reduces uses by 1 per decay run for lessons not cited in 30+ days
- Never reduces below 1 (lessons aren't auto-deleted)

**Files:**
- `.decay-last-run`: Unix timestamp of last decay execution
- Checkpoint file modification times indicate session activity

### Orphaned Checkpoint Cleanup

Checkpoint files can become orphaned when Claude deletes old transcripts:

- Runs opportunistically on each stop-hook invocation
- Cleans up to 10 orphaned checkpoints per run
- Only deletes checkpoints older than 7 days with no matching transcript
- Safe defaults: if stat fails, treats file as new (won't delete)

## Adapters

### Claude Code Adapter

Two shell scripts that hook into Claude Code's event system:

**inject-hook.sh** (SessionStart event):
- Injects lesson context at conversation start
- Triggers weekly decay check in background
- Adds "LESSON DUTY" reminder

**stop-hook.sh** (Stop event):
- Tracks lesson citations from AI responses
- Uses incremental checkpointing
- Cleans orphaned checkpoints opportunistically

### OpenCode Adapter

A TypeScript plugin that hooks into OpenCode events:

**plugin.ts**:
- `session.created`: Injects lessons context
- `session.idle`: Tracks citations (with in-memory checkpointing)
- `message.updated`: Captures `LESSON:` commands from user

## Testing

### Running Tests

```bash
# Run all tests
./tests/test-stop-hook.sh

# Run specific test
./tests/test-stop-hook.sh test_basic_citation
```

### Test Structure

Tests use a simple framework in `test-stop-hook.sh`:

```bash
test_example() {
    # Setup
    create_fake_transcript "..."

    # Execute
    run_hook

    # Assert
    assert_contains "$output" "expected"
    assert_file_exists "$file"
}
```

### Current Test Coverage (18 tests)

| Category | Tests |
|----------|-------|
| Basic functionality | 5 |
| Checkpointing | 4 |
| Edge cases | 4 |
| Cleanup | 2 |
| Decay | 3 |

### Adding New Tests

1. Add test function in `tests/test-stop-hook.sh`
2. Follow naming convention: `test_<description>`
3. Use helper functions: `create_fake_transcript`, `run_hook`, `assert_*`
4. Run full suite to verify

## Development Workflow

### Making Changes

1. **Edit core logic**: Modify `core/lessons-manager.sh`
2. **Edit hooks**: Modify files in `adapters/claude-code/`
3. **Run tests**: `./tests/test-stop-hook.sh`
4. **Install hooks**: See [Deployment Guide](docs/DEPLOYMENT.md)

### Code Style

- Shell scripts use `set -euo pipefail` (or `-uo pipefail` for hooks that need graceful failure)
- Use `local` for all function variables
- Quote all variable expansions: `"$var"` not `$var`
- Use `[[ ]]` for conditionals (bash-specific)
- Add comments for non-obvious logic

### Common Patterns

**Safe file operations:**
```bash
# Check file exists before reading
[[ -f "$file" ]] || return 0

# Create directory if needed
mkdir -p "$dir"

# Safe stat with fallback
mtime=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null || echo "")
```

**Two-phase updates (avoid stale reads):**
```bash
# PHASE 1: Collect items to modify
local items_to_update=()
while read -r item; do
    items_to_update+=("$item")
done < "$file"

# PHASE 2: Apply updates with fresh reads
for item in "${items_to_update[@]}"; do
    # Re-read current state before modifying
    current_value=$(grep ... "$file")
    update_value "$item" "$new_value" "$file"
done
```

**Numeric validation:**
```bash
# Strip non-numeric characters
value=$(head -1 "$file" 2>/dev/null | tr -dc '0-9')
[[ -z "$value" ]] && value=0
```

## Debugging

### Enable Debug Output

For inject-hook and stop-hook, temporarily add:
```bash
exec 2>/tmp/lessons-debug.log
set -x
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Citations not tracked | Checkpoint too new | Delete session checkpoint file |
| Decay not running | No sessions detected | Create a checkpoint file |
| Hook not triggering | Not installed | Run install command |
| jq parse error | Invalid JSON | Check transcript file format |

### Inspecting State

```bash
# View system lessons
cat ~/.config/coding-agent-lessons/LESSONS.md

# View decay state
cat ~/.config/coding-agent-lessons/.decay-last-run

# List checkpoints
ls -la ~/.config/coding-agent-lessons/.citation-state/

# Check a specific checkpoint
cat ~/.config/coding-agent-lessons/.citation-state/<session-id>
```

## Future Improvements

Potential areas for enhancement:

1. **Decay granularity**: Per-lesson decay rates based on category
2. **Citation analytics**: Track which lessons are most useful
3. **Lesson dependencies**: Link related lessons
4. **Export/import**: Share lessons between systems
5. **Web UI**: Visual lesson management interface
