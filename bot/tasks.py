#!/usr/bin/env python3
"""
Simple Task Tracking
A lightweight in-memory to-do list for team collaboration.
"""

import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

# In-memory storage for tasks, loaded from a file
_TASKS_FILE = Path("tasks.json")
_tasks: list[dict] = []
_next_task_id = 1


def _load_tasks():
    """Loads tasks from the JSON file, handling potential corruption."""
    global _tasks, _next_task_id
    if _TASKS_FILE.exists():
        try:
            with _TASKS_FILE.open() as f:
                _tasks = json.load(f)
                _next_task_id = max(task["id"] for task in _tasks) + 1 if _tasks else 1
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                f"Could not decode '{_TASKS_FILE}'. Backing up and starting fresh."
            )
            _TASKS_FILE.rename(str(_TASKS_FILE) + ".bak")
            _tasks = []
            _next_task_id = 1
    else:
        _tasks = []
        _next_task_id = 1


def _save_tasks():
    """Saves the current tasks to the JSON file."""
    try:
        with _TASKS_FILE.open("w") as f:
            json.dump(_tasks, f, indent=2)
    except OSError as e:
        logger.error(f"Could not save tasks to '{_TASKS_FILE}': {e}")
        # Depending on desired behavior, we might want to raise this
        # to inform the user that the task was not saved.
        raise


def add_task(description: str) -> dict:
    """Adds a new task to the to-do list."""
    global _next_task_id
    if not description:
        raise ValueError("Task description cannot be empty.")

    task = {"id": _next_task_id, "description": description, "done": False}
    _tasks.append(task)
    _next_task_id += 1
    _save_tasks()
    return task


def list_tasks() -> list[dict]:
    """Lists all current tasks."""
    return _tasks


def mark_task_done(task_id: int) -> dict | None:
    """Marks a specific task as done."""
    for task in _tasks:
        if task["id"] == task_id:
            task["done"] = True
            _save_tasks()
            return task
    return None


def clear_tasks():
    """Clears all tasks from the list."""
    global _tasks, _next_task_id
    _tasks = []
    _next_task_id = 1
    _save_tasks()


# Load tasks when the module is imported
_load_tasks()
