"""
Unit tests for budget functionality.

Tests the budget summarization and spending categorization features.
"""

import sys
from decimal import Decimal
from pathlib import Path


# Add bot directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))

from features.budget import categorize_spend, summarize_budget  # noqa: E402


def test_summarize_budget_empty_transactions():
    """Test budget summary with no transactions."""
    result = summarize_budget([], 1000)

    assert result.totals == Decimal("0")
    assert result.remaining == Decimal("1000")
    assert result.percent_used == 0.0
    assert result.status == "unused"


def test_summarize_budget_under_budget():
    """Test budget summary when under budget."""
    transactions = [{"amount": 100.50}, {"amount": 250.25}]
    result = summarize_budget(transactions, 1000)

    assert result.totals == Decimal("350.75")
    assert result.remaining == Decimal("649.25")
    assert abs(result.percent_used - 35.1) < 0.01
    assert result.status == "under_budget"


def test_summarize_budget_on_track():
    """Test budget summary when on track (50-79% used)."""
    transactions = [{"amount": 300}, {"amount": 400}]
    result = summarize_budget(transactions, 1000)

    assert result.totals == Decimal("700")
    assert result.remaining == Decimal("300")
    assert abs(result.percent_used - 70.0) < 0.01
    assert result.status == "on_track"


def test_summarize_budget_warning():
    """Test budget summary when in warning range (80-99% used)."""
    transactions = [{"amount": 450}, {"amount": 400}]
    result = summarize_budget(transactions, 1000)

    assert result.totals == Decimal("850")
    assert result.remaining == Decimal("150")
    assert abs(result.percent_used - 85.0) < 0.01
    assert result.status == "warning"


def test_summarize_budget_over_budget():
    """Test budget summary when over budget (100%+ used)."""
    transactions = [{"amount": 600}, {"amount": 500}]
    result = summarize_budget(transactions, 1000)

    assert result.totals == Decimal("1100")
    assert result.remaining == Decimal("-100")
    assert abs(result.percent_used - 110.0) < 0.01
    assert result.status == "over_budget"


def test_summarize_budget_with_decimal_limit():
    """Test budget summary with Decimal limit."""
    transactions = [{"amount": 123.45}]
    result = summarize_budget(transactions, Decimal("500.00"))

    assert result.totals == Decimal("123.45")
    assert result.remaining == Decimal("376.55")
    assert abs(result.percent_used - 24.7) < 0.01
    assert result.status == "under_budget"


def test_categorize_spend_empty_items():
    """Test categorization with no items."""
    result = categorize_spend([])
    assert result == {}


def test_categorize_spend_default_keys():
    """Test categorization with default category and amount keys."""
    items = [
        {"category": "Food", "amount": 150.75},
        {"category": "Transport", "amount": 50.25},
        {"category": "Food", "amount": 75.50},
    ]
    result = categorize_spend(items)

    expected = {"Food": Decimal("226.25"), "Transport": Decimal("50.25")}
    assert result == expected


def test_categorize_spend_custom_keys():
    """Test categorization with custom category and amount keys."""
    items = [
        {"type": "Office", "cost": 100},
        {"type": "Travel", "cost": 200},
        {"type": "Office", "cost": 50},
    ]
    result = categorize_spend(items, category_key="type", amount_key="cost")

    expected = {"Office": Decimal("150.00"), "Travel": Decimal("200.00")}
    assert result == expected


def test_categorize_spend_missing_category():
    """Test categorization when category is missing."""
    items = [{"amount": 100}, {"category": "Food", "amount": 50}]
    result = categorize_spend(items)

    expected = {"uncategorized": Decimal("100.00"), "Food": Decimal("50.00")}
    assert result == expected


def test_categorize_spend_missing_amount():
    """Test categorization when amount is missing."""
    items = [{"category": "Food"}, {"category": "Transport", "amount": 100}]
    result = categorize_spend(items)

    expected = {"Food": Decimal("0.00"), "Transport": Decimal("100.00")}
    assert result == expected


def test_categorize_spend_decimal_precision():
    """Test that categorization rounds to 2 decimal places."""
    items = [
        {"category": "Test", "amount": 10.555},
        {"category": "Test", "amount": 20.444},
    ]
    result = categorize_spend(items)

    # Should round to 30.56 + 20.44 = 31.00
    expected = {"Test": Decimal("31.00")}
    assert result == expected


def run_all_tests():
    """Run all budget tests."""
    test_functions = [
        test_summarize_budget_empty_transactions,
        test_summarize_budget_under_budget,
        test_summarize_budget_on_track,
        test_summarize_budget_warning,
        test_summarize_budget_over_budget,
        test_summarize_budget_with_decimal_limit,
        test_categorize_spend_empty_items,
        test_categorize_spend_default_keys,
        test_categorize_spend_custom_keys,
        test_categorize_spend_missing_category,
        test_categorize_spend_missing_amount,
        test_categorize_spend_decimal_precision,
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

    print(f"\nBudget Tests: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
