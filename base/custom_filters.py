"""
Custom template filters for the application
"""

import base64
import locale
import logging

from django import template
from num2words import num2words

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "en_IN")

register = template.Library()

formate = {
    "grouping": True,  # Enable thousands grouping
    "grouping_threshold": 3,  # Group digits in threes
    "decimal_point": ".",  # Use dot as the decimal separator
    "frac_digits": 2,  # Show 2 digits after the decimal point
}


def _convert_to_numeric(value):
    """
    Bulletproof string-to-number converter that handles various input formats.

    Args:
        value: String, int, float, or other value to convert

    Returns:
        float or int: Converted numeric value, or None if conversion fails
    """
    if value is None:
        return None

    # If already a number, return as-is
    if isinstance(value, (int, float)):
        return value

    # Convert to string and clean
    str_value = str(value).strip()

    if not str_value:
        return None

    # Handle empty string
    if str_value == "":
        return None

    # Remove common currency symbols and whitespace
    cleaned_value = str_value.replace("€", "").replace("£", "").replace(",", "").strip()

    # Handle negative numbers
    is_negative = cleaned_value.startswith("-")
    if is_negative:
        cleaned_value = cleaned_value[1:]

    # Handle percentage
    is_percentage = cleaned_value.endswith("%")
    if is_percentage:
        cleaned_value = cleaned_value[:-1]

    try:
        # Try to convert to float first (handles decimals)
        numeric_value = float(cleaned_value)

        # Apply percentage conversion if needed
        if is_percentage:
            numeric_value = numeric_value / 100

        # Apply negative sign if needed
        if is_negative:
            numeric_value = -numeric_value

        # Return as int if it's a whole number and not too large
        if numeric_value.is_integer() and abs(numeric_value) < 1e15:
            return int(numeric_value)

        return numeric_value

    except (ValueError, OverflowError) as e:
        logger.warning(f"Failed to convert '{value}' to numeric: {e}")
        return None


@register.filter(name="currency")
def currency(value, arg=None):
    """
    Bulletproof currency formatter that handles strings, integers, floats, and None values.
    Converts string inputs to appropriate numeric types before formatting.
    """
    try:
        if value is None or value == "":
            return "0.00"

        # Convert string to number if needed
        numeric_value = _convert_to_numeric(value)

        if numeric_value is None:
            return "0.00"

        data = locale.format_string(
            "%%.%df" % formate["frac_digits"],
            numeric_value,
            grouping=formate["grouping"],
            monetary=False,
        )
        return data
    except (TypeError, ValueError, locale.Error) as e:
        return "0.00"


@register.filter(name="currency_nonDecimal")
def currency_nonDecimal(value, arg=None):
    """
    Bulletproof non-decimal currency formatter for integer values.
    """
    try:
        if value is None or value == "":
            return "0"

        # Convert string to number if needed
        numeric_value = _convert_to_numeric(value)

        if numeric_value is None:
            return "0"

        # Convert to integer
        value_int = int(numeric_value)

        return locale.format_string(
            "%d",
            value_int,
            grouping=formate["grouping"],
            monetary=False,
        )
    except (TypeError, ValueError, locale.Error) as e:
        return "0"


@register.filter(name="phone_number")
def phone_number(value):
    if value is None:
        return ""
    try:
        numbers = value.replace(" ", "")
        return f"{numbers[:5]} {numbers[5:]}" if len(numbers) == 10 else numbers
    except (TypeError, ValueError) as e:
        logger.error(e)
        return value


@register.filter(name="mult")
def mult(value, arg):
    """Multiply two values."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def assembly_totals(assembly):
    """Return dict with unique_items, total_qty, total_amount for an assembly."""
    items = assembly.assembly_product_items.all()
    unique = items.count()
    total_qty = sum(item.quantity_required for item in items)
    total_amount = sum(item.selling_price * item.quantity_required for item in items)
    return {"unique": unique, "qty": total_qty, "amount": total_amount}


@register.filter(name="range")
def filter_range(start):
    try:
        return range(int(start))
    except (TypeError, ValueError):
        return []


@register.filter(name="b64encode")
def base64_encode(value):
    """Encode a string or bytes using base64 and return a UTF-8 string."""
    return base64.b64encode(value).decode("utf-8")


@register.filter(name="get_item")
def get_item(dictionary, key):
    """Get item from dictionary by key."""
    try:
        return dictionary.get(key, 0)
    except (AttributeError, TypeError):
        return 0


@register.filter(name="currencyToWord")
def currency_to_word(value, _arg=None):
    """Convert currency value to Indian Rupess text format."""
    try:
        amount = float(value)
        return num2words(amount, lang="en_IN", to="currency", currency="INR").title()
    except (ValueError, TypeError) as e:
        logger.error("Currency to word formatting error for value '%s': %s", value, e)
        return value
