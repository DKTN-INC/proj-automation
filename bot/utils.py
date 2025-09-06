#!/usr/bin/env python3
"""
Message Chunking Utility
Safely splits long messages to fit Discord's character limits while preserving formatting.
"""

import re
from typing import List, Optional


class MessageChunker:
    """Utility for safely chunking long messages for Discord."""
    
    # Discord limits
    MAX_MESSAGE_LENGTH = 2000
    MAX_EMBED_DESCRIPTION_LENGTH = 4096
    MAX_EMBED_FIELD_VALUE_LENGTH = 1024
    
    def __init__(self, max_length: int = MAX_MESSAGE_LENGTH):
        self.max_length = max_length
    
    def chunk_text(self, text: str, preserve_words: bool = True, preserve_lines: bool = True) -> List[str]:
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
        
        chunks = []
        remaining = text
        
        while remaining:
            if len(remaining) <= self.max_length:
                chunks.append(remaining)
                break
            
            # Find the best split point
            split_point = self._find_split_point(remaining, preserve_words, preserve_lines)
            
            chunk = remaining[:split_point].rstrip()
            if chunk:
                chunks.append(chunk)
            
            remaining = remaining[split_point:].lstrip()
        
        return chunks
    
    def _find_split_point(self, text: str, preserve_words: bool, preserve_lines: bool) -> int:
        """Find the best point to split text."""
        max_pos = min(len(text), self.max_length)
        
        # If we're at the end, return the full length
        if max_pos >= len(text):
            return len(text)
        
        # Try to split at line boundaries first
        if preserve_lines:
            # Look for newlines within the limit
            newline_pos = text.rfind('\n', 0, max_pos)
            if newline_pos > max_pos * 0.5:  # Don't split too early
                return newline_pos + 1
        
        # Try to split at word boundaries
        if preserve_words:
            # Look for spaces within the limit
            space_pos = text.rfind(' ', 0, max_pos)
            if space_pos > max_pos * 0.5:  # Don't split too early
                return space_pos + 1
        
        # If no good split point found, split at the limit
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
        # Split by markdown sections first (headers, code blocks, etc.)
        sections = self._split_by_markdown_sections(text)
        
        chunks = []
        current_chunk = ""
        
        for section in sections:
            # If adding this section would exceed the limit
            if len(current_chunk) + len(section) > self.max_length:
                # If we have accumulated content, save it as a chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # If the section itself is too long, split it
                if len(section) > self.max_length:
                    section_chunks = self.chunk_text(section, preserve_words=True, preserve_lines=True)
                    chunks.extend(section_chunks)
                else:
                    current_chunk = section
            else:
                current_chunk += section
        
        # Add any remaining content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    def _split_by_markdown_sections(self, text: str) -> List[str]:
        """Split text by markdown sections (headers, code blocks, etc.)."""
        # Patterns for markdown sections
        patterns = [
            r'^```[\s\S]*?^```',  # Code blocks
            r'^#{1,6} .*$',       # Headers
            r'^- .*$',            # List items
            r'^\d+\. .*$',        # Numbered list items
            r'^> .*$',            # Quotes
        ]
        
        # Combine patterns
        pattern = '|'.join(f'({p})' for p in patterns)
        
        # Find all matches
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        
        if not matches:
            # No markdown found, split by paragraphs
            return text.split('\n\n')
        
        sections = []
        last_end = 0
        
        for match in matches:
            # Add text before this match
            before = text[last_end:match.start()]
            if before.strip():
                sections.append(before)
            
            # Add the matched section
            sections.append(match.group())
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining.strip():
                sections.append(remaining)
        
        return sections
    
    @staticmethod
    def add_chunk_indicators(chunks: List[str], total_pages: Optional[int] = None) -> List[str]:
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
        result = []
        
        for i, chunk in enumerate(chunks, 1):
            indicator = f"📄 Page {i}/{total}\n\n"
            # Make sure adding the indicator doesn't exceed limits
            if len(chunk) + len(indicator) <= MessageChunker.MAX_MESSAGE_LENGTH:
                result.append(indicator + chunk)
            else:
                # If it would exceed, put indicator at the end
                indicator = f"\n\n📄 Page {i}/{total}"
                max_content_length = MessageChunker.MAX_MESSAGE_LENGTH - len(indicator)
                truncated_chunk = chunk[:max_content_length].rstrip()
                result.append(truncated_chunk + indicator)
        
        return result
    
    @staticmethod
    def truncate_with_ellipsis(text: str, max_length: int, ellipsis: str = "...") -> str:
        """
        Truncate text to max_length, adding ellipsis if truncated.
        
        Args:
            text: Text to truncate
            max_length: Maximum length including ellipsis
            ellipsis: String to add when truncating
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(ellipsis)].rstrip() + ellipsis