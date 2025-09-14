#!/usr/bin/env python3
"""
Idea Sheet Management
Provides commands for creating, listing, and viewing idea sheets.
"""

import os
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)
IDEASHEETS_DIR = "docs/ideasheets"


def create_idea_sheet(title: str, content: str = "") -> Path:
    """Creates a new idea sheet markdown file."""
    if not title:
        raise ValueError("Title cannot be empty.")

    # Sanitize title to create a valid filename
    filename = "".join(c for c in title if c.isalnum() or c in " ._").rstrip()
    if not filename:
        raise ValueError("Invalid title for a filename.")
        
    filepath = Path(IDEASHEETS_DIR) / f"{filename}.md"
    
    try:
        # Ensure the directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the file with initial content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            if content:
                f.write(f"{content}\n")
    except IOError as e:
        logger.error(f"Could not create idea sheet at '{filepath}': {e}")
        raise
            
    return filepath


def list_idea_sheets() -> List[str]:
    """Lists all available idea sheets."""
    if not os.path.exists(IDEASHEETS_DIR):
        return []
        
    try:
        return [f.stem for f in Path(IDEASHEETS_DIR).glob("*.md") if f.stem != "README"]
    except IOError as e:
        logger.error(f"Could not list idea sheets in '{IDEASHEETS_DIR}': {e}")
        return []


def get_idea_sheet_content(title: str) -> str:
    """Gets the content of a specific idea sheet."""
    filepath = Path(IDEASHEETS_DIR) / f"{title}.md"
    
    if not filepath.exists():
        raise FileNotFoundError(f"Idea sheet '{title}' not found.")
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except IOError as e:
        logger.error(f"Could not read idea sheet '{filepath}': {e}")
        raise
