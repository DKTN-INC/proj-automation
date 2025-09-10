"""
Budget management features for Discord bot.

Provides functionality to summarize budgets and categorize spending.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Union
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class BudgetSummary:
    """Budget summary with totals, remaining amount, usage %, and status."""
    totals: Decimal
    remaining: Decimal
    percent_used: float
    status: str


def summarize_budget(transactions: List[Dict[str, Any]],
                     limit: Union[Decimal, float, int]) -> BudgetSummary:
    """
    Summarize budget based on transactions and spending limit.

    Args:
        transactions: List of transaction dictionaries with 'amount' key
        limit: Budget limit as Decimal, float, or int

    Returns:
        BudgetSummary with calculated totals, remaining, percent_used, and status
    """
    if not transactions:
        limit_decimal = Decimal(str(limit))
        return BudgetSummary(
            totals=Decimal('0'),
            remaining=limit_decimal,
            percent_used=0.0,
            status="unused"
        )

    # Convert limit to Decimal for precise calculations
    limit_decimal = Decimal(str(limit))

    # Sum all transaction amounts
    total_spent = Decimal('0')
    for transaction in transactions:
        amount = transaction.get('amount', 0)
        total_spent += Decimal(str(amount))

    # Calculate remaining and percentage
    remaining = limit_decimal - total_spent
    percent_used = float((total_spent / limit_decimal * 100).quantize(
        Decimal('0.1'), rounding=ROUND_HALF_UP))

    # Determine status
    if percent_used >= 100:
        status = "over_budget"
    elif percent_used >= 80:
        status = "warning"
    elif percent_used >= 50:
        status = "on_track"
    else:
        status = "under_budget"

    return BudgetSummary(
        totals=total_spent,
        remaining=remaining,
        percent_used=percent_used,
        status=status
    )


def categorize_spend(items: List[Dict[str, Any]],
                     category_key: str = "category",
                     amount_key: str = "amount") -> Dict[str, Decimal]:
    """
    Categorize and aggregate spending by category.

    Args:
        items: List of spending items with category and amount keys
        category_key: Key name for category in item dictionaries
        amount_key: Key name for amount in item dictionaries

    Returns:
        Dictionary mapping category names to aggregated amounts
    """
    if not items:
        return {}

    category_totals: Dict[str, Decimal] = {}

    for item in items:
        category = item.get(category_key, "uncategorized")
        amount = item.get(amount_key, 0)

        # Convert to Decimal for precise calculations
        amount_decimal = Decimal(str(amount))

        if category in category_totals:
            category_totals[category] += amount_decimal
        else:
            category_totals[category] = amount_decimal

    # Round all amounts to 2 decimal places
    for category in category_totals:
        category_totals[category] = category_totals[category].quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)

    return category_totals
