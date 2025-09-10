from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader
import weasyprint

class MarkdownProcessor:
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize the processor with optional template directory."""
        self.template_dir = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        self.setup_jinja_env()

    def setup_jinja_env(self):
        """Setup Jinja2 environment for HTML templating."""
        try:
            if self.template_dir.exists():
                self.jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))
            else:
                # Create default templates directory
                self.template_dir.mkdir(parents=True, exist_ok=True)
                self.create_default_templates()
                self.jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        except Exception as e:
            print(f"Error setting up Jinja environment: {e}")
            self.jinja_env = None

    def create_default_templates(self):
        default_template = """</body>
</html>"""  # Replace with your actual template
        template_path = self.template_dir / "default.html"
        with template_path.open("w", encoding="utf-8") as f:
            f.write(default_template)

    def extract_title(self, markdown_content: str) -> str:
        # Placeholder implementation
        return "Document Title"

    def process_file(self, input_path: str, output_path: str):
        """Process a single markdown file."""
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)
            # Validate input file
            if not input_path.exists():
                return {
                    "error": f"Input file not found: {input_path}",
                    "success": False,
                }

            # Read markdown content
            with input_path.open(encoding="utf-8") as f:
                markdown_content = f.read()

            if not markdown_content.strip():
                return {
                    "error": "Markdown file is empty.",
                    "success": False,
                }

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Template and rendering logic would go here...
            html_content = self.render_html(markdown_content)
            # Convert HTML to PDF
            html_doc = weasyprint.HTML(string=html_content)
            html_doc.write_pdf(str(output_path))
            return {
                "success": True,
                "output": str(output_path)
            }
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
            }

    def render_html(self, markdown_content: str) -> str:
        # Placeholder for full markdown-to-HTML conversion and templating
        if self.jinja_env:
            template = self.jinja_env.get_template("default.html")
            return template.render(content=markdown_content, title=self.extract_title(markdown_content))
        return f"<html><body>{markdown_content}</body></html>"
