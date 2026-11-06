"""Seeded synthetic invoice generator with exact ground truth.

Output is entirely fictional and is used for tests, the demo and smoke evaluation. Results
from it are reported separately and are never presented as real-dataset results.

DEV_LAYOUTS may be used to develop extraction rules. HELD_OUT_LAYOUTS must not: their wording
never enters a schema, and they are used only for synthetic evaluation. A test enforces this.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

import pypdfium2 as pdfium
from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

CENT = Decimal("0.01")
A4_ROWS_PER_PAGE = 28
RECEIPT_WIDTH = 226.0
RECEIPT_VENDOR_CHARS = 26
_EU_NUMBERS = str.maketrans(",.", ".,")


@dataclass(frozen=True)
class Layout:
    name: str
    number_label: str
    date_label: str
    currency_label: str | None
    subtotal_label: str
    tax_label: str
    total_label: str
    date_formats: tuple[str, ...]
    currencies: tuple[str, ...]
    eu_numbers: bool = False
    symbol_prefix: bool = False


LAYOUTS = {
    layout.name: layout
    for layout in (
        Layout(
            "classic", "Invoice Number:", "Invoice Date:", "Currency:",
            "Subtotal", "Tax", "Total",
            ("%Y-%m-%d", "%d/%m/%Y", "%d %B %Y"), ("USD", "SGD", "AUD"),
        ),
        Layout(
            "modern", "Bill No", "Issue Date", "Currency",
            "Net Amount", "VAT", "Amount Due",
            ("%d.%m.%Y", "%d %b %Y"), ("EUR", "CHF"), eu_numbers=True,
        ),
        Layout(
            "receipt", "Receipt No", "Date", None,
            "SUBTOTAL", "TAX", "TOTAL",
            ("%d/%m/%y", "%d-%m-%Y"), ("IDR",),
        ),
        Layout(
            "statement", "Ref", "Date", None,
            "Sub Total", "GST", "Grand Total",
            ("%B %d, %Y", "%d/%m/%Y"), ("EUR", "GBP"), symbol_prefix=True,
        ),
        Layout(
            "ledger", "Reference", "Dated", "Settled In",
            "Goods Value", "Sales Levy", "Payable Sum",
            ("%d %B %Y", "%Y/%m/%d"), ("USD", "NZD"),
        ),
    )
}  # fmt: skip
DEV_LAYOUTS = ("classic", "modern", "receipt", "statement")
HELD_OUT_LAYOUTS = ("ledger",)
_SYMBOLS = {"EUR": "€", "GBP": "£"}


@dataclass(frozen=True)
class LineItem:
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal


@dataclass
class SyntheticInvoice:
    document_id: str
    layout: str
    pdf: bytes
    truth: dict[str, str | None]
    items: list[LineItem] = field(default_factory=list)


def generate_invoice(
    seed: int, *, layout: str | None = None, items: int | None = None, tax: bool | None = None
) -> SyntheticInvoice:
    """Build one invoice. With no `layout`, picks from the development layouts only."""
    rng = random.Random(seed)  # noqa: S311 - reproducible test data, not security
    fake = Faker()
    fake.seed_instance(seed)
    style = LAYOUTS[layout or rng.choice(DEV_LAYOUTS)]

    rows = [_row(rng, fake) for _ in range(items if items is not None else rng.randint(1, 8))]
    subtotal = sum((row.amount for row in rows), Decimal(0))
    has_tax = tax if tax is not None else rng.random() < 0.8
    tax_amount = (subtotal * Decimal("0.10")).quantize(CENT, ROUND_HALF_UP) if has_tax else None
    total = subtotal + (tax_amount or Decimal(0))
    issued = date(2023, 1, 1) + timedelta(days=rng.randint(0, 900))
    currency = rng.choice(style.currencies)
    vendor = fake.company().replace(",", "")
    if style.name == "receipt":
        vendor = vendor[:RECEIPT_VENDOR_CHARS].strip()
    number = f"INV-{rng.randint(1000, 99999)}"

    meta = [
        (style.number_label, number),
        (style.date_label, issued.strftime(rng.choice(style.date_formats))),
    ]
    if style.currency_label is not None:
        meta.append((style.currency_label, currency))
    summary = [(style.subtotal_label, subtotal)]
    if tax_amount is not None:
        summary.append((style.tax_label, tax_amount))
    summary.append((style.total_label, total))

    money = _formatter(style, currency)
    render = _RENDERERS[style.name]
    truth: dict[str, str | None] = {
        "vendor_name": vendor,
        "invoice_number": number,
        "invoice_date": issued.isoformat(),
        "currency": currency if style.currency_label or style.symbol_prefix else None,
        "subtotal": str(subtotal),
        "tax_amount": None if tax_amount is None else str(tax_amount),
        "total_amount": str(total),
    }
    return SyntheticInvoice(
        f"synthetic-{style.name}-{seed}",
        style.name,
        render(vendor, meta, rows, summary, money),
        truth,
        rows,
    )


def render_image(pdf: bytes, *, dpi: int = 150, rotate: float = 0.0, page: int = 0) -> bytes:
    """Render a PDF page to PNG, for low-DPI and rotated scan variants."""
    document = pdfium.PdfDocument(pdf)
    image = document[page].render(scale=dpi / 72).to_pil().convert("RGB")
    document.close()
    if rotate:
        image = image.rotate(rotate, expand=True, fillcolor="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _row(rng: random.Random, fake: Faker) -> LineItem:
    quantity = rng.randint(1, 9)
    unit_price = Decimal(rng.randint(100, 50000)) / 100
    return LineItem(
        description=" ".join(fake.words(nb=rng.randint(2, 3))).title(),
        quantity=quantity,
        unit_price=unit_price,
        amount=(unit_price * quantity).quantize(CENT),
    )


def _formatter(style: Layout, currency: str):  # type: ignore[no-untyped-def]
    def money(value: Decimal) -> str:
        text = f"{value:,.2f}"
        if style.eu_numbers:
            text = text.translate(_EU_NUMBERS)
        return f"{_SYMBOLS[currency]} {text}" if style.symbol_prefix else text

    return money


def _table(pdf, rows, y, money, top, columns=(50, 330, 430, 540), font="Helvetica"):  # type: ignore[no-untyped-def]
    def header(at: float) -> float:
        pdf.drawString(columns[0], at, "Description")
        pdf.drawRightString(columns[1], at, "Qty")
        pdf.drawRightString(columns[2], at, "Unit Price")
        pdf.drawRightString(columns[3], at, "Amount")
        return at - 20

    y = header(y)
    for index, row in enumerate(rows):
        if index and index % A4_ROWS_PER_PAGE == 0:
            pdf.showPage()
            pdf.setFont(font, 11)
            y = header(top)
        pdf.drawString(columns[0], y, row.description)
        pdf.drawRightString(columns[1], y, str(row.quantity))
        pdf.drawRightString(columns[2], y, money(row.unit_price).split()[-1])
        pdf.drawRightString(columns[3], y, money(row.amount).split()[-1])
        y -= 18
    return y


def _summary(pdf, summary, x, right, y, money):  # type: ignore[no-untyped-def]
    for label, value in summary:
        pdf.drawString(x, y, label)
        pdf.drawRightString(right, y, money(value))
        y -= 18
    return y


def _classic(vendor, meta, rows, summary, money) -> bytes:  # type: ignore[no-untyped-def]
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 790, vendor)
    pdf.setFont("Helvetica", 11)
    y = 760.0
    for label, value in meta:
        pdf.drawString(50, y, f"{label} {value}")
        y -= 16
    y = _table(pdf, rows, y - 20, money, 790)
    _summary(pdf, summary, 380, 540, y - 12, money)
    pdf.save()
    return buffer.getvalue()


def _modern(vendor, meta, rows, summary, money) -> bytes:  # type: ignore[no-untyped-def]
    """Vendor on the right, metadata in a right-hand block, date listed first."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Times-Bold", 18)
    pdf.drawRightString(545, 795, vendor)
    pdf.setFont("Times-Roman", 11)
    y = 765.0
    for label, value in [meta[1], meta[0], *meta[2:]]:
        pdf.drawRightString(440, y, label)
        pdf.drawString(450, y, value)
        y -= 15
    y = _table(pdf, rows, y - 24, money, 795, font="Times-Roman")
    _summary(pdf, summary, 370, 540, y - 14, money)
    pdf.save()
    return buffer.getvalue()


def _receipt(vendor, meta, rows, summary, money) -> bytes:  # type: ignore[no-untyped-def]
    """Narrow till slip: three columns, paid and change lines after the total."""
    height = 190.0 + 16 * len(rows) + 18 * (len(summary) + 2)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(RECEIPT_WIDTH, height))
    pdf.setFont("Courier-Bold", 11)
    pdf.drawString(12, height - 24, vendor)
    pdf.setFont("Courier", 9)
    y = height - 44
    for label, value in meta:
        pdf.drawString(12, y, f"{label}: {value}")
        y -= 13
    y -= 8
    pdf.drawString(12, y, "Item")
    pdf.drawRightString(160, y, "Qty")
    pdf.drawRightString(214, y, "Amt")
    y -= 15
    for row in rows:
        pdf.drawString(12, y, row.description[:20])
        pdf.drawRightString(160, y, str(row.quantity))
        pdf.drawRightString(214, y, money(row.amount))
        y -= 15
    y = _summary(pdf, summary, 12, 214, y - 8, money)
    paid = summary[-1][1] + Decimal(5)
    _summary(pdf, [("CASH", paid), ("CHANGE", Decimal(5))], 12, 214, y, money)
    pdf.save()
    return buffer.getvalue()


def _statement(vendor, meta, rows, summary, money) -> bytes:  # type: ignore[no-untyped-def]
    """Metadata shares one line, and summary amounts carry a currency symbol."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(297, 800, vendor)
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(297, 784, "TAX INVOICE")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, 755, f"{meta[0][0]}: {meta[0][1]}")
    pdf.drawString(330, 755, f"{meta[1][0]}: {meta[1][1]}")
    y = _table(pdf, rows, 725, money, 800)
    _summary(pdf, summary, 360, 540, y - 12, money)
    pdf.save()
    return buffer.getvalue()


def _ledger(vendor, meta, rows, summary, money) -> bytes:  # type: ignore[no-untyped-def]
    """Held out. Summary comes before the table, under a footer-style vendor line."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica", 11)
    y = 800.0
    for label, value in meta:
        pdf.drawString(50, y, f"{label} / {value}")
        y -= 15
    y = _summary(pdf, summary, 300, 540, 800, money)
    y = _table(pdf, rows, min(y, 740) - 24, money, 800)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, max(y - 30, 40), vendor)
    pdf.save()
    return buffer.getvalue()


_RENDERERS = {
    "classic": _classic,
    "modern": _modern,
    "receipt": _receipt,
    "statement": _statement,
    "ledger": _ledger,
}
