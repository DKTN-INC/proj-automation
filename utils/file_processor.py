"""Minimal file_processor shim implementing markdown->HTML and HTML->PDF.

This avoids importing `bot.utils` and provides a small, self-contained
implementation used by the smoke-test harness and compatibility imports.
"""
from pathlib import Path
import re
import markdown
from jinja2 import Template


async def markdown_to_html(markdown_content: str, title: str = "Document") -> str:
    try:
        html_content = markdown.markdown(
            markdown_content, extensions=["codehilite", "toc", "tables", "fenced_code"]
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

    try:
        rendered = re.sub(r"<script[\s\S]*?>[\s\S]*?<\/script>", "", rendered, flags=re.IGNORECASE)
    except Exception:
        pass

    return rendered


def html_to_pdf(html_content: str, out_path: Path) -> bool:
    try:
        import pdfkit

        options = {
            "page-size": "A4",
            "margin-top": "0.75in",
            "margin-right": "0.75in",
            "margin-bottom": "0.75in",
            "margin-left": "0.75in",
            "encoding": "UTF-8",
            "no-outline": None,
        }
        pdfkit.from_string(html_content, str(out_path), options=options)
        return True
    except Exception:
        try:
            # Fallback: write text file explaining missing PDF backend
            p = out_path.with_suffix(".txt")
            p.write_text("PDF generation not available - pdfkit or native libs missing\n\n" + html_content, encoding="utf-8")
        except Exception:
            pass
        return False
