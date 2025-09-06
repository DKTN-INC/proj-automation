#!/usr/bin/env python3
"""
Utility functions for Discord Bot
Provides AI integration, file processing, OCR, and other helper functions
"""

import os
import re
import sqlite3
import tempfile
import aiosqlite
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json
import hashlib

# File processing
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# AI and OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Audio processing
try:
    from pydub import AudioSegment
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# GitHub integration
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# Web scraping
try:
    import aiohttp
    from bs4 import BeautifulSoup
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

# Code analysis
import subprocess
import ast

# Markdown processing
import markdown
from jinja2 import Template
try:
    import pdfkit
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from .config import config
except ImportError:
    from config import config

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
    
    async def store_conversation(self, user_id: int, message: str, response: str, context: Dict = None):
        """Store a conversation in the database."""
        context_hash = None
        if context:
            context_hash = hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (user_id, message, response, context_hash) VALUES (?, ?, ?, ?)",
                (user_id, message, response, context_hash)
            )
            await db.commit()
    
    async def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get conversation history for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT message, response, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            rows = await cursor.fetchall()
            return [{"message": row[0], "response": row[1], "timestamp": row[2]} for row in rows]

class AIHelper:
    """Helper class for AI-powered features."""
    
    def __init__(self):
        if OPENAI_AVAILABLE and config.openai_api_key:
            openai.api_key = config.openai_api_key
            self.available = True
        else:
            self.available = False
    
    async def generate_tags(self, content: str) -> List[str]:
        """Generate tags for markdown content using AI."""
        if not self.available:
            return self._fallback_tags(content)
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=config.ai_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates relevant tags for technical content. Return only a comma-separated list of 3-5 relevant tags."},
                    {"role": "user", "content": f"Generate tags for this content:\n\n{content[:1000]}"}
                ],
                max_tokens=50,
                temperature=0.3
            )
            tags_text = response.choices[0].message.content.strip()
            return [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        except Exception:
            return self._fallback_tags(content)
    
    def _fallback_tags(self, content: str) -> List[str]:
        """Fallback tag generation without AI."""
        # Simple keyword extraction
        keywords = ['python', 'javascript', 'api', 'database', 'web', 'mobile', 'ai', 'ml', 'data']
        found_tags = []
        content_lower = content.lower()
        
        for keyword in keywords:
            if keyword in content_lower:
                found_tags.append(keyword)
        
        # Add generic tags based on content patterns
        if 'class ' in content or 'def ' in content:
            found_tags.append('programming')
        if 'http' in content_lower or 'api' in content_lower:
            found_tags.append('api')
        if not found_tags:
            found_tags = ['general', 'documentation']
        
        return found_tags[:5]
    
    async def transcribe_audio(self, audio_path: Path) -> str:
        """Transcribe audio using OpenAI Whisper."""
        if not self.available:
            return "Audio transcription not available (OpenAI API key required)"
        
        try:
            with open(audio_path, 'rb') as audio_file:
                transcript = await openai.Audio.atranscribe(
                    model=config.whisper_model,
                    file=audio_file
                )
                return transcript.text
        except Exception as e:
            return f"Transcription failed: {str(e)}"
    
    async def generate_unit_tests(self, code: str, language: str = "python") -> str:
        """Generate unit test stubs for code."""
        if not self.available:
            return "# Unit test generation not available (OpenAI API key required)"
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=config.ai_model,
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant that generates unit tests for {language} code. Generate comprehensive test cases with assertions."},
                    {"role": "user", "content": f"Generate unit tests for this {language} code:\n\n{code}"}
                ],
                max_tokens=500,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"# Test generation failed: {str(e)}"

class FileProcessor:
    """Handles file processing, OCR, and conversions."""
    
    @staticmethod
    async def extract_text_from_image(image_path: Path) -> str:
        """Extract text from image using OCR."""
        if not OCR_AVAILABLE:
            return "OCR not available - install pytesseract, pillow, and opencv-python"
        
        try:
            # Load and preprocess image
            image = cv2.imread(str(image_path))
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply image preprocessing for better OCR
            processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Extract text
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
        # Simple language detection based on syntax patterns
        if 'def ' in code and 'import ' in code:
            return 'python'
        elif 'function ' in code and ('var ' in code or 'let ' in code or 'const ' in code):
            return 'javascript'
        elif 'public class ' in code or 'import java' in code:
            return 'java'
        elif '#include ' in code or 'int main(' in code:
            return 'cpp'
        elif 'function ' in code and 'end' in code:
            return 'lua'
        elif 'package ' in code and 'func ' in code:
            return 'go'
        else:
            return 'text'
    
    @staticmethod
    async def markdown_to_html(markdown_content: str, title: str = "Document") -> str:
        """Convert markdown to HTML with styling."""
        try:
            html_content = markdown.markdown(
                markdown_content,
                extensions=['codehilite', 'toc', 'tables', 'fenced_code']
            )
        except ImportError:
            # Fallback if extensions not available
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
        
        return template.render(title=title, content=html_content)
    
    @staticmethod
    async def html_to_pdf(html_content: str, output_path: Path) -> bool:
        """Convert HTML to PDF using pdfkit."""
        if not PDF_AVAILABLE:
            # Create a simple text file if pdfkit not available
            with open(output_path.with_suffix('.txt'), 'w') as f:
                f.write("PDF generation not available - pdfkit not installed\n\n")
                f.write(html_content)
            return False
        
        try:
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }
            pdfkit.from_string(html_content, str(output_path), options=options)
            return True
        except Exception:
            return False

class CodeAnalyzer:
    """Analyzes code for issues and suggestions."""
    
    @staticmethod
    async def lint_python_code(code: str) -> List[str]:
        """Lint Python code using flake8."""
        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            # Run flake8
            result = subprocess.run(
                ['flake8', '--select=E,W,F', temp_path],
                capture_output=True,
                text=True
            )
            
            # Clean up
            os.unlink(temp_path)
            
            if result.returncode == 0:
                return ["✅ No linting issues found!"]
            else:
                issues = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        # Parse flake8 output and format nicely
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            line_num = parts[1]
                            col_num = parts[2]
                            message = parts[3].strip()
                            issues.append(f"Line {line_num}:{col_num} - {message}")
                
                return issues if issues else ["❌ Linting failed"]
        
        except FileNotFoundError:
            return ["❌ flake8 not installed - install with: pip install flake8"]
        except Exception as e:
            return [f"❌ Linting error: {str(e)}"]

class GitHubHelper:
    """Helper for GitHub integration."""
    
    def __init__(self):
        if GITHUB_AVAILABLE and config.github_token:
            self.github = Github(config.github_token)
            self.available = True
        else:
            self.available = False
    
    async def create_pr(self, repo_name: str, title: str, body: str, head_branch: str, base_branch: str = "main") -> str:
        """Create a GitHub pull request."""
        if not self.available:
            return "GitHub integration not available (token required)"
        
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)
            return f"✅ Pull request created: {pr.html_url}"
        except Exception as e:
            return f"❌ Failed to create PR: {str(e)}"
    
    async def get_issues(self, repo_name: str, state: str = "open", limit: int = 5) -> List[Dict]:
        """Get GitHub issues for a repository."""
        if not self.available:
            return []
        
        try:
            repo = self.github.get_repo(repo_name)
            issues = repo.get_issues(state=state)
            
            result = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break
                result.append({
                    "number": issue.number,
                    "title": issue.title,
                    "url": issue.html_url,
                    "state": issue.state,
                    "created_at": issue.created_at.isoformat()
                })
            
            return result
        except Exception:
            return []

class WebSearchHelper:
    """Helper for web search functionality."""
    
    @staticmethod
    async def google_search(query: str, limit: int = 3) -> List[Dict]:
        """Perform a basic web search (Note: This is a simplified implementation)."""
        if not WEB_AVAILABLE:
            return [{"title": "Search unavailable - aiohttp and beautifulsoup4 required", "url": "", "snippet": ""}]
        
        # Note: This is a basic implementation. For production, consider using Google Custom Search API
        try:
            async with aiohttp.ClientSession() as session:
                # Use DuckDuckGo as it doesn't require API keys
                url = f"https://html.duckduckgo.com/html/?q={query}"
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; Discord Bot)'}
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        results = []
                        for link in soup.find_all('a', {'class': 'result__a'})[:limit]:
                            title = link.get_text().strip()
                            href = link.get('href')
                            if title and href:
                                results.append({
                                    "title": title,
                                    "url": href,
                                    "snippet": ""  # DuckDuckGo HTML doesn't provide snippets easily
                                })
                        
                        return results
                    
        except Exception:
            pass
        
        return [{"title": "Search unavailable", "url": "", "snippet": "Web search is currently unavailable"}]

# Global instances
memory = ConversationMemory(config.db_path)
ai_helper = AIHelper()
file_processor = FileProcessor()
code_analyzer = CodeAnalyzer()
github_helper = GitHubHelper()
web_search = WebSearchHelper()