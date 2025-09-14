#!/usr/bin/env python3
"""
Utility functions for Project Automation Discord Bot

Includes:
- MessageChunker: Safely splits long messages for Discord while preserving formatting
- ConversationMemory: Persistent per-user conversation history (SQLite)
- AIHelper: Google-powered tagging, transcription, and unit test generation
- FileProcessor: OCR, audio conversion, Markdown->HTML/PDF conversion, language detection
- CodeAnalyzer: Python linting via flake8
- GitHubHelper: Basic GitHub PR and issues utilities
- WebSearchHelper: Lightweight web search using DuckDuckGo HTML

All components are designed to degrade gracefully when optional dependencies are missing.
"""

import hashlib
import json
import re
import tempfile
import asyncio as _asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import markdown
from jinja2 import Template

import aiosqlite
import aiofiles
import logging
logger = logging.getLogger(__name__)


# Optional dependencies and availability flags
# OCR
try:
    import cv2
    import numpy as np  # noqa: F401 (used in advanced pipelines if added)
    import pytesseract
    from PIL import Image  # noqa: F401 (imported for completeness; used by pytesseract)

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# AI / Google
try:
    import google.generativeai as genai

    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False

# Audio processing
try:
    import warnings
    import shutil

    # Import pydub while temporarily suppressing RuntimeWarnings that occur
    # when ffmpeg/avconv are not present on the system. After import, try
    # to locate ffmpeg on PATH and assign it so pydub doesn't warn later.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        from pydub import AudioSegment

    # If ffmpeg is available on PATH, point pydub to it explicitly.
    ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg_path:
        try:
            AudioSegment.converter = ffmpeg_path
        except Exception:
            # If assignment fails, don't crash import; pydub will fallback.
            pass

    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# GitHub integration
try:
    from github import Github

    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# Web fetching/scraping
try:
    import aiohttp
    from bs4 import BeautifulSoup

    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

# Markdown / PDF

try:
    import pdfkit

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Config import with fallback for package or direct run
try:
    from .config import config
except ImportError:
    from config import config  # type: ignore


# -----------------------------------------------------------------------------
# MessageChunker
# -----------------------------------------------------------------------------
class MessageChunker:
    """Utility for safely chunking long messages for Discord."""

    # Discord limits
    MAX_MESSAGE_LENGTH = 2000
    MAX_EMBED_DESCRIPTION_LENGTH = 4096
    MAX_EMBED_FIELD_VALUE_LENGTH = 1024

    def __init__(self, max_length: int = MAX_MESSAGE_LENGTH):
        self.max_length = max_length

    def chunk_text(
        self, text: str, preserve_words: bool = True, preserve_lines: bool = True
    ) -> List[str]:
        """
        Split text into chunks that fit Discord's limits.

        Args:
            text: Text to split
            preserve_words: Try to split at word boundaries
            preserve_lines: Try to split at line boundaries

        Returns:
            List of text chunks
        """
        if len(text) <= self.max_length:
            return [text]

        chunks: List[str] = []
        remaining = text

        while remaining:
            if len(remaining) <= self.max_length:
                chunks.append(remaining)
                break

            split_point = self._find_split_point(
                remaining, preserve_words, preserve_lines
            )

            chunk = remaining[:split_point].rstrip()
            if chunk:
                chunks.append(chunk)

            remaining = remaining[split_point:].lstrip()

        return chunks

    def _find_split_point(
        self, text: str, preserve_words: bool, preserve_lines: bool
    ) -> int:
        """Find the best point to split text."""
        max_pos = min(len(text), self.max_length)

        if max_pos >= len(text):
            return len(text)

        # Prefer newline splits
        if preserve_lines:
            newline_pos = text.rfind("\n", 0, max_pos)
            if newline_pos > max_pos * 0.5:
                return newline_pos + 1

        # Then word boundary splits
        if preserve_words:
            space_pos = text.rfind(" ", 0, max_pos)
            if space_pos > max_pos * 0.5:
                return space_pos + 1

        # Fallback to hard split
        return max_pos

    def chunk_for_embed_description(self, text: str) -> List[str]:
        """Split text for Discord embed descriptions."""
        chunker = MessageChunker(self.MAX_EMBED_DESCRIPTION_LENGTH)
        return chunker.chunk_text(text)

    def chunk_for_embed_field(self, text: str) -> List[str]:
        """Split text for Discord embed field values."""
        chunker = MessageChunker(self.MAX_EMBED_FIELD_VALUE_LENGTH)
        return chunker.chunk_text(text)

    def chunk_markdown_safely(self, text: str) -> List[str]:
        """
        Split markdown text while trying to preserve formatting.

        Args:
            text: Markdown text to split

        Returns:
            List of markdown chunks
        """
        sections = self._split_by_markdown_sections(text)

        chunks: List[str] = []
        current_chunk = ""

        for section in sections:
            if len(current_chunk) + len(section) > self.max_length:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                if len(section) > self.max_length:
                    section_chunks = self.chunk_text(
                        section, preserve_words=True, preserve_lines=True
                    )
                    chunks.extend(section_chunks)
                else:
                    current_chunk = section
            else:
                current_chunk += section

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk.strip()]

    def _split_by_markdown_sections(self, text: str) -> List[str]:
        """Split text by markdown sections (headers, code blocks, etc.)."""
        patterns = [
            r"^```[\s\S]*?^```",  # Code blocks
            r"^#{1,6} .*$",  # Headers
            r"^- .*$",  # List items
            r"^\d+\. .*$",  # Numbered list items
            r"^> .*$",  # Quotes
        ]

        pattern = "|".join(f"({p})" for p in patterns)
        matches = list(re.finditer(pattern, text, re.MULTILINE))

        if not matches:
            return text.split("\n\n")

        sections: List[str] = []
        last_end = 0

        for match in matches:
            before = text[last_end : match.start()]
            if before.strip():
                sections.append(before)

            sections.append(match.group())
            last_end = match.end()

        if last_end < len(text):
            remaining = text[last_end:]
            if remaining.strip():
                sections.append(remaining)

        return sections

    @staticmethod
    def add_chunk_indicators(
        chunks: List[str], total_pages: Optional[int] = None
    ) -> List[str]:
        """
        Add page indicators to chunks.

        Args:
            chunks: List of text chunks
            total_pages: Total number of pages (defaults to len(chunks))

        Returns:
            Chunks with page indicators added
        """
        if len(chunks) <= 1:
            return chunks

        total = total_pages or len(chunks)
        result: List[str] = []

        for i, chunk in enumerate(chunks, 1):
            indicator = f"📄 Page {i}/{total}\n\n"
            if len(chunk) + len(indicator) <= MessageChunker.MAX_MESSAGE_LENGTH:
                result.append(indicator + chunk)
            else:
                indicator_tail = f"\n\n📄 Page {i}/{total}"
                max_content_length = MessageChunker.MAX_MESSAGE_LENGTH - len(
                    indicator_tail
                )
                truncated_chunk = chunk[:max_content_length].rstrip()
                result.append(truncated_chunk + indicator_tail)

        return result

    @staticmethod
    def truncate_with_ellipsis(
        text: str, max_length: int, ellipsis: str = "..."
    ) -> str:
        """
        Truncate text to max_length, adding ellipsis if truncated.
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - len(ellipsis)].rstrip() + ellipsis


# -----------------------------------------------------------------------------
# Conversation Memory (SQLite)
# -----------------------------------------------------------------------------
class ConversationMemory:
    """Manages persistent conversation memory using SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def init_db(self):
        """Initialize the database with required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    context_hash TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    preferences TEXT,  -- JSON string
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def store_conversation(
        self, user_id: int, message: str, response: str, context: Optional[Dict] = None
    ):
        """Store a conversation in the database."""
        context_hash = None
        if context:
            try:
                context_hash = hashlib.md5(
                    json.dumps(context, sort_keys=True).encode()
                ).hexdigest()
            except Exception:
                context_hash = None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (user_id, message, response, context_hash) VALUES (?, ?, ?, ?)",
                (user_id, message, response, context_hash),
            )
            await db.commit()

    async def get_conversation_history(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT message, response, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                {"message": row[0], "response": row[1], "timestamp": row[2]}
                for row in rows
            ]


# -----------------------------------------------------------------------------
# AI Helper (Google)
# -----------------------------------------------------------------------------
class AIHelper:
    """Helper class for AI-powered features."""

    def __init__(self):
        key = getattr(config, "google_api_key", None)
        if GOOGLE_AI_AVAILABLE and key:
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel(getattr(config, "ai_model", "gemini-1.5-flash"))
            self.available = True
        else:
            self.available = False

    async def generate_tags(self, content: str) -> List[str]:
        """Generate tags for markdown content using AI."""
        if not self.available:
            return self._fallback_tags(content)

        try:
            response = await self.model.generate_content_async(
                f"Generate a comma-separated list of 3-5 relevant tags for the following technical content. Return only the list, without any introductory text.\n\nContent:\n\n{content[:1500]}"
            )
            tags_text = response.text.strip()
            return [
                tag.strip().lstrip("#") for tag in tags_text.split(",") if tag.strip()
            ]
        except Exception:
            return self._fallback_tags(content)

    def _fallback_tags(self, content: str) -> List[str]:
        """Fallback tag generation without AI."""
        keywords = [
            "python",
            "javascript",
            "api",
            "database",
            "web",
            "mobile",
            "ai",
            "ml",
            "data",
        ]
        found_tags: List[str] = []
        content_lower = content.lower()

        for keyword in keywords:
            if keyword in content_lower:
                found_tags.append(keyword)

        if "class " in content or "def " in content:
            found_tags.append("programming")
        if "http" in content_lower or "api" in content_lower:
            found_tags.append("api")
        if not found_tags:
            found_tags = ["general", "documentation"]

        # Deduplicate while preserving order
        seen = set()
        unique = [t for t in found_tags if not (t in seen or seen.add(t))]
        return unique[:5]

    async def transcribe_audio(self, audio_path: Path) -> str:
        """Transcribe audio using a placeholder, as Google AI doesn't directly support it in this context."""
        return "Audio transcription not available with the current AI provider."

    async def generate_unit_tests(self, code: str, language: str = "python") -> str:
        """Generate unit test stubs for code."""
        if not self.available:
            return "# Unit test generation not available (Google API key required)"

        try:
            response = await self.model.generate_content_async(
                f"Generate comprehensive unit tests for the following {language} code. Use best practices and assertions.\n\nCode:\n\n{code}"
            )
            return response.text
        except Exception as e:
            return f"# Test generation failed: {str(e)}"


# -----------------------------------------------------------------------------
# File Processing (OCR, audio, conversions)
# -----------------------------------------------------------------------------
class FileProcessor:
    """Handles file processing, OCR, and conversions."""

    @staticmethod
    async def extract_text_from_image(image_path: Path) -> str:
        """Extract text from image using OCR."""
        if not OCR_AVAILABLE:
            return "OCR not available - install pytesseract, pillow, and opencv-python"

        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return "OCR failed: could not read image"
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            processed = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )[1]
            text = pytesseract.image_to_string(processed)
            return text.strip()
        except Exception as e:
            return f"OCR failed: {str(e)}"

    @staticmethod
    async def convert_audio_to_wav(input_path: Path, output_path: Path) -> bool:
        """Convert audio file to WAV format for processing."""
        if not AUDIO_AVAILABLE:
            return False

        try:
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format="wav")
            return True
        except Exception:
            return False

    @staticmethod
    async def detect_language(code: str) -> str:
        """Detect programming language from code snippet."""
        if any(p in code for p in ["def ", "import ", "from ", "print(", "__init__"]):
            return "python"
        if any(
            p in code for p in ["function ", "var ", "let ", "const ", "console.log"]
        ):
            return "javascript"
        if any(
            p in code
            for p in ["public class ", "public static void main", "import java"]
        ):
            return "java"
        if any(p in code for p in ["#include ", "int main(", "std::", "cout"]):
            return "cpp"
        if any(p in code for p in ["package ", "func main(", "import (", "fmt."]):
            return "go"
        if any(p in code for p in ["fn main(", "use std::", "let mut"]):
            return "rust"
        if code.startswith("#!/bin/bash") or code.startswith("#!/bin/sh"):
            return "bash"
        return "text"

    @staticmethod
    async def markdown_to_html(markdown_content: str, title: str = "Document") -> str:
        """Convert markdown to HTML with styling."""
        try:
            html_content = markdown.markdown(
                markdown_content,
                extensions=["codehilite", "toc", "tables", "fenced_code"],
            )
        except Exception:
            html_content = markdown.markdown(markdown_content)

        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        code { background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
        pre { background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    {{ content }}
</body>
</html>
        """)
        rendered = template.render(title=title, content=html_content)

        # Security: remove any <script> tags from rendered HTML to avoid executing
        # injected scripts when HTML is viewed or converted to PDF.
        try:
            # A lightweight removal of script tags; avoid heavy deps here.
            rendered = re.sub(
                r"<script[\s\S]*?>[\s\S]*?<\/script>", "", rendered, flags=re.IGNORECASE
            )
        except Exception:
            pass

        return rendered

    @staticmethod
    async def html_to_pdf(html_content: str, output_path: Path) -> bool:
        """Convert HTML to PDF using pdfkit."""
        if not PDF_AVAILABLE:
            # Create a simple fallback text file
            try:
                p = output_path.with_suffix(".txt")
                p.write_text(
                    "PDF generation not available - pdfkit not installed\n\n"
                    + html_content,
                    encoding="utf-8",
                )
            except Exception:
                pass
            return False

        try:
            options = {
                "page-size": "A4",
                "margin-top": PDF_MARGIN,
                "margin-right": PDF_MARGIN,
                "margin-bottom": PDF_MARGIN,
                "margin-left": PDF_MARGIN,
                "encoding": "UTF-8",
                "no-outline": None,
            }
            pdfkit.from_string(html_content, str(output_path), options=options)
            return True
        except Exception:
            return False


# -----------------------------------------------------------------------------
# Code Analyzer
# -----------------------------------------------------------------------------
PDF_MARGIN = "0.75in"


class CodeAnalyzer:
    """Analyzes code for issues and suggestions."""

    @staticmethod
    async def lint_python_code(code: str) -> List[str]:
        """Lint Python code with reduced complexity."""
        issues = []
        try:
            temp_path = Path(tempfile.mktemp(suffix=".py"))
            async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
                await f.write(code)

            proc = await _asyncio.create_subprocess_exec(
                "flake8", str(temp_path),
                stdout=_asyncio.subprocess.PIPE,
                stderr=_asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if stdout:
                issues.extend(stdout.decode().splitlines())
            if stderr:
                logger.error(f"Linting error: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Error during linting: {e}")
        finally:
            if temp_path.exists():
                temp_path.unlink()

        return issues


# -----------------------------------------------------------------------------
# GitHub Helper
# -----------------------------------------------------------------------------
class GitHubHelper:
    """Helper for GitHub integration."""

    def __init__(self):
        token = getattr(config, "github_token", None)
        if GITHUB_AVAILABLE and token:
            self.github = Github(token)
            self.available = True
        else:
            self.github = None
            self.available = False
            if not token:
                logger.error("GitHub token is missing in the configuration.")
            if not GITHUB_AVAILABLE:
                logger.error("GitHub integration is disabled.")

    async def create_pr(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> str:
        """Create a GitHub pull request."""
        if not self.available or not self.github:
            return "GitHub integration not available (token required)"

        try:
            loop = _asyncio.get_event_loop()

            def _create():
                repo = self.github.get_repo(repo_name)
                pr = repo.create_pull(
                    title=title, body=body, head=head_branch, base=base_branch
                )
                return pr.html_url

            pr_url = await loop.run_in_executor(None, _create)
            return f"✅ Pull request created: {pr_url}"
        except Exception as e:
            return f"[ERROR] Failed to create PR: {str(e)}"

    async def get_issues(
        self, repo_name: str, state: str = "open", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get GitHub issues for a repository."""
        if not self.available or not self.github:
            return []
        try:
            loop = _asyncio.get_event_loop()

            def _fetch():
                repo = self.github.get_repo(repo_name)
                issues = repo.get_issues(state=state)
                result: List[Dict[str, Any]] = []
                for i, issue in enumerate(issues):
                    if i >= limit:
                        break
                    result.append(
                        {
                            "number": issue.number,
                            "title": issue.title,
                            "url": issue.html_url,
                            "state": issue.state,
                            "created_at": issue.created_at.isoformat(),
                        }
                    )
                return result

            result = await loop.run_in_executor(None, _fetch)
            return result
        except Exception:
            return []


# -----------------------------------------------------------------------------
# Web Search Helper
# -----------------------------------------------------------------------------
class WebSearchHelper:
    """Helper for web search functionality."""

    @staticmethod
    async def google_search(query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Perform a basic web search via DuckDuckGo's HTML results."""
        if not WEB_AVAILABLE:
            return [
                {
                    "title": "Search unavailable - aiohttp and beautifulsoup4 required",
                    "url": "",
                    "snippet": "",
                }
            ]

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://html.duckduckgo.com/html/?q={query}"
                headers = {"User-Agent": "Mozilla/5.0 (compatible; Discord Bot)"}
                async with session.get(url, headers=headers, timeout=20) as response:
                    if response.status != 200:
                        return [
                            {
                                "title": "Search unavailable",
                                "url": "",
                                "snippet": "Request failed",
                            }
                        ]
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    results: List[Dict[str, Any]] = []
                    for link in soup.find_all("a", {"class": "result__a"})[:limit]:
                        title = link.get_text().strip()
                        href = link.get("href")
                        if title and href:
                            results.append({"title": title, "url": href, "snippet": ""})
                    return results or [
                        {"title": "No results", "url": "", "snippet": ""}
                    ]
        except Exception:
            return [
                {
                    "title": "Search unavailable",
                    "url": "",
                    "snippet": "Web search is currently unavailable",
                }
            ]


# -----------------------------------------------------------------------------
# Global instances
# -----------------------------------------------------------------------------
memory = ConversationMemory(
    getattr(config, "db_path", Path("bot/conversation_memory.db"))
)
ai_helper = AIHelper()
file_processor = FileProcessor()
code_analyzer = CodeAnalyzer()
github_helper = GitHubHelper()
web_search = WebSearchHelper()
