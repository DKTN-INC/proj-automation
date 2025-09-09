#!/usr/bin/env python3
"""
Markdown Processing Script for Project Automation

This script provides HTML templating, table of contents generation,
and AI summarization features for markdown files.
"""

import argparse
import asyncio
import datetime
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional

import markdown
import weasyprint
from jinja2 import Environment, FileSystemLoader


# Import currency formatting and async Discord webhook
try:
    from async_discord_webhook import send_pdf_if_webhook_configured
    from currency_formatter import CurrencyFormatter, format_gbp
except ImportError:
    # Fallback for package-relative imports
    try:
        from .async_discord_webhook import send_pdf_if_webhook_configured
        from .currency_formatter import CurrencyFormatter, format_gbp
    except ImportError:
        # Graceful fallback if modules not available
        CurrencyFormatter = None
        format_gbp = None
        send_pdf_if_webhook_configured = None


class MarkdownProcessor:
    """Main class for processing markdown files with enhanced features."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize the processor with optional template directory."""
        self.template_dir = template_dir or str(Path(__file__).parent / "templates")
        self.setup_jinja_env()

    def setup_jinja_env(self):
        """Setup Jinja2 environment for HTML templating."""
        try:
            if Path(self.template_dir).exists():
                self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir))
            else:
                # Create default templates directory
                Path(self.template_dir).mkdir(parents=True, exist_ok=True)
                self.create_default_templates()
                self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir))
        except Exception as e:
            print(f"Error setting up Jinja environment: {e}", file=sys.stderr)
            self.jinja_env = None

    def create_default_templates(self):
        """Create default HTML templates."""
        default_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title or 'Document' }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #333;
        }
        .toc {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin: 2rem 0;
            border-left: 4px solid #007bff;
        }
        .toc h2 { margin-top: 0; }
        .toc ul { list-style-type: none; padding-left: 0; }
        .toc li { margin: 0.5rem 0; }
        .toc a { text-decoration: none; color: #007bff; }
        .toc a:hover { text-decoration: underline; }
        .summary {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 1rem;
            margin: 2rem 0;
        }
        .summary h3 { margin-top: 0; color: #856404; }
        pre { background: #f8f9fa; padding: 1rem; border-radius: 4px; overflow-x: auto; }
        code { background: #f8f9fa; padding: 0.2rem 0.4rem; border-radius: 3px; }
        blockquote { border-left: 4px solid #ddd; margin: 0; padding-left: 1rem; color: #666; }
        table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
        th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
        th { background-color: #f8f9fa; font-weight: 600; }
        .metadata {
            font-size: 0.9rem;
            color: #666;
            border-top: 1px solid #eee;
            padding-top: 1rem;
            margin-top: 2rem;
        }
    </style>
</head>
<body>
    {% if summary %}
    <div class="summary">
        <h3>📄 Document Summary</h3>
        <p>{{ summary }}</p>
    </div>
    {% endif %}

    {% if toc %}
    <div class="toc">
        <h2>📚 Table of Contents</h2>
        {{ toc | safe }}
    </div>
    {% endif %}

    <main>
        {{ content | safe }}
    </main>

    {% if metadata %}
    <div class="metadata">
        <p><strong>Generated:</strong> {{ metadata.generated_at }}</p>
        {% if metadata.file_path %}<p><strong>Source:</strong> {{ metadata.file_path }}</p>{% endif %}
        {% if metadata.word_count %}<p><strong>Word count:</strong> {{ metadata.word_count }}</p>{% endif %}
    </div>
    {% endif %}
</body>
</html>"""

        template_path = Path(self.template_dir) / "default.html"
        with template_path.open("w", encoding="utf-8") as f:
            f.write(default_template)

    def extract_title(self, markdown_content: str) -> str:
        """Extract title from markdown content."""
        lines = markdown_content.split("\n")
        for line in lines:
            if line.strip().startswith("# "):
                return line.strip()[2:].strip()
        return "Untitled Document"

    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate a simple extractive summary of the content."""
        # Remove markdown syntax for better summary
        clean_content = re.sub(r"[#*`\[\]()]", "", content)
        clean_content = re.sub(r"\n+", " ", clean_content)

        sentences = re.split(r"[.!?]+", clean_content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if not sentences:
            return "No content available for summary."

        # Take first few sentences up to max_length
        summary = ""
        for sentence in sentences[:3]:  # Limit to first 3 sentences
            if len(summary + sentence) < max_length:
                summary += sentence + ". "
            else:
                break

        return summary.strip() or sentences[0][:max_length] + "..."

    def count_words(self, text: str) -> int:
        """Count words in text."""
        # Remove markdown syntax and count words
        clean_text = re.sub(r"[#*`\[\]()]", "", text)
        words = re.findall(r"\b\w+\b", clean_text)
        return len(words)

    def process_markdown_to_html(
        self, markdown_content: str, file_path: Optional[str] = None
    ) -> Dict:
        """Process markdown content to HTML with TOC and summary."""
        try:
            # Setup markdown processor with extensions
            md = markdown.Markdown(
                extensions=["toc", "codehilite", "tables", "fenced_code", "nl2br"]
            )

            # Convert markdown to HTML
            html_content = md.convert(markdown_content)

            # Extract title
            title = self.extract_title(markdown_content)

            # Generate summary
            summary = self.generate_summary(markdown_content)

            # Get table of contents
            toc_html = getattr(md, "toc", "")

            # Generate metadata
            metadata = {
                "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_path": file_path,
                "word_count": self.count_words(markdown_content),
            }

            return {
                "title": title,
                "content": html_content,
                "toc": toc_html,
                "summary": summary,
                "metadata": metadata,
                "success": True,
            }

        except Exception as e:
            return {"error": f"Error processing markdown: {str(e)}", "success": False}

    def render_template(self, template_name: str, **kwargs) -> str:
        """Render HTML template with given context."""
        try:
            if not self.jinja_env:
                raise Exception("Jinja environment not initialized")

            template = self.jinja_env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            print(f"Error rendering template: {e}", file=sys.stderr)
            # Fallback to simple HTML
            return f"""<!DOCTYPE html>
<html><head><title>{kwargs.get("title", "Document")}</title></head>
<body>{kwargs.get("content", "")}</body></html>"""

    def convert_to_pdf(self, html_content: str, output_path: str) -> bool:
        """Convert HTML content to PDF."""
        try:
            # Create output directory if it doesn't exist
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Convert HTML to PDF
            html_doc = weasyprint.HTML(string=html_content)
            html_doc.write_pdf(output_path)
            return True
        except Exception as e:
            print(f"Error converting to PDF: {e}", file=sys.stderr)
            return False

    def process_file(
        self, input_path: str, output_dir: str, template_name: str = "default.html"
    ) -> Dict:
        """Process a single markdown file."""
        try:
            # Validate input file
            if not Path(input_path).exists():
                return {
                    "error": f"Input file not found: {input_path}",
                    "success": False,
                }

            if not input_path.lower().endswith(".md"):
                return {
                    "error": f"Input file must be a markdown file: {input_path}",
                    "success": False,
                }

            # Read markdown content
            with Path(input_path).open(encoding="utf-8") as f:
                markdown_content = f.read()

            if not markdown_content.strip():
                return {"error": f"Input file is empty: {input_path}", "success": False}

            # Process markdown
            result = self.process_markdown_to_html(markdown_content, input_path)
            if not result["success"]:
                return result

            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Generate output filename
            input_pathobj = Path(input_path)
            base_name = input_pathobj.stem
            html_output = Path(output_dir) / f"{base_name}.html"
            pdf_output = Path(output_dir) / f"{base_name}.pdf"

            # Render HTML template
            html_content = self.render_template(template_name, **result)

            # Write HTML file
            with html_output.open("w", encoding="utf-8") as f:
                f.write(html_content)

            # Convert to PDF
            pdf_success = self.convert_to_pdf(html_content, str(pdf_output))

            return {
                "success": True,
                "html_output": html_output,
                "pdf_output": pdf_output if pdf_success else None,
                "title": result["title"],
                "summary": result["summary"],
                "word_count": result["metadata"]["word_count"],
            }

        except Exception as e:
            return {
                "error": f"Error processing file {input_path}: {str(e)}",
                "success": False,
            }

    async def process_file_with_discord(
        self,
        input_path: str,
        output_dir: str,
        template_name: str = "default.html",
        send_to_discord: bool = True,
    ) -> Dict:
        """
        Process a single markdown file and optionally send PDF to Discord.

        Args:
            input_path: Path to markdown file
            output_dir: Output directory
            template_name: Template to use
            send_to_discord: Whether to send PDF to Discord if webhook is configured

        Returns:
            Processing result with Discord status
        """
        # Process file normally first
        result = self.process_file(input_path, output_dir, template_name)

        # If processing was successful and PDF was generated, try to send to Discord
        if result["success"] and result.get("pdf_output") and send_to_discord:
            if send_pdf_if_webhook_configured:
                try:
                    # Create a nice message for Discord
                    title = result.get("title", "Untitled")
                    summary = result.get("summary", "")
                    word_count = result.get("word_count", 0)

                    message = f"📄 **{title}**\n\n"
                    if summary:
                        message += f"📝 {summary}\n\n"
                    message += f"📊 Word count: {word_count}"

                    # Send to Discord
                    discord_success = await send_pdf_if_webhook_configured(
                        result["pdf_output"], message
                    )
                    result["discord_sent"] = discord_success
                    if discord_success:
                        print(f"✅ PDF sent to Discord: {result['pdf_output']}")
                    else:
                        print(
                            f"⚠️  Failed to send PDF to Discord: {result['pdf_output']}"
                        )
                except Exception as e:
                    print(f"⚠️  Error sending to Discord: {e}")
                    result["discord_sent"] = False
                    result["discord_error"] = str(e)
            else:
                result["discord_sent"] = False
                result["discord_error"] = "Discord webhook module not available"
        else:
            result["discord_sent"] = False

        return result


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Process markdown files with HTML templating and AI summarization"
    )
    parser.add_argument("input", help="Input markdown file or directory")
    parser.add_argument(
        "-o", "--output", default="output", help="Output directory (default: output)"
    )
    parser.add_argument(
        "-t",
        "--template",
        default="default.html",
        help="HTML template name (default: default.html)",
    )
    parser.add_argument("--template-dir", help="Custom template directory")
    parser.add_argument(
        "--pdf-only", action="store_true", help="Generate only PDF output"
    )
    parser.add_argument(
        "--html-only", action="store_true", help="Generate only HTML output"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--discord",
        action="store_true",
        help="Send PDFs to Discord if webhook is configured",
    )

    args = parser.parse_args()

    # If Discord integration is requested, use async main
    if args.discord:
        asyncio.run(async_main(args))
    else:
        sync_main(args)


def sync_main(args):
    """Synchronous main function (original behavior)."""
    # Initialize processor
    processor = MarkdownProcessor(template_dir=args.template_dir)

    # Process input
    if Path(args.input).is_file():
        # Single file
        result = processor.process_file(args.input, args.output, args.template)
        if result["success"]:
            print(f"✅ Processed: {args.input}")
            print(f"   Title: {result['title']}")
            print(f"   Summary: {result['summary']}")
            print(f"   Word count: {result['word_count']}")
            if result.get("html_output"):
                print(f"   HTML: {result['html_output']}")
            if result.get("pdf_output"):
                print(f"   PDF: {result['pdf_output']}")
        else:
            print(f"❌ Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

    elif Path(args.input).is_dir():
        # Directory
        markdown_files = []
        for root, _dirs, files in os.walk(args.input):
            for file in files:
                if file.lower().endswith(".md"):
                    markdown_files.append(Path(root) / file)

        if not markdown_files:
            print(f"No markdown files found in {args.input}", file=sys.stderr)
            sys.exit(1)

        successful = 0
        for md_file in markdown_files:
            result = processor.process_file(md_file, args.output, args.template)
            if result["success"]:
                successful += 1
                if args.verbose:
                    print(f"✅ Processed: {md_file}")
            else:
                print(
                    f"❌ Error processing {md_file}: {result['error']}", file=sys.stderr
                )

        print(f"Processed {successful}/{len(markdown_files)} files successfully")

    else:
        print(f"Input path not found: {args.input}", file=sys.stderr)
        sys.exit(1)


async def async_main(args):
    """Asynchronous main function with Discord integration."""
    # Initialize processor
    processor = MarkdownProcessor(template_dir=args.template_dir)

    # Process input
    if Path(args.input).is_file():
        # Single file
        result = await processor.process_file_with_discord(
            args.input, args.output, args.template
        )
        if result["success"]:
            print(f"✅ Processed: {args.input}")
            print(f"   Title: {result['title']}")
            print(f"   Summary: {result['summary']}")
            print(f"   Word count: {result['word_count']}")
            if result.get("html_output"):
                print(f"   HTML: {result['html_output']}")
            if result.get("pdf_output"):
                print(f"   PDF: {result['pdf_output']}")
            if result.get("discord_sent"):
                print("   📤 Sent to Discord: ✅")
            elif result.get("discord_error"):
                print(f"   📤 Discord error: {result['discord_error']}")
        else:
            print(f"❌ Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

    elif Path(args.input).is_dir():
        # Directory
        markdown_files = []
        for root, _dirs, files in os.walk(args.input):
            for file in files:
                if file.lower().endswith(".md"):
                    markdown_files.append(Path(root) / file)

        if not markdown_files:
            print(f"No markdown files found in {args.input}", file=sys.stderr)
            sys.exit(1)

        successful = 0
        discord_sent = 0
        for md_file in markdown_files:
            result = await processor.process_file_with_discord(
                md_file, args.output, args.template
            )
            if result["success"]:
                successful += 1
                if result.get("discord_sent"):
                    discord_sent += 1
                if args.verbose:
                    print(f"✅ Processed: {md_file}")
                    if result.get("discord_sent"):
                        print("   📤 Sent to Discord: ✅")
            else:
                print(
                    f"❌ Error processing {md_file}: {result['error']}", file=sys.stderr
                )

        print(f"Processed {successful}/{len(markdown_files)} files successfully")
        print(f"Sent {discord_sent} PDFs to Discord")

    else:
        print(f"Input path not found: {args.input}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
