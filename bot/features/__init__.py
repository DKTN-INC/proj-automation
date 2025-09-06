"""
Bot features module for Project Automation Discord Bot.

This module provides feature implementations for budget and marketing commands.
"""

from .budget import BudgetSummary, categorize_spend, summarize_budget
from .marketing import CampaignBrief, generate_campaign_brief, render_campaign_brief_markdown


__all__ = [
    "summarize_budget",
    "categorize_spend",
    "BudgetSummary",
    "generate_campaign_brief",
    "render_campaign_brief_markdown",
    "CampaignBrief",
]
