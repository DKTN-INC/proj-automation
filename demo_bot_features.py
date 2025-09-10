#!/usr/bin/env python3
"""
Demo script showing Discord Bot functionality
This demonstrates the core features without requiring Discord tokens
"""

import asyncio
import sys
from pathlib import Path


# Add bot directory to path
sys.path.append(str(Path(__file__).parent / "bot"))

from utils import ai_helper, code_analyzer, file_processor


async def demo_markdown_processing():
    """Demonstrate markdown to HTML conversion."""
    print("🔄 Testing Markdown Processing...")

    test_markdown = """# AI-Powered Feature Demo

**Author:** Demo User  
**Created:** 2024-01-01  
**Tags:** demo, ai, discord-bot

---

## Overview
This demonstrates the Discord bot's markdown processing capabilities.

## Code Example
```python
async def example_function():
    return "Hello, Discord Bot!"
```

## Features
- ✅ Markdown to HTML conversion
- ✅ Code syntax highlighting
- ✅ Professional styling
- ✅ Metadata support

## Next Steps
1. Configure Discord bot token
2. Set up OpenAI API key for AI features
3. Deploy to production server
"""

    html_content = await file_processor.markdown_to_html(test_markdown, "Demo Document")
    print(f"✅ Generated HTML ({len(html_content)} characters)")

    # Save demo HTML file
    output_path = Path("output") / "demo_output.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"💾 Saved to: {output_path}")


async def demo_code_analysis():
    """Demonstrate Python code analysis."""
    print("\n🔍 Testing Code Analysis...")

    test_code = """
def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers)/len(numbers)

# This function has some style issues
def badFunction( x,y ):
    result=x+y
    return result
"""

    issues = await code_analyzer.lint_python_code(test_code)
    print("📋 Linting Results:")
    for issue in issues[:5]:  # Show first 5 issues
        print(f"  - {issue}")


async def demo_ai_features():
    """Demonstrate AI feature availability."""
    print("\n🤖 Testing AI Features...")

    print(f"AI Helper Available: {'✅' if ai_helper.available else '❌'}")

    if not ai_helper.available:
        print("ℹ️  To enable AI features:")
        print("   1. Install: pip install openai tiktoken")
        print("   2. Set OPENAI_API_KEY environment variable")

        # Test fallback tagging
        content = (
            "This is a Python automation script for Discord bots with AI integration"
        )
        tags = ai_helper._fallback_tags(content)
        print(f"📋 Fallback tags generated: {tags}")


async def demo_language_detection():
    """Demonstrate language detection."""
    print("\n🔤 Testing Language Detection...")

    code_samples = {
        "Python": "def hello(): print('Hello World')",
        "JavaScript": "function hello() { console.log('Hello World'); }",
        "Java": "public class Hello { public static void main(String[] args) { } }",
        "C++": "#include <iostream>\nint main() { return 0; }",
    }

    for expected, code in code_samples.items():
        detected = await file_processor.detect_language(code)
        status = "✅" if detected.lower() == expected.lower() else "❌"
        print(f"  {status} {expected}: detected as '{detected}'")


async def main():
    """Run all demonstrations."""
    print("🚀 Discord Bot Feature Demonstration\n")
    print("=" * 50)

    try:
        await demo_markdown_processing()
        await demo_code_analysis()
        await demo_ai_features()
        await demo_language_detection()

        print("\n" + "=" * 50)
        print("✅ All demos completed successfully!")
        print("\n📚 For full documentation, see: docs/bot-integration.md")
        print(
            "🔧 To run the bot, configure tokens in bot/.env and run: python bot/main.py"
        )

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
