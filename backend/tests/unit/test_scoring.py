from evals.datasets.cord import map_gold_rows
from evals.scoring import DocumentPrediction, score, to_prediction

from ledgerlens.fields import FieldRecord

HEADERS = ("total_amount", "tax_amount")
ROWS = ("description", "quantity", "unit_price", "amount")


def field(name: str, value: str | None, source: str = "llm_pass_a") -> FieldRecord:
    return FieldRecord(name=name, value_raw=value, value_normalized=None, source=source)


def records() -> list[FieldRecord]:
    return [
        field("total_amount", "10,000"),
        field("tax_amount", None),
        field("line_items[0].description", "Tea"),
        field("line_items[0].amount", "10,000"),
    ]


def scored(prediction: DocumentPrediction) -> dict[str, object]:
    return score(
        [prediction],
        {"d": {"total_amount": "10,000", "tax_amount": None}},
        {"d": [{"description": "tea", "quantity": None, "unit_price": None, "amount": "10.000"}]},
        HEADERS,
        ROWS,
    )


def test_prediction_gathers_rows_and_headers() -> None:
    prediction = to_prediction("d", records(), HEADERS)
    assert prediction.header == {"total_amount": "10,000", "tax_amount": None}
    assert prediction.rows == [{"description": "Tea", "amount": "10,000"}]
    assert prediction.failed is False


def test_fallback_is_a_failed_extraction_with_nothing_to_score() -> None:
    prediction = to_prediction("d", records(), HEADERS, fell_back=True)
    assert prediction.failed is True
    assert prediction.header == {"total_amount": None, "tax_amount": None}
    assert prediction.rows == []


def test_correct_rule_based_values_earn_no_credit_after_a_fallback() -> None:
    """The fallback's values are right, and the system must still score zero."""
    good = scored(to_prediction("d", records(), HEADERS))
    failed = scored(to_prediction("d", records(), HEADERS, fell_back=True))
    assert good["fields"]["total_amount"]["tp"] == 1  # type: ignore[index]
    assert failed["fields"]["total_amount"]["tp"] == 0  # type: ignore[index]
    assert failed["fields"]["total_amount"]["fn"] == 1  # type: ignore[index]
    assert failed["line_items_row_level"]["rows_correct"] == 0  # type: ignore[index]


def test_result_records_versions_and_labels_the_secondary_score() -> None:
    result = scored(to_prediction("d", records(), HEADERS))
    assert result["metrics_version"] == "1.1.1"
    assert result["normalization"]["version"] == "1.0"  # type: ignore[index]
    assert result["line_items_set_based"]["label"] == "set-based, ignores row alignment"  # type: ignore[index]


def test_row_level_scoring_normalises_before_matching() -> None:
    result = scored(to_prediction("d", records(), HEADERS))
    assert result["line_items_row_level"]["rows_correct"] == 1  # type: ignore[index]


def test_gold_rows_keep_cells_together() -> None:
    rows = map_gold_rows(
        {
            "menu": [
                {"nm": "Tea", "cnt": "2", "price": "5,000"},
                {"nm": ["1", "Rice"], "price": "-"},
                {"price": "-"},
            ]
        }
    )
    assert rows == [
        {"description": "Tea", "quantity": "2", "unit_price": None, "amount": "5,000"},
        {"description": "Rice", "quantity": None, "unit_price": None, "amount": None},
    ]


def test_single_menu_dict_gives_one_row() -> None:
    assert len(map_gold_rows({"menu": {"nm": "Tea"}})) == 1
    assert map_gold_rows({}) == []
