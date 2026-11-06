"""Seeded synthetic invoice generator with exact ground truth.

Output is entirely fictional and is used for tests, the demo and smoke evaluation. Results
from it are reported separately and are never presented as real-dataset results.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

CENT = Decimal("0.01")
ROWS_PER_PAGE = 28
_CURRENCIES = ("USD", "EUR", "GBP", "SGD")
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d %B %Y")


@dataclass(frozen=True)
class LineItem:
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal


@dataclass
class SyntheticInvoice:
    document_id: str
    pdf: bytes
    truth: dict[str, str | None]
    items: list[LineItem] = field(default_factory=list)


def _money(value: Decimal) -> str:
    return f"{value:,.2f}"


def generate_invoice(
    seed: int, *, items: int | None = None, tax: bool | None = None
) -> SyntheticInvoice:
    rng = random.Random(seed)  # noqa: S311 - reproducible test data, not security
    fake = Faker()
    fake.seed_instance(seed)

    count = items if items is not None else rng.randint(1, 8)
    rows = []
    for _ in range(count):
        quantity = rng.randint(1, 9)
        unit_price = Decimal(rng.randint(100, 50000)) / 100
        rows.append(
            LineItem(
                description=" ".join(fake.words(nb=rng.randint(2, 3))).title(),
                quantity=quantity,
                unit_price=unit_price,
                amount=(unit_price * quantity).quantize(CENT),
            )
        )

    subtotal = sum((row.amount for row in rows), Decimal(0))
    has_tax = tax if tax is not None else rng.random() < 0.8
    tax_amount = (subtotal * Decimal("0.10")).quantize(CENT, ROUND_HALF_UP) if has_tax else None
    total = subtotal + (tax_amount or Decimal(0))
    issued = date(2023, 1, 1) + timedelta(days=rng.randint(0, 900))
    currency = rng.choice(_CURRENCIES)
    vendor = fake.company().replace(",", "")
    number = f"INV-{rng.randint(1000, 99999)}"

    summary = [("Subtotal", subtotal)]
    if tax_amount is not None:
        summary.append(("Tax", tax_amount))
    summary.append(("Total", total))

    pdf = _render(
        vendor, number, issued.strftime(rng.choice(_DATE_FORMATS)), currency, rows, summary
    )
    truth: dict[str, str | None] = {
        "vendor_name": vendor,
        "invoice_number": number,
        "invoice_date": issued.isoformat(),
        "currency": currency,
        "subtotal": str(subtotal),
        "tax_amount": None if tax_amount is None else str(tax_amount),
        "total_amount": str(total),
    }
    return SyntheticInvoice(f"synthetic-{seed}", pdf, truth, rows)


def _render(
    vendor: str,
    number: str,
    issued: str,
    currency: str,
    rows: list[LineItem],
    summary: list[tuple[str, Decimal]],
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 790, vendor)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, 760, f"Invoice Number: {number}")
    pdf.drawString(50, 744, f"Invoice Date: {issued}")
    pdf.drawString(50, 728, f"Currency: {currency}")

    y = _table_header(pdf, 696)
    for index, row in enumerate(rows):
        if index and index % ROWS_PER_PAGE == 0:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = _table_header(pdf, 790)
        pdf.drawString(50, y, row.description)
        pdf.drawRightString(330, y, str(row.quantity))
        pdf.drawRightString(430, y, _money(row.unit_price))
        pdf.drawRightString(540, y, _money(row.amount))
        y -= 18

    y -= 12
    for label, value in summary:
        pdf.drawString(380, y, label)
        pdf.drawRightString(540, y, _money(value))
        y -= 18
    pdf.save()
    return buffer.getvalue()


def _table_header(pdf: canvas.Canvas, y: float) -> float:
    pdf.drawString(50, y, "Description")
    pdf.drawRightString(330, y, "Qty")
    pdf.drawRightString(430, y, "Unit Price")
    pdf.drawRightString(540, y, "Amount")
    return y - 20
