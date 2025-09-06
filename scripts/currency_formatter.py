#!/usr/bin/env python3
"""
Currency Formatting Utilities
Provides currency formatting with locale support including UK defaults
"""

from decimal import Decimal


class CurrencyFormatter:
    """Currency formatter with locale support and UK defaults."""

    # UK defaults
    UK_DEFAULTS = {
        "currency_code": "GBP",
        "locale_name": "en_GB",
        "symbol": "£",
        "decimal_places": 2,
        "symbol_position": "before",  # before or after the amount
    }

    def __init__(
        self,
        currency_code: str = "GBP",
        locale_name: str = "en_GB",
        symbol: str = "£",
        decimal_places: int = 2,
        symbol_position: str = "before",
    ):
        """
        Initialize currency formatter.

        Args:
            currency_code: Currency code (e.g., GBP, USD, EUR)
            locale_name: Locale name (e.g., en_GB, en_US, fr_FR)
            symbol: Currency symbol (e.g., £, $, €)
            decimal_places: Number of decimal places
            symbol_position: Position of symbol ('before' or 'after')
        """
        self.currency_code = currency_code
        self.locale_name = locale_name
        self.symbol = symbol
        self.decimal_places = decimal_places
        self.symbol_position = symbol_position

    @classmethod
    def uk_default(cls):
        """Create formatter with UK defaults (GBP, en_GB, £)."""
        return cls(**cls.UK_DEFAULTS)

    def format_amount(self, amount: float | int | str | Decimal) -> str:
        """
        Format an amount with currency symbol and locale formatting.

        Args:
            amount: Amount to format

        Returns:
            Formatted currency string
        """
        try:
            # Convert to Decimal for precise arithmetic
            if isinstance(amount, str):
                decimal_amount = Decimal(amount)
            else:
                decimal_amount = Decimal(str(amount))

            # Round to specified decimal places
            rounded_amount = round(decimal_amount, self.decimal_places)

            # Format with commas for thousands separator
            formatted_number = f"{rounded_amount:,.{self.decimal_places}f}"

            # Apply currency symbol
            if self.symbol_position == "before":
                return f"{self.symbol}{formatted_number}"
            else:
                return f"{formatted_number} {self.symbol}"

        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount for currency formatting: {amount}") from e

    def format_with_code(self, amount: float | int | str | Decimal) -> str:
        """
        Format amount with currency code instead of symbol.

        Args:
            amount: Amount to format

        Returns:
            Formatted currency string with code
        """
        try:
            decimal_amount = Decimal(str(amount))
            rounded_amount = round(decimal_amount, self.decimal_places)
            formatted_number = f"{rounded_amount:,.{self.decimal_places}f}"
            return f"{formatted_number} {self.currency_code}"
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount for currency formatting: {amount}") from e

    def parse_amount(self, formatted_amount: str) -> Decimal:
        """
        Parse a formatted currency string back to decimal amount.

        Args:
            formatted_amount: Formatted currency string

        Returns:
            Decimal amount
        """
        try:
            # Remove currency symbol and code
            clean_amount = (
                formatted_amount.replace(self.symbol, "").replace(self.currency_code, "").strip()
            )
            # Remove thousands separators
            clean_amount = clean_amount.replace(",", "")
            return Decimal(clean_amount)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid formatted amount: {formatted_amount}") from e


# Convenience functions for common currencies
def format_gbp(amount: float | int | str | Decimal) -> str:
    """Format amount as GBP with UK defaults."""
    formatter = CurrencyFormatter.uk_default()
    return formatter.format_amount(amount)


def format_usd(amount: float | int | str | Decimal) -> str:
    """Format amount as USD."""
    formatter = CurrencyFormatter(
        currency_code="USD",
        locale_name="en_US",
        symbol="$",
        decimal_places=2,
        symbol_position="before",
    )
    return formatter.format_amount(amount)


def format_eur(amount: float | int | str | Decimal) -> str:
    """Format amount as EUR."""
    formatter = CurrencyFormatter(
        currency_code="EUR",
        locale_name="en_EU",
        symbol="€",
        decimal_places=2,
        symbol_position="before",
    )
    return formatter.format_amount(amount)


if __name__ == "__main__":
    # Demo usage
    print("Currency Formatter Demo")
    print("=" * 30)

    # UK GBP formatting (default)
    formatter = CurrencyFormatter.uk_default()
    amounts = [1234.56, 1000000, 0.99, 42]

    print("UK GBP Formatting:")
    for amount in amounts:
        formatted = formatter.format_amount(amount)
        with_code = formatter.format_with_code(amount)
        print(f"  {amount:>10} -> {formatted:>12} | {with_code}")

    print("\nConvenience functions:")
    test_amount = 1234.56
    print(f"  GBP: {format_gbp(test_amount)}")
    print(f"  USD: {format_usd(test_amount)}")
    print(f"  EUR: {format_eur(test_amount)}")

    print("\nParsing test:")
    formatted = format_gbp(1234.56)
    parsed = formatter.parse_amount(formatted)
    print(f"  Formatted: {formatted}")
    print(f"  Parsed back: {parsed}")
