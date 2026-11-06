"""Business rules over a document's extracted fields."""

import re
from decimal import Decimal

from ledgerlens.fields import FieldRecord, ValidationResult

TOLERANCE = Decimal("0.01")
_LINE_AMOUNT = re.compile(r"^line_items\[\d+\]\.amount$")


def _decimal(record: FieldRecord | None) -> Decimal | None:
    if record is None or record.value_normalized is None:
        return None
    return Decimal(record.value_normalized)


def check_arithmetic(records: list[FieldRecord]) -> None:
    """Attach arithmetic results to every field a rule involves. Unknown inputs add no result."""
    by_name = {record.name: record for record in records}
    subtotal = by_name.get("subtotal")
    tax = by_name.get("tax_amount")
    total = by_name.get("total_amount")

    subtotal_value = _decimal(subtotal)
    tax_value = _decimal(tax)
    total_value = _decimal(total)
    if subtotal_value is not None and tax_value is not None and total_value is not None:
        difference = abs(subtotal_value + tax_value - total_value)
        _attach(
            [record for record in (subtotal, tax, total) if record is not None],
            "subtotal_plus_tax_equals_total",
            difference <= TOLERANCE,
            f"difference {difference}",
        )

    lines = [record for record in records if _LINE_AMOUNT.match(record.name)]
    amounts = [_decimal(record) for record in lines]
    known = [amount for amount in amounts if amount is not None]
    if subtotal is not None and subtotal_value is not None and known and len(known) == len(lines):
        difference = abs(sum(known, Decimal(0)) - subtotal_value)
        _attach(
            [subtotal, *lines],
            "line_amounts_sum_to_subtotal",
            difference <= TOLERANCE,
            f"difference {difference}",
        )


def _attach(records: list[FieldRecord], rule_id: str, passed: bool, message: str) -> None:
    result = ValidationResult(rule_id=rule_id, passed=passed, message=message)
    for record in records:
        record.validation_results.append(result)
