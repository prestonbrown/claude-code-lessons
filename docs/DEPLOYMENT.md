# Deployment Guide

This document explains how to install, update, and manage the coding-agent-lessons hooks for different AI coding assistants.

## Claude Code Deployment

### Installation

Claude Code hooks are installed to `~/.claude/hooks/`:

```bash
# Create hooks directory
mkdir -p ~/.claude/hooks

# Copy hook scripts
cp adapters/claude-code/inject-hook.sh ~/.claude/hooks/
cp adapters/claude-code/stop-hook.sh ~/.claude/hooks/

# Make executable
chmod +x ~/.claude/hooks/inject-hook.sh
chmod +x ~/.claude/hooks/stop-hook.sh

# Install core manager (creates symlink for hooks to find)
mkdir -p ~/.config/coding-agent-lessons
cp core/lessons-manager.sh ~/.config/coding-agent-lessons/
chmod +x ~/.config/coding-agent-lessons/lessons-manager.sh
```

### Claude Settings Configuration

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "~/.claude/hooks/inject-hook.sh"
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "~/.claude/hooks/stop-hook.sh"
      }
    ]
  }
}
```

### Updating Hooks

When the repository is updated:

```bash
# From repo directory
cp adapters/claude-code/inject-hook.sh ~/.claude/hooks/
cp adapters/claude-code/stop-hook.sh ~/.claude/hooks/
cp core/lessons-manager.sh ~/.config/coding-agent-lessons/
```

Or create an install script:

```bash
#!/bin/bash
# install-hooks.sh
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_HOOKS="$HOME/.claude/hooks"
LESSONS_BASE="$HOME/.config/coding-agent-lessons"

mkdir -p "$CLAUDE_HOOKS" "$LESSONS_BASE"
cp "$REPO_DIR/adapters/claude-code/inject-hook.sh" "$CLAUDE_HOOKS/"
cp "$REPO_DIR/adapters/claude-code/stop-hook.sh" "$CLAUDE_HOOKS/"
cp "$REPO_DIR/core/lessons-manager.sh" "$LESSONS_BASE/"
chmod +x "$CLAUDE_HOOKS"/*.sh "$LESSONS_BASE/lessons-manager.sh"
echo "Hooks installed successfully"
```

### File Locations Reference

| Location | Purpose |
|----------|---------|
| `~/.claude/hooks/inject-hook.sh` | SessionStart hook (injects lessons) |
| `~/.claude/hooks/stop-hook.sh` | Stop hook (tracks citations) |
| `~/.claude/settings.json` | Claude Code configuration |
| `~/.config/coding-agent-lessons/lessons-manager.sh` | Core manager script |
| `~/.config/coding-agent-lessons/LESSONS.md` | System-wide lessons |
| `~/.config/coding-agent-lessons/.decay-last-run` | Decay timestamp |
| `~/.config/coding-agent-lessons/.citation-state/` | Citation checkpoints |

### Relationship: Repo vs Installed

```
Repository (source of truth)          Installed (runtime)
━━━━━━━━━━━━━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━━━━━━━
adapters/claude-code/              → ~/.claude/hooks/
  inject-hook.sh                      inject-hook.sh
  stop-hook.sh                        stop-hook.sh

core/                              → ~/.config/coding-agent-lessons/
  lessons-manager.sh                  lessons-manager.sh
```

**Important**: The repository files are NOT used at runtime. Claude Code only reads from `~/.claude/hooks/`. Always reinstall after making changes.

## OpenCode Deployment

### Installation

OpenCode uses a TypeScript plugin system:

```bash
# Navigate to OpenCode plugins directory
cd ~/.opencode/plugins

# Clone or symlink the adapter
ln -s /path/to/coding-agent-lessons/adapters/opencode lessons-plugin

# Or copy files
mkdir -p lessons-plugin
cp -r /path/to/coding-agent-lessons/adapters/opencode/* lessons-plugin/
```

### Plugin Registration

Register in OpenCode's configuration (method depends on OpenCode version).

## Verifying Installation

### Check Hooks Are Installed

```bash
# Verify files exist
ls -la ~/.claude/hooks/
ls -la ~/.config/coding-agent-lessons/

# Check permissions
file ~/.claude/hooks/*.sh
file ~/.config/coding-agent-lessons/lessons-manager.sh
```

### Test Hook Execution

```bash
# Test inject hook (simulates SessionStart)
echo '{"cwd":"/tmp"}' | ~/.claude/hooks/inject-hook.sh

# Should output JSON with lessons context if lessons exist

# Test manager directly
~/.config/coding-agent-lessons/lessons-manager.sh list
```

### Verify in Claude Session

Start a new Claude Code session. You should see in the context:
- "LESSONS ACTIVE: X system (S###), Y project (L###)"
- Top lessons listed with star ratings
- "LESSON DUTY" reminder

## Disabling Temporarily

Add to `~/.claude/settings.json`:

```json
{
  "lessonsSystem": {
    "enabled": false
  }
}
```

Both hooks check this setting and exit early if disabled.

## Troubleshooting

### Hooks Not Running

1. **Check settings.json syntax**: Invalid JSON prevents hook registration
2. **Verify file permissions**: `chmod +x ~/.claude/hooks/*.sh`
3. **Check Claude Code version**: Hooks require Claude Code with hook support

### No Lessons Appearing

1. **Check lessons files exist**:
   ```bash
   ls ~/.config/coding-agent-lessons/LESSONS.md
   ls $PROJECT/.coding-agent-lessons/LESSONS.md
   ```
2. **Test manager directly**:
   ```bash
   ~/.config/coding-agent-lessons/lessons-manager.sh inject 5
   ```

### Citations Not Being Tracked

1. **Check checkpoint directory**:
   ```bash
   ls ~/.config/coding-agent-lessons/.citation-state/
   ```
2. **Verify transcript access**: Hook needs read access to Claude transcripts
3. **Check for jq errors**: `which jq` - jq must be installed

### Decay Not Running

1. **Check decay state file**:
   ```bash
   cat ~/.config/coding-agent-lessons/.decay-last-run
   ```
2. **Force decay manually**:
   ```bash
   ~/.config/coding-agent-lessons/lessons-manager.sh decay 30
   ```

## Backup and Migration

### Backup Lessons

```bash
# Backup system lessons
cp ~/.config/coding-agent-lessons/LESSONS.md ~/lessons-backup-$(date +%Y%m%d).md

# Backup project lessons (run from project root)
cp .coding-agent-lessons/LESSONS.md ~/project-lessons-backup-$(date +%Y%m%d).md
```

### Migrate to New Machine

1. Copy lesson files:
   ```bash
   scp old-machine:~/.config/coding-agent-lessons/LESSONS.md ~/.config/coding-agent-lessons/
   ```

2. Install hooks (see Installation above)

3. Decay state and checkpoints don't need migration (will regenerate)

## Version Compatibility

| Component | Requirement |
|-----------|-------------|
| Bash | 4.0+ (for associative arrays) |
| jq | 1.5+ |
| Claude Code | Hook support (check docs) |
| macOS | 10.15+ (for stat -f) |
| Linux | Any recent (for stat -c) |
