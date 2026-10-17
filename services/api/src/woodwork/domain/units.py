"""Exact measurements. Input precision is rejected, derived precision is resolved."""
from fractions import Fraction
import re

from .errors import DomainError, finding

MM_PATTERN = r"^(?:0|[1-9][0-9]*)(?:\.[0-9]{0,5}[1-9])?$"
DECIMAL_PATTERN = r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
DENOMINATORS = {1, 2, 4, 8, 16, 32, 64}
UNIT_FACTORS = {"mm": Fraction(1), "cm": Fraction(10), "in": Fraction(127, 5)}


def exact_decimal(value: Fraction | str | int) -> str:
    """Serialize a terminating fraction without Decimal-context rounding."""
    value = Fraction(value)
    negative = value < 0
    numerator = abs(value.numerator)
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ValueError("Nonterminating fraction needs explicit resolution.")
    places = max(twos, fives)
    scaled = numerator * 2 ** (places - twos) * 5 ** (places - fives)
    if places:
        digits = str(scaled).rjust(places + 1, "0")
        text = (digits[:-places] + "." + digits[-places:]).rstrip("0").rstrip(".")
    else:
        text = str(scaled)
    return ("-" if negative and scaled else "") + text


def resolve_mm(value: Fraction | str | int) -> str:
    """Apply exact HALF_EVEN once at the six-place derived-mm boundary."""
    value = Fraction(value)
    sign = -1 if value < 0 else 1
    scaled = abs(value) * 1_000_000
    whole, remainder = divmod(scaled.numerator, scaled.denominator)
    if 2 * remainder > scaled.denominator or (2 * remainder == scaled.denominator and whole % 2):
        whole += 1
    return exact_decimal(Fraction(sign * whole, 1_000_000))


def canonical_mm(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Millimeters must be a decimal string.")
    text = value.strip()
    if len(text) > 64 or not re.fullmatch(DECIMAL_PATTERN, text):
        raise ValueError("Use a nonnegative decimal millimeter string without exponent or sign.")
    normalized = exact_decimal(Fraction(text))
    if not re.fullmatch(MM_PATTERN, normalized) or len(normalized) > 18:
        raise ValueError("Exact millimeters require at most six fractional digits and 18 characters.")
    return normalized


def normalize_measurement(text: str, default_unit: str | None = None, *, field: str = "input") -> str:
    def fail(code, message):
        raise DomainError([finding(code, message, field)])

    if not isinstance(text, str) or not text.strip() or len(text) > 100:
        fail("MEASUREMENT_INVALID", "Enter a measurement with an explicit unit.")
    if default_unit is not None and default_unit not in UNIT_FACTORS:
        fail("UNIT_UNSUPPORTED", "Supported units are mm, cm, and in.")
    source = text.strip()
    match = re.fullmatch(r'(.+?)\s*(mm|cm|in|\")', source, re.IGNORECASE)
    if match:
        body, unit = match.groups()
        unit = "in" if unit == '"' else unit.lower()
    else:
        body, unit = source, default_unit
    if unit is None:
        fail("UNIT_REQUIRED", "Declare a default unit or include mm, cm, or in.")
    body = body.strip()
    if re.fullmatch(DECIMAL_PATTERN, body):
        number = Fraction(body)
    else:
        fraction = re.fullmatch(r"(?:(\d+)\s+)?(\d+)/(\d+)", body)
        if not fraction or unit != "in":
            fail("MEASUREMENT_INVALID", "Use a decimal or an inch fraction such as 30 1/2 in.")
        whole, numerator, denominator = fraction.groups()
        denominator = int(denominator)
        if denominator not in DENOMINATORS:
            fail("FRACTION_DENOMINATOR_UNSUPPORTED", "Use denominator 1, 2, 4, 8, 16, 32, or 64.")
        if whole is not None and int(numerator) >= denominator:
            fail("MEASUREMENT_INVALID", "The fractional portion of a mixed number must be less than one.")
        number = Fraction(int(whole or 0)) + Fraction(int(numerator), denominator)
    exact = number * UNIT_FACTORS[unit]
    value = exact_decimal(exact)
    try:
        return canonical_mm(value)
    except ValueError:
        fail("MEASUREMENT_PRECISION", "The exact converted millimeters require more than six fractional digits or exceed the input size limit.")
