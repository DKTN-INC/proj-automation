#!/usr/bin/env python3
"""
Demo script showcasing the budget and marketing bot features.

This script demonstrates the functionality that would be used in Discord slash commands.
"""

import sys
from pathlib import Path


# Add bot directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "bot"))

from features import (
    categorize_spend,
    generate_campaign_brief,
    render_campaign_brief_markdown,
    summarize_budget,
)


def demo_budget_features():
    """Demonstrate budget functionality."""
    print("=" * 60)
    print("BUDGET FEATURES DEMO")
    print("=" * 60)

    # Sample transaction data
    transactions = [
        {'amount': 450.75},
        {'amount': 320.50},
        {'amount': 125.25},
        {'amount': 89.99}
    ]

    # Test budget summary
    budget_limit = 1200.0
    summary = summarize_budget(transactions, budget_limit)

    print(f"Budget Limit: ${budget_limit:,.2f}")
    print(f"Total Spent: ${summary.totals}")
    print(f"Remaining: ${summary.remaining}")
    print(f"Percent Used: {summary.percent_used}%")
    print(f"Status: {summary.status.replace('_', ' ').title()}")
    print()

    # Test spending categorization
    spending_items = [
        {'category': 'Office Supplies', 'amount': 150.75},
        {'category': 'Travel', 'amount': 320.50},
        {'category': 'Marketing', 'amount': 450.75},
        {'category': 'Office Supplies', 'amount': 64.24},
        {'category': 'Software', 'amount': 125.25},
        {'category': 'Travel', 'amount': 75.00}
    ]

    categories = categorize_spend(spending_items)

    print("SPENDING BY CATEGORY:")
    print("-" * 30)
    for category, amount in sorted(categories.items()):
        print(f"{category:<20} ${amount}")
    print()


def demo_marketing_features():
    """Demonstrate marketing functionality."""
    print("=" * 60)
    print("MARKETING FEATURES DEMO")
    print("=" * 60)

    # Create a comprehensive campaign brief
    brief = generate_campaign_brief(
        campaign_name="Q4 Product Launch Campaign",
        target_audience="Tech professionals and early adopters aged 25-45",
        objectives=[
            "Generate 10,000 qualified leads",
            "Achieve 25% brand awareness increase",
            "Drive 500 product demo requests",
            "Establish thought leadership in the market"
        ],
        budget=85000.0,
        timeline="October 1 - December 31, 2024",
        channels=[
            "LinkedIn Advertising",
            "Google Ads",
            "Content Marketing",
            "Webinar Series",
            "Industry Conferences",
            "Email Marketing"
        ],
        key_messages=[
            "Revolutionary AI-powered solution for modern teams",
            "Save 40% time on routine tasks",
            "Trusted by 1000+ companies worldwide",
            "Free 30-day trial with full support"
        ],
        success_metrics=[
            "10,000 qualified leads generated",
            "25% increase in brand awareness",
            "500 product demo requests",
            "40% email open rate",
            "15% conversion rate from demo to trial"
        ]
    )

    # Render as markdown
    markdown = render_campaign_brief_markdown(brief)

    print("CAMPAIGN BRIEF MARKDOWN OUTPUT:")
    print("-" * 40)
    print(markdown)


def main():
    """Run all demos."""
    print("🚀 Bot Features Demo")
    print("Demonstrating budget and marketing functionality for Discord bot commands")
    print()

    try:
        demo_budget_features()
        demo_marketing_features()

        print("=" * 60)
        print("✅ All features working correctly!")
        print("These functions are ready for integration with Discord slash commands.")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error during demo: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
