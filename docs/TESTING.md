# Testing Guide

This document covers the testing infrastructure, how to run tests, and how to add new tests.

## Test Framework

The test suite uses a lightweight bash-based framework in `tests/test-stop-hook.sh`. It provides:

- Isolated test environments (temporary directories)
- Helper functions for common operations
- Assertion utilities
- Automatic cleanup

## Running Tests

```bash
# Run all tests
./tests/test-stop-hook.sh

# Output shows pass/fail for each test
# Example:
#   PASS: test_basic_citation
#   PASS: test_checkpoint_created_after_first_run
#   ...
#   ════════════════════════════════════════
#   Results: 18 passed, 0 failed
```

## Test Categories

### Basic Functionality (5 tests)

| Test | Purpose |
|------|---------|
| `test_basic_citation` | Citations are tracked and manager called |
| `test_multiple_citations` | Multiple distinct citations in one message |
| `test_no_citations` | No errors when no citations present |
| `test_disabled_via_settings` | Respects enabled=false setting |
| `test_system_lesson_citation` | S### citations work like L### |

### Checkpointing (4 tests)

| Test | Purpose |
|------|---------|
| `test_checkpoint_created_after_first_run` | State file created |
| `test_incremental_processing` | Only new messages processed |
| `test_checkpoint_updated_even_without_citations` | Checkpoint advances regardless |
| `test_first_run_processes_all` | Initial run sees all history |

### Edge Cases (4 tests)

| Test | Purpose |
|------|---------|
| `test_ignores_listing_format` | `[L001] [*****` not counted as citation |
| `test_empty_transcript` | Handles empty file gracefully |
| `test_malformed_json` | Handles invalid JSON gracefully |
| `test_missing_transcript` | Handles missing file gracefully |

### Cleanup (2 tests)

| Test | Purpose |
|------|---------|
| `test_cleanup_removes_old_orphans` | Orphaned checkpoints >7 days deleted |
| `test_cleanup_keeps_recent_orphans` | Recent orphans preserved |

### Decay (3 tests)

| Test | Purpose |
|------|---------|
| `test_decay_reduces_stale_lesson_uses` | Uses decremented for old lessons |
| `test_decay_skips_without_activity` | No decay if no sessions occurred |
| `test_decay_never_below_one` | Uses never goes below 1 |

## Test Environment

Each test runs in an isolated environment:

```bash
# Temporary directories created per-test
TEST_HOME=/tmp/test-lessons-XXXXX
├── .claude/
│   ├── settings.json
│   └── projects/
│       └── test-project/
│           └── <session-id>.jsonl
├── .config/
│   └── coding-agent-lessons/
│       ├── lessons-manager.sh → (symlink to real manager)
│       ├── LESSONS.md
│       └── .citation-state/
└── test-project/
    └── .coding-agent-lessons/
        └── LESSONS.md
```

## Helper Functions

### Test Setup

```bash
setup_test_env() {
    # Creates isolated temp directory
    # Sets up directory structure
    # Configures HOME override
    # Symlinks manager script
}

teardown_test_env() {
    # Cleans up temp directory
    # Restores original HOME
}
```

### Transcript Creation

```bash
create_fake_transcript() {
    local content="$1"
    local session_id="${2:-$(uuidgen)}"
    # Creates JSONL transcript file
    # Returns path to transcript
}

# Example usage:
create_fake_transcript '{
    "type": "assistant",
    "timestamp": "2024-01-15T10:00:00Z",
    "message": {
        "content": [{"type": "text", "text": "Applying [L001]: some lesson"}]
    }
}'
```

### Hook Execution

```bash
run_hook() {
    local transcript="$1"
    # Invokes stop-hook.sh with proper input
    # Captures stdout/stderr
    # Returns exit code
}

run_inject_hook() {
    # Invokes inject-hook.sh
    # Returns lesson context output
}
```

### Assertions

```bash
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="$3"
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="$3"
}

assert_file_exists() {
    local path="$1"
    local message="$2"
}

assert_file_not_exists() {
    local path="$1"
    local message="$2"
}

assert_file_contains() {
    local path="$1"
    local pattern="$2"
    local message="$3"
}
```

## Writing New Tests

### Basic Structure

```bash
test_my_new_feature() {
    # 1. Setup - create test data
    local transcript=$(create_fake_transcript '...')

    # 2. Execute - run the code under test
    local output=$(run_hook "$transcript" 2>&1)
    local exit_code=$?

    # 3. Assert - verify results
    assert_equals 0 $exit_code "Hook should succeed"
    assert_contains "$output" "expected text"
    assert_file_exists "$STATE_DIR/session-id"
}
```

### Testing Decay

```bash
test_decay_example() {
    # Create lesson with old Last date
    create_lesson "L001" "Test" "**Uses**: 5, **Last**: 2024-01-01"

    # Create checkpoint to indicate activity
    touch "$STATE_DIR/fake-session"

    # Run decay
    local output=$("$MANAGER" decay 30 2>&1)

    # Verify uses decreased
    assert_file_contains "$LESSONS_FILE" "**Uses**: 4"
}
```

### Testing Cleanup

```bash
test_cleanup_example() {
    # Create orphaned checkpoint (no matching transcript)
    local orphan="$STATE_DIR/orphaned-session-id"
    echo "2024-01-01T00:00:00Z" > "$orphan"

    # Backdate file (macOS)
    touch -t 202401010000 "$orphan"

    # Run hook (triggers cleanup)
    run_hook "$(create_fake_transcript '{}')"

    # Verify orphan removed
    assert_file_not_exists "$orphan"
}
```

## Debugging Tests

### Verbose Output

Add debug output to see what's happening:

```bash
test_debug_example() {
    set -x  # Enable bash tracing

    local transcript=$(create_fake_transcript '...')
    echo "Created transcript: $transcript" >&2

    local output=$(run_hook "$transcript" 2>&1)
    echo "Hook output: $output" >&2

    set +x  # Disable tracing
}
```

### Inspect Test Environment

```bash
test_inspect_env() {
    # Don't clean up at end
    KEEP_TEST_ENV=1

    # ... run test ...

    echo "Test env at: $TEST_HOME" >&2
    # Manually inspect files after test
}
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "command not found: jq" | jq not in PATH during test | Ensure jq is installed |
| Manager script not found | Symlink not created | Check `ln -sf` in setup |
| Citations not detected | Transcript format wrong | Check JSONL structure |
| Checkpoint not created | Missing transcript_path in input | Add to hook input JSON |

## Mock Manager

Tests use a mock manager that logs calls instead of modifying real files:

```bash
# Mock manager logs calls to a file
mock_manager() {
    echo "CALLED: $*" >> "$MOCK_LOG"
    case "$1" in
        cite)
            echo "OK: Cited $2"
            ;;
        inject)
            echo "[S001] Test lesson"
            ;;
        *)
            echo "OK"
            ;;
    esac
}
```

## Continuous Integration

Tests can run in CI environments:

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: sudo apt-get install -y jq
      - name: Run tests
        run: ./tests/test-stop-hook.sh
```

### CI Considerations

- Tests use `/tmp` for isolation (works on Linux/macOS)
- `stat` command differs between macOS (-f) and Linux (-c)
- Tests handle both variants
- UUID generation via `uuidgen` (install if missing)
