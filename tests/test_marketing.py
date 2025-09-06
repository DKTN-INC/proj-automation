"""
Unit tests for marketing functionality.

Tests the campaign brief generation and Markdown rendering features.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add bot directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))

from features.marketing import (  # noqa: E402
    generate_campaign_brief, render_campaign_brief_markdown, CampaignBrief
)


def test_generate_campaign_brief_minimal():
    """Test campaign brief generation with minimal required fields."""
    brief = generate_campaign_brief(
        campaign_name="Test Campaign",
        target_audience="Young adults 18-25",
        objectives=["Increase brand awareness", "Drive website traffic"]
    )

    assert brief.campaign_name == "Test Campaign"
    assert brief.target_audience == "Young adults 18-25"
    assert brief.objectives == ["Increase brand awareness", "Drive website traffic"]
    assert brief.budget is None
    assert brief.timeline is None
    assert brief.channels == []
    assert brief.key_messages == []
    assert brief.success_metrics == []
    assert brief.created_at is not None
    assert isinstance(brief.created_at, datetime)


def test_generate_campaign_brief_full():
    """Test campaign brief generation with all fields."""
    brief = generate_campaign_brief(
        campaign_name="Summer Sale Campaign",
        target_audience="Existing customers and potential buyers",
        objectives=["Increase sales by 30%", "Clear summer inventory"],
        budget=50000.0,
        timeline="June 1 - August 31, 2024",
        channels=["Email", "Social Media", "Google Ads"],
        key_messages=["Save 40% on summer items", "Limited time offer"],
        success_metrics=["30% sales increase", "50% inventory clearance"]
    )

    assert brief.campaign_name == "Summer Sale Campaign"
    assert brief.target_audience == "Existing customers and potential buyers"
    assert brief.objectives == ["Increase sales by 30%", "Clear summer inventory"]
    assert brief.budget == 50000.0
    assert brief.timeline == "June 1 - August 31, 2024"
    assert brief.channels == ["Email", "Social Media", "Google Ads"]
    assert brief.key_messages == ["Save 40% on summer items", "Limited time offer"]
    assert brief.success_metrics == ["30% sales increase", "50% inventory clearance"]
    assert brief.created_at is not None


def test_render_campaign_brief_markdown_minimal():
    """Test Markdown rendering with minimal campaign brief."""
    brief = CampaignBrief(
        campaign_name="Basic Campaign",
        target_audience="General audience",
        objectives=["Goal 1", "Goal 2"]
    )

    markdown = render_campaign_brief_markdown(brief)

    assert "# Basic Campaign" in markdown
    assert "## Target Audience" in markdown
    assert "General audience" in markdown
    assert "## Objectives" in markdown
    assert "- Goal 1" in markdown
    assert "- Goal 2" in markdown
    assert "## Budget" not in markdown  # Should not appear when None
    assert "## Timeline" not in markdown  # Should not appear when None


def test_render_campaign_brief_markdown_with_budget():
    """Test Markdown rendering with budget."""
    brief = CampaignBrief(
        campaign_name="Budget Campaign",
        target_audience="Target group",
        objectives=["Objective 1"],
        budget=12345.67
    )

    markdown = render_campaign_brief_markdown(brief)

    assert "## Budget" in markdown
    assert "$12,345.67" in markdown


def test_render_campaign_brief_markdown_with_timeline():
    """Test Markdown rendering with timeline."""
    brief = CampaignBrief(
        campaign_name="Timeline Campaign",
        target_audience="Target group",
        objectives=["Objective 1"],
        timeline="Q1 2024"
    )

    markdown = render_campaign_brief_markdown(brief)

    assert "## Timeline" in markdown
    assert "Q1 2024" in markdown


def test_render_campaign_brief_markdown_with_channels():
    """Test Markdown rendering with marketing channels."""
    brief = CampaignBrief(
        campaign_name="Channels Campaign",
        target_audience="Target group",
        objectives=["Objective 1"],
        channels=["Email", "Facebook", "Google Ads"]
    )

    markdown = render_campaign_brief_markdown(brief)

    assert "## Marketing Channels" in markdown
    assert "- Email" in markdown
    assert "- Facebook" in markdown
    assert "- Google Ads" in markdown


def test_render_campaign_brief_markdown_with_key_messages():
    """Test Markdown rendering with key messages."""
    brief = CampaignBrief(
        campaign_name="Messages Campaign",
        target_audience="Target group",
        objectives=["Objective 1"],
        key_messages=["Message 1", "Message 2"]
    )

    markdown = render_campaign_brief_markdown(brief)

    assert "## Key Messages" in markdown
    assert "- Message 1" in markdown
    assert "- Message 2" in markdown


def test_render_campaign_brief_markdown_with_success_metrics():
    """Test Markdown rendering with success metrics."""
    brief = CampaignBrief(
        campaign_name="Metrics Campaign",
        target_audience="Target group",
        objectives=["Objective 1"],
        success_metrics=["Metric 1", "Metric 2"]
    )

    markdown = render_campaign_brief_markdown(brief)

    assert "## Success Metrics" in markdown
    assert "- Metric 1" in markdown
    assert "- Metric 2" in markdown


def test_render_campaign_brief_markdown_with_created_at():
    """Test Markdown rendering with creation timestamp."""
    test_time = datetime(2024, 6, 15, 14, 30, 0)
    brief = CampaignBrief(
        campaign_name="Timestamp Campaign",
        target_audience="Target group",
        objectives=["Objective 1"],
        created_at=test_time
    )

    markdown = render_campaign_brief_markdown(brief)

    assert "## Created" in markdown
    assert "2024-06-15 14:30:00" in markdown


def test_render_campaign_brief_markdown_full():
    """Test Markdown rendering with all fields populated."""
    test_time = datetime(2024, 1, 1, 12, 0, 0)
    brief = CampaignBrief(
        campaign_name="Complete Campaign",
        target_audience="All demographics",
        objectives=["Obj 1", "Obj 2"],
        budget=10000.0,
        timeline="Full year",
        channels=["Channel A", "Channel B"],
        key_messages=["Message A", "Message B"],
        success_metrics=["Metric A", "Metric B"],
        created_at=test_time
    )

    markdown = render_campaign_brief_markdown(brief)

    # Check all sections are present
    assert "# Complete Campaign" in markdown
    assert "## Target Audience" in markdown
    assert "All demographics" in markdown
    assert "## Objectives" in markdown
    assert "- Obj 1" in markdown
    assert "- Obj 2" in markdown
    assert "## Budget" in markdown
    assert "$10,000.00" in markdown
    assert "## Timeline" in markdown
    assert "Full year" in markdown
    assert "## Marketing Channels" in markdown
    assert "- Channel A" in markdown
    assert "- Channel B" in markdown
    assert "## Key Messages" in markdown
    assert "- Message A" in markdown
    assert "- Message B" in markdown
    assert "## Success Metrics" in markdown
    assert "- Metric A" in markdown
    assert "- Metric B" in markdown
    assert "## Created" in markdown
    assert "2024-01-01 12:00:00" in markdown


def test_render_campaign_brief_markdown_empty_lists():
    """Test Markdown rendering with empty lists (should not show sections)."""
    brief = CampaignBrief(
        campaign_name="Empty Lists Campaign",
        target_audience="Target group",
        objectives=["Objective 1"],
        channels=[],
        key_messages=[],
        success_metrics=[]
    )

    markdown = render_campaign_brief_markdown(brief)

    # Empty lists should not create sections
    assert "## Marketing Channels" not in markdown
    assert "## Key Messages" not in markdown
    assert "## Success Metrics" not in markdown


def run_all_tests():
    """Run all marketing tests."""
    test_functions = [
        test_generate_campaign_brief_minimal,
        test_generate_campaign_brief_full,
        test_render_campaign_brief_markdown_minimal,
        test_render_campaign_brief_markdown_with_budget,
        test_render_campaign_brief_markdown_with_timeline,
        test_render_campaign_brief_markdown_with_channels,
        test_render_campaign_brief_markdown_with_key_messages,
        test_render_campaign_brief_markdown_with_success_metrics,
        test_render_campaign_brief_markdown_with_created_at,
        test_render_campaign_brief_markdown_full,
        test_render_campaign_brief_markdown_empty_lists
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\nMarketing Tests: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
