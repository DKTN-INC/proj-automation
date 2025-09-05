# Processing System Documentation

## Overview

The Project Automation platform now includes a comprehensive markdown processing system with HTML templating, table of contents generation, and AI summarization features.

## Features

### 🎨 HTML Templating
- **Jinja2-based templates** for flexible document rendering
- **Responsive design** with modern CSS styling
- **Professional appearance** suitable for business use
- **Customizable themes** for different document types

### 📚 Table of Contents
- **Automatic generation** from markdown headers
- **Hierarchical structure** with proper nesting
- **Clickable navigation** for easy document traversal
- **Responsive layout** that adapts to content

### 🤖 AI Summarization
- **Extractive summarization** for quick document overviews
- **Key topic identification** from content analysis
- **Sentiment analysis** for team activity monitoring
- **Multi-format support** (Markdown, HTML, JSON)

### ✅ Error Checking
- **Input validation** for all parameters
- **File existence checks** before processing
- **Comprehensive error messages** for debugging
- **Graceful failure handling** with detailed logs

## Quick Start

### Processing Ideasheets

```bash
# Check dependencies and validate setup
./scripts/process_ideasheets.sh --check

# Process all markdown files in docs/ideasheets/
./scripts/process_ideasheets.sh

# Process with verbose output
./scripts/process_ideasheets.sh --verbose

# Clean output directory before processing
./scripts/process_ideasheets.sh --clean
```

### Using the Python Module Directly

```bash
# Process a single file
python scripts/markdown_processor.py docs/ideasheets/example.md -o output

# Process entire directory
python scripts/markdown_processor.py docs/ideasheets/ -o output -v

# Use custom template
python scripts/markdown_processor.py input.md -o output -t custom.html --template-dir templates/
```

## Command Line Options

### process_ideasheets.sh

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message |
| `-v, --verbose` | Enable verbose output |
| `-c, --check` | Only check dependencies and validate setup |
| `--clean` | Clean output directory before processing |

### markdown_processor.py

| Option | Description |
|--------|-------------|
| `input` | Input markdown file or directory (required) |
| `-o, --output` | Output directory (default: output) |
| `-t, --template` | HTML template name (default: default.html) |
| `--template-dir` | Custom template directory |
| `--pdf-only` | Generate only PDF output |
| `--html-only` | Generate only HTML output |
| `-v, --verbose` | Verbose output |

## Templates

### Default Template

The system includes a professional default template with:
- Modern typography and spacing
- Responsive design for all screen sizes
- Color-coded sections for different content types
- Professional color scheme suitable for business use

### Custom Templates

Create custom templates in the `scripts/templates/` directory:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title or 'Document' }}</title>
    <!-- Your custom styles -->
</head>
<body>
    {% if summary %}
    <div class="summary">
        <h3>📄 Summary</h3>
        <p>{{ summary }}</p>
    </div>
    {% endif %}
    
    {% if toc %}
    <div class="toc">
        <h2>📚 Contents</h2>
        {{ toc | safe }}
    </div>
    {% endif %}
    
    <main>
        {{ content | safe }}
    </main>
    
    {% if metadata %}
    <div class="metadata">
        <p>Generated: {{ metadata.generated_at }}</p>
    </div>
    {% endif %}
</body>
</html>
```

### Template Variables

Available variables in templates:

- `title` - Document title (extracted from first H1)
- `content` - Processed HTML content
- `toc` - Table of contents HTML
- `summary` - AI-generated summary
- `metadata` - Processing metadata including:
  - `generated_at` - Generation timestamp
  - `file_path` - Source file path
  - `word_count` - Document word count

## CI/CD Integration

### Automatic Processing Workflow

The `process-ideasheets.yml` workflow automatically:
1. **Triggers** on changes to `docs/ideasheets/**/*.md`
2. **Validates** all inputs and dependencies
3. **Processes** changed files or entire directory
4. **Generates** HTML and PDF outputs
5. **Creates** downloadable artifacts
6. **Comments** on PRs with processing results

### Workflow Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `force_process_all` | Process all files, not just changed | false |
| `output_format` | Output format (both/html-only/pdf-only) | both |

### Enhanced Standup Workflows

Both standup workflows now include:
- **Input validation** with error checking
- **AI summarization** of team activity
- **Multiple output formats** (Markdown, HTML, JSON)
- **Repository insights** and analytics
- **Artifact generation** for downloads

## Error Handling

The system includes comprehensive error handling:

### Input Validation
- File existence checks
- Markdown file validation
- Directory permission checks
- Parameter format validation

### Processing Errors
- Markdown parsing failures
- Template rendering errors
- PDF conversion issues
- File system errors

### Error Messages
All errors include:
- Clear description of the problem
- Suggested solutions when applicable
- File paths and line numbers when relevant
- Exit codes for script automation

## Dependencies

### System Requirements
- Python 3.8+
- Modern Linux distribution
- System fonts for PDF generation

### Python Packages
- `markdown>=3.4.0` - Core markdown processing
- `Jinja2>=3.1.0` - Template engine
- `weasyprint>=59.0` - PDF generation
- `pymdown-extensions>=10.0.0` - Enhanced markdown features

### System Packages
- `libpango-1.0-0` - Text rendering
- `libharfbuzz0b` - Font shaping
- `libfontconfig1` - Font configuration
- `fonts-dejavu-core` - Default fonts

## Troubleshooting

### Common Issues

#### "No module named 'markdown'"
```bash
pip install -r requirements.txt --user
```

#### "WeasyPrint cannot find fonts"
```bash
sudo apt-get install fonts-dejavu-core libfontconfig1
```

#### "Permission denied" when writing output
```bash
chmod 755 output/
# or
./scripts/process_ideasheets.sh --clean
```

#### PDF generation fails
Ensure all system dependencies are installed:
```bash
sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
```

### Debug Mode

Enable verbose output for debugging:
```bash
./scripts/process_ideasheets.sh --verbose
python scripts/markdown_processor.py input.md -o output -v
```

## Contributing

### Adding New Features

1. **Update the processor** in `scripts/markdown_processor.py`
2. **Add tests** for new functionality
3. **Update templates** if needed
4. **Document changes** in this file

### Template Development

1. Create templates in `scripts/templates/`
2. Use existing template variables
3. Test with sample content
4. Document custom variables

### Workflow Enhancement

1. Update workflow files in `.github/workflows/`
2. Test with sample data
3. Validate error handling
4. Update documentation

## Security Considerations

- **Input sanitization** prevents injection attacks
- **File path validation** prevents directory traversal
- **Template isolation** prevents code execution
- **Error message filtering** prevents information leakage

## Performance

### Optimization Tips
- Process files individually for large repositories
- Use `--html-only` for faster processing when PDFs aren't needed
- Cache templates for repeated processing
- Use `.gitignore` to exclude output directories

### Resource Usage
- **Memory**: ~50MB per large document
- **CPU**: Moderate during PDF generation
- **Disk**: ~2x source file size for outputs
- **Network**: None (offline processing)

## License

This processing system is part of the Project Automation platform and follows the same MIT license terms.