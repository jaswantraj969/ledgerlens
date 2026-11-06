import dataclasses

from evals.synthetic.generate import (
    DEV_LAYOUTS,
    HELD_OUT_LAYOUTS,
    LAYOUTS,
    generate_invoice,
    render_image,
)
from PIL import Image

from ledgerlens.parsing.pdfium import PdfiumParser
from ledgerlens.schema import load_schema


def test_at_least_five_distinct_layouts() -> None:
    assert len(LAYOUTS) >= 5
    labels = {(style.number_label, style.total_label) for style in LAYOUTS.values()}
    assert len(labels) == len(LAYOUTS)


def test_dev_and_held_out_layouts_do_not_overlap() -> None:
    assert set(DEV_LAYOUTS).isdisjoint(HELD_OUT_LAYOUTS)
    assert set(DEV_LAYOUTS) | set(HELD_OUT_LAYOUTS) == set(LAYOUTS)
    assert HELD_OUT_LAYOUTS


def test_default_generation_never_picks_a_held_out_layout() -> None:
    assert {generate_invoice(seed).layout for seed in range(60)} == set(DEV_LAYOUTS)


def _wording(names: tuple[str, ...]) -> set[str]:
    wording: set[str] = set()
    for name in names:
        for key, value in dataclasses.asdict(LAYOUTS[name]).items():
            if key.endswith("_label") and value:
                wording.add(value.rstrip(":").casefold())
    return wording


def test_held_out_wording_is_unique_to_the_held_out_layout() -> None:
    assert _wording(HELD_OUT_LAYOUTS).isdisjoint(_wording(DEV_LAYOUTS))


def test_no_schema_was_developed_on_held_out_wording() -> None:
    for name in ("default", "receipt_minimal"):
        schema = load_schema(name)
        labels = {label.casefold() for spec in schema.fields for label in spec.labels}
        assert labels.isdisjoint(_wording(HELD_OUT_LAYOUTS))


def test_generation_is_reproducible() -> None:
    first, second = generate_invoice(11), generate_invoice(11)
    assert first.truth == second.truth
    assert first.items == second.items


def test_every_layout_renders_its_amounts() -> None:
    for name, style in LAYOUTS.items():
        invoice = generate_invoice(21, layout=name, tax=True)
        text = " ".join(
            token.text for page in PdfiumParser().parse(invoice.pdf).pages for token in page.tokens
        )
        assert style.total_label.split()[-1] in text, name
        assert invoice.truth["tax_amount"] is not None


def test_tax_can_be_absent() -> None:
    assert generate_invoice(22, tax=False).truth["tax_amount"] is None


def test_multi_page_line_items() -> None:
    parsed = PdfiumParser().parse(generate_invoice(23, layout="modern", items=45).pdf)
    assert len(parsed.pages) == 2


def test_low_dpi_and_rotated_image_variants() -> None:
    from io import BytesIO

    pdf = generate_invoice(24, layout="classic").pdf
    low = Image.open(BytesIO(render_image(pdf, dpi=72)))
    high = Image.open(BytesIO(render_image(pdf, dpi=200)))
    rotated = Image.open(BytesIO(render_image(pdf, dpi=72, rotate=5)))
    assert high.width > low.width
    assert rotated.width > low.width
    assert rotated.height > low.height
