from ledgerlens.confidence.features import build_features
from ledgerlens.extraction.merge import merge_sources
from ledgerlens.fields import FieldRecord
from ledgerlens.schema import load_schema

SCHEMA = load_schema("cord_receipt")


def field(name: str, value: str | None, source: str) -> FieldRecord:
    return FieldRecord(name=name, value_raw=value, value_normalized=None, source=source)


A, B, RULES = "llm_pass_a", "llm_pass_b", "deterministic"


def merged(a: str | None, b: str | None, rules: str | None) -> FieldRecord:
    records = merge_sources(
        [field("total_amount", a, A)],
        [field("total_amount", b, B)],
        [field("total_amount", rules, RULES)],
        SCHEMA,
    )
    return next(record for record in records if record.name == "total_amount")


def test_all_agree() -> None:
    record = merged("10,000", "10.000", "10000")
    assert record.value_raw == "10,000"
    assert record.source == A
    assert record.signals["agree_count"] == 3
    assert record.signals["agree_pass_a_b"] is True
    assert record.signals["agree_pass_a_deterministic"] is True


def test_two_sources_outvote_pass_a() -> None:
    record = merged("9,000", "10.000", "10000")
    assert record.value_raw == "10.000"
    assert record.source == B
    assert record.signals["agree_count"] == 2
    assert record.signals["agree_pass_a_b"] is False


def test_three_way_tie_goes_to_pass_a() -> None:
    record = merged("1,000", "2,000", "3,000")
    assert record.value_raw == "1,000"
    assert record.signals["agree_count"] == 1
    assert record.signals["sources_with_value"] == 3


def test_value_only_the_rules_found_stays_deterministic() -> None:
    record = merged(None, None, "10,000")
    assert record.source == RULES
    assert record.signals["agree_count"] == 1
    assert record.signals["agree_pass_a_b"] is None


def test_all_missing_gives_no_value() -> None:
    record = merged(None, None, None)
    assert record.value_raw is None


def test_unparsable_value_gets_no_vote() -> None:
    record = merged("not an amount", "10,000", "10,000")
    assert record.value_raw == "10,000"
    assert record.signals["agree_pass_a_b"] is None


def test_failed_pass_is_an_empty_source() -> None:
    records = merge_sources([], [field("total_amount", "5,000", B)], [], SCHEMA)
    total = next(record for record in records if record.name == "total_amount")
    assert total.value_raw == "5,000"
    assert total.source == B


def test_rows_come_from_pass_a_with_cell_agreement() -> None:
    records = merge_sources(
        [field("line_items[0].amount", "5,000", A), field("line_items[1].amount", "7,000", A)],
        [field("line_items[0].amount", "5.000", B)],
        [field("line_items[0].amount", "5,000", RULES)],
        SCHEMA,
    )
    cells = {record.name: record for record in records if record.name.startswith("line_items")}
    assert cells["line_items[0].amount"].signals["agree_count"] == 3
    assert cells["line_items[1].amount"].signals["agree_count"] == 1
    assert cells["line_items[1].amount"].signals["agree_pass_a_b"] is None


def test_rows_fall_to_pass_b_when_pass_a_has_none() -> None:
    records = merge_sources([], [field("line_items[0].amount", "5,000", B)], [], SCHEMA)
    assert [r.value_raw for r in records if r.name.startswith("line_items")] == ["5,000"]


def test_agreement_reaches_the_features_and_is_null_when_absent() -> None:
    features = build_features(merged("10,000", "10,000", None))
    assert features["agree_count"] == 2
    assert features["agree_pass_a_b"] is True
    assert features["agree_pass_a_deterministic"] is None
    plain = build_features(field("total_amount", "1", A))
    assert plain["agree_count"] is None
    assert plain["cross_pass_available"] is False
