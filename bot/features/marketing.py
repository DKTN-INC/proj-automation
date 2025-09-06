"""
Marketing campaign features for Discord bot.

Provides functionality to generate campaign briefs and render them as Markdown.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class CampaignBrief:
    """Campaign brief containing all necessary information for a marketing campaign."""
    campaign_name: str
    target_audience: str
    objectives: List[str]
    budget: Optional[float] = None
    timeline: Optional[str] = None
    channels: Optional[List[str]] = None
    key_messages: Optional[List[str]] = None
    success_metrics: Optional[List[str]] = None
    created_at: Optional[datetime] = None


def generate_campaign_brief(
    campaign_name: str,
    target_audience: str,
    objectives: List[str],
    budget: Optional[float] = None,
    timeline: Optional[str] = None,
    channels: Optional[List[str]] = None,
    key_messages: Optional[List[str]] = None,
    success_metrics: Optional[List[str]] = None
) -> CampaignBrief:
    """
    Generate a campaign brief with the provided information.

    Args:
        campaign_name: Name of the marketing campaign
        target_audience: Description of the target audience
        objectives: List of campaign objectives
        budget: Optional campaign budget
        timeline: Optional timeline description
        channels: Optional list of marketing channels
        key_messages: Optional list of key marketing messages
        success_metrics: Optional list of success metrics

    Returns:
        CampaignBrief dataclass with all provided information
    """
    return CampaignBrief(
        campaign_name=campaign_name,
        target_audience=target_audience,
        objectives=objectives,
        budget=budget,
        timeline=timeline,
        channels=channels or [],
        key_messages=key_messages or [],
        success_metrics=success_metrics or [],
        created_at=datetime.now()
    )


def render_campaign_brief_markdown(brief: CampaignBrief) -> str:
    """
    Render a campaign brief as formatted Markdown.

    Args:
        brief: CampaignBrief instance to render

    Returns:
        Formatted Markdown string
    """
    lines = [
        f"# {brief.campaign_name}",
        "",
        "## Target Audience",
        brief.target_audience,
        "",
        "## Objectives"
    ]

    # Add objectives as bullet points
    for objective in brief.objectives:
        lines.append(f"- {objective}")
    lines.append("")

    # Add budget if provided
    if brief.budget is not None:
        lines.extend([
            "## Budget",
            f"${brief.budget:,.2f}",
            ""
        ])

    # Add timeline if provided
    if brief.timeline:
        lines.extend([
            "## Timeline",
            brief.timeline,
            ""
        ])

    # Add channels if provided
    if brief.channels:
        lines.extend(["## Marketing Channels"])
        for channel in brief.channels:
            lines.append(f"- {channel}")
        lines.append("")

    # Add key messages if provided
    if brief.key_messages:
        lines.extend(["## Key Messages"])
        for message in brief.key_messages:
            lines.append(f"- {message}")
        lines.append("")

    # Add success metrics if provided
    if brief.success_metrics:
        lines.extend(["## Success Metrics"])
        for metric in brief.success_metrics:
            lines.append(f"- {metric}")
        lines.append("")

    # Add creation timestamp
    if brief.created_at:
        lines.extend([
            "## Created",
            brief.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ""
        ])

    return "\n".join(lines).rstrip() + "\n"
