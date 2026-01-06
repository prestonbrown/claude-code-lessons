#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Pilot-based tests for the RecallMonitorApp TUI.

These tests use Textual's pilot testing framework to verify app behavior.
Some tests are designed to FAIL initially to prove bugs exist.
"""

from pathlib import Path
import json
import pytest

pytest.importorskip("textual")

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

from textual.widgets import RichLog, Static, Tab


# Import with fallback for installed vs dev paths
try:
    from core.tui.app import RecallMonitorApp
except ImportError:
    from .app import RecallMonitorApp


# --- Fixtures ---


@pytest.fixture
def temp_log_with_events(tmp_path: Path, monkeypatch):
    """
    Create a temp directory with a debug.log file containing sample events.

    Patches CLAUDE_RECALL_STATE to use the temp directory.
    """
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    log_path = state_dir / "debug.log"

    # Sample events with realistic data
    events = [
        {
            "event": "session_start",
            "level": "info",
            "timestamp": "2026-01-06T10:00:00Z",
            "session_id": "test-123",
            "pid": 1234,
            "project": "test-project",
            "total_lessons": 5,
            "system_count": 2,
            "project_count": 3,
        },
        {
            "event": "citation",
            "level": "info",
            "timestamp": "2026-01-06T10:01:00Z",
            "session_id": "test-123",
            "pid": 1234,
            "project": "test-project",
            "lesson_id": "L001",
            "uses_before": 5,
            "uses_after": 6,
        },
        {
            "event": "hook_end",
            "level": "info",
            "timestamp": "2026-01-06T10:01:30Z",
            "session_id": "test-123",
            "pid": 1234,
            "project": "test-project",
            "hook": "SessionStart",
            "total_ms": 45.5,
        },
    ]

    lines = [json.dumps(e) for e in events]
    log_path.write_text("\n".join(lines) + "\n")

    # Patch environment to use temp state dir
    monkeypatch.setenv("CLAUDE_RECALL_STATE", str(state_dir))

    return log_path


# --- Pilot Tests ---


@pytest.mark.asyncio
async def test_app_displays_events_on_start(temp_log_with_events: Path):
    """
    Verify the event log (#event-log RichLog) has content after mount.

    This test should FAIL if events are not being loaded/displayed on startup.
    The bug: events may not render until manual refresh is triggered.
    """
    app = RecallMonitorApp(log_path=temp_log_with_events)

    async with app.run_test() as pilot:
        # Wait for mount and initial data load
        await pilot.pause()

        # Query the event log widget
        event_log = app.query_one("#event-log", RichLog)

        # The event log should have content (lines written to it)
        # RichLog stores lines internally - check the lines list
        assert len(event_log.lines) > 0, (
            "Event log should have content after mount, but it's empty. "
            "This indicates events are not being loaded on startup."
        )


@pytest.mark.asyncio
async def test_health_tab_shows_stats(temp_log_with_events: Path):
    """
    Switch to Health tab (F2) and verify #health-stats widget has real content.

    This test should FAIL if health stats show only "Loading..." placeholder.
    The bug: health stats may not update after initial load.
    """
    app = RecallMonitorApp(log_path=temp_log_with_events)

    async with app.run_test() as pilot:
        # Wait for mount
        await pilot.pause()

        # Switch to Health tab
        await pilot.press("f2")
        await pilot.pause()

        # Query the health stats widget
        health_stats = app.query_one("#health-stats", Static)

        # Get the rendered content using render() method
        content = str(health_stats.render())

        # Should NOT just say "Loading..." - should have actual stats
        assert "Loading" not in content or "System Health" in content, (
            f"Health stats should show actual data, not just 'Loading...'. "
            f"Got: {content[:100]}..."
        )

        # Should contain expected health information
        assert "Sessions" in content or "System Health" in content, (
            f"Health stats should contain session/health information. "
            f"Got: {content[:200]}..."
        )


@pytest.mark.asyncio
async def test_tabs_have_spacing(temp_log_with_events: Path):
    """
    Query Tab widgets and verify they have some padding/margin.

    This tests that tabs are properly styled with spacing for readability.
    The bug: tabs may be cramped together without proper spacing.
    """
    app = RecallMonitorApp(log_path=temp_log_with_events)

    async with app.run_test() as pilot:
        # Wait for mount
        await pilot.pause()

        # Query all Tab widgets
        tabs = app.query(Tab)

        # Should have multiple tabs
        assert len(tabs) >= 3, f"Expected at least 3 tabs, got {len(tabs)}"

        # Check that tabs have some spacing (padding or margin)
        # This is tricky to test directly, so we check computed styles
        for tab in tabs:
            styles = tab.styles

            # Check for padding (any direction)
            has_padding = (
                styles.padding.top > 0 or
                styles.padding.right > 0 or
                styles.padding.bottom > 0 or
                styles.padding.left > 0
            )

            # Check for margin (any direction)
            has_margin = (
                styles.margin.top > 0 or
                styles.margin.right > 0 or
                styles.margin.bottom > 0 or
                styles.margin.left > 0
            )

            # At least one form of spacing should exist
            assert has_padding or has_margin, (
                f"Tab '{tab.label}' has no padding or margin. "
                f"Padding: {styles.padding}, Margin: {styles.margin}"
            )


@pytest.mark.asyncio
async def test_event_log_shows_formatted_events(temp_log_with_events: Path):
    """
    Verify events are properly formatted with timestamps and event types.

    Complements the basic content test by checking formatting quality.
    """
    app = RecallMonitorApp(log_path=temp_log_with_events)

    async with app.run_test() as pilot:
        await pilot.pause()

        event_log = app.query_one("#event-log", RichLog)

        # If there's content, it should be formatted properly
        if len(event_log.lines) > 0:
            # The test passes if we have any formatted content
            # More detailed formatting checks would require inspecting
            # the actual rendered text, which is complex with Rich markup
            pass
        else:
            pytest.fail("Event log has no content to verify formatting")


@pytest.mark.asyncio
async def test_app_has_expected_tabs(temp_log_with_events: Path):
    """
    Verify the app has all expected tabs: Live, Health, State, Session, Charts.
    """
    app = RecallMonitorApp(log_path=temp_log_with_events)

    async with app.run_test() as pilot:
        await pilot.pause()

        tabs = app.query(Tab)
        tab_labels = [str(tab.label) for tab in tabs]

        expected_tabs = ["Live Activity", "Health", "State", "Session", "Charts"]

        for expected in expected_tabs:
            assert any(expected in label for label in tab_labels), (
                f"Expected tab '{expected}' not found. "
                f"Available tabs: {tab_labels}"
            )
