from ledgerlens.extraction.hybrid import choose_header, choose_rows, hybrid
from ledgerlens.fields import FieldRecord
from ledgerlens.schema import load_schema


def rec(value: str | None, source: str = "llm_pass_a", *, found: bool = True,
        label: bool | None = None, name: str = "total_amount") -> FieldRecord:  # fmt: skip
    record = FieldRecord(name=name, value_raw=value, value_normalized=value, source=source)
    record.evidence_independent = source.startswith("llm")
    record.evidence_status = (
        ("exact" if found else "not_found") if record.evidence_independent else "self_sourced"
    )
    record.signals["label_supported"] = label
    return record


def test_rules_win_when_an_llm_pass_agrees() -> None:
    chosen = choose_header("t", rec("10", "deterministic"), rec("9"), rec("10", "llm_pass_b"))
    assert (chosen.value_raw, chosen.source, chosen.signals["s4h_choice"]) == (
        "10",
        "deterministic",
        "rules",
    )
    assert chosen.signals["agree_rules_llm"] is True
    assert chosen.signals["agree_pass_a_b"] is False


def test_without_agreement_the_best_supported_verified_llm_value_wins() -> None:
    a, b = rec("9", label=False), rec("8", "llm_pass_b", label=True)
    chosen = choose_header("t", rec("10", "deterministic"), a, b)
    assert (chosen.value_raw, chosen.signals["s4h_choice"]) == ("8", "pass_b")
    assert chosen.signals["agree_rules_llm"] is False


def test_a_support_tie_goes_to_pass_a() -> None:
    chosen = choose_header("t", None, rec("9"), rec("8", "llm_pass_b"))
    assert chosen.signals["s4h_choice"] == "pass_a"


def test_agreeing_passes_add_support_to_both() -> None:
    chosen = choose_header("t", None, rec("9"), rec("9", "llm_pass_b", label=True))
    assert chosen.value_raw == "9" and chosen.signals["agree_pass_a_b"] is True


def test_unverified_llm_values_are_never_chosen() -> None:
    unparsed = rec("x")
    unparsed.value_normalized = None
    chosen = choose_header(
        "t", rec("10", "deterministic"), unparsed, rec("8", "llm_pass_b", found=False)
    )
    assert chosen.value_raw is None and chosen.signals["s4h_choice"] == "none"


def test_rules_alone_are_not_taken_without_llm_agreement() -> None:
    chosen = choose_header("t", rec("10", "deterministic"), None, None)
    assert chosen.value_raw is None
    assert chosen.signals["agree_rules_llm"] is None


def row(
    *cells: str | None, source: str = "llm_pass_a", found: bool = True
) -> dict[str, FieldRecord]:
    names = ("description", "quantity", "unit_price", "amount")
    return {
        n: rec(v, source, found=found, name=n)
        for n, v in zip(names, cells, strict=True)
        if v is not None
    }


def test_rule_rows_win_when_one_row_matches_an_llm_row() -> None:
    rules = [
        row("tea", "1", None, "5", source="deterministic"),
        row("x", "1", None, "9", source="deterministic"),
    ]
    choice, rows = choose_rows(rules, [row("tea", "1", None, "5")], [])
    assert choice == "rules" and rows == rules


def test_otherwise_the_pass_with_more_verified_descriptions_wins() -> None:
    a = [row("tea", "1", None, "5", found=False)]
    b = [
        row("tea", "1", None, "5", source="llm_pass_b"),
        row("rice", "2", None, "9", source="llm_pass_b"),
    ]
    assert choose_rows([], a, b)[0] == "pass_b"


def test_a_row_tie_goes_to_pass_a_even_when_it_has_no_rows() -> None:
    assert choose_rows([], [], [row("tea", "1", None, "5", source="llm_pass_b", found=False)]) == (
        "none",
        [],
    )
    assert choose_rows([], [], []) == ("none", [])


def test_hybrid_returns_fresh_records_with_choice_signals_only() -> None:
    schema = load_schema("cord_receipt")
    rules = [
        rec("10", "deterministic"),
        *row("tea", "1", None, "5", source="deterministic").values(),
    ]
    for record in rules[1:]:
        record.name = f"line_items[0].{record.name}"
    a = [rec("10"), *row("tea", "1", None, "5").values()]
    for record in a[1:]:
        record.name = f"line_items[0].{record.name}"
    records = {r.name: r for r in hybrid(schema, rules, a, [])}
    assert records["total_amount"].source == "deterministic"
    assert records["total_amount"].validation_results == []
    assert records["subtotal"].value_raw is None
    assert records["line_items[0].amount"].signals == {"s4h_choice": "rules"}
    assert "line_items[0].unit_price" not in records
