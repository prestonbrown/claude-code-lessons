#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
LessonsManager class - Main entry point for the lessons system.

This module provides the LessonsManager class that combines lesson and handoff
functionality through composition of mixins.
"""

import os
from pathlib import Path

# Handle both module import and direct script execution
try:
    from core.lessons import LessonsMixin
    from core.handoffs import HandoffsMixin
except ImportError:
    from lessons import LessonsMixin
    from handoffs import HandoffsMixin


def _get_lessons_base() -> Path:
    """Get the system lessons base directory, checking RECALL_BASE first, then LESSONS_BASE."""
    # Check new env var first, fall back to old
    base_path = os.environ.get("RECALL_BASE") or os.environ.get("LESSONS_BASE")
    if base_path:
        return Path(base_path)
    return Path.home() / ".config" / "coding-agent-lessons"


def _get_project_data_dir(project_root: Path) -> Path:
    """Get the project data directory, preferring .recall/ over .coding-agent-lessons/."""
    recall_dir = project_root / ".recall"
    legacy_dir = project_root / ".coding-agent-lessons"

    # Prefer new directory if it exists, otherwise use legacy if it exists
    if recall_dir.exists():
        return recall_dir
    elif legacy_dir.exists():
        return legacy_dir
    else:
        # Default to new directory for new projects
        return recall_dir


class LessonsManager(LessonsMixin, HandoffsMixin):
    """
    Manager for AI coding agent lessons.

    Provides methods to add, cite, edit, delete, promote, and list lessons
    stored in markdown format.

    This class composes functionality from:
    - LessonsMixin: All lesson-related operations
    - HandoffsMixin: All handoff-related operations (formerly ApproachesMixin)
    """

    def __init__(self, lessons_base: Path, project_root: Path):
        """
        Initialize the lessons manager.

        Args:
            lessons_base: Base directory for system lessons (~/.config/coding-agent-lessons)
            project_root: Root directory of the project (containing .git)
        """
        self.lessons_base = Path(lessons_base)
        self.project_root = Path(project_root)

        self.system_lessons_file = self.lessons_base / "LESSONS.md"

        # Get project data directory (prefers .recall/ over .coding-agent-lessons/)
        project_data_dir = _get_project_data_dir(self.project_root)
        self.project_lessons_file = project_data_dir / "LESSONS.md"

        self._decay_state_file = self.lessons_base / ".decay-last-run"
        self._session_state_dir = self.lessons_base / ".citation-state"

        # Ensure directories exist for both lessons files
        self.system_lessons_file.parent.mkdir(parents=True, exist_ok=True)
        self.project_lessons_file.parent.mkdir(parents=True, exist_ok=True)
