import json
from pathlib import Path

from evals.datasets.sroie import (
    SroieDocument,
    load_documents,
    split_groups,
    split_payload,
    vendor_groups,
    vendor_key,
)


def document(index: int, company: str) -> SroieDocument:
    return SroieDocument(f"sroie:{index:03}", company, "01/02/2018", "10.00")


def fixture(count: int = 60) -> list[SroieDocument]:
    """Fictional vendors, including one that dominates."""
    names = ("Amber", "Birch", "Cobalt", "Dune", "Ember", "Fjord", "Gale", "Harbor", "Ivory",
             "Juniper", "Kestrel", "Lumen")  # fmt: skip
    documents = [document(i, f"Fictional {names[i % 12]} Store") for i in range(count)]
    documents += [document(count + i, "Dominant Mart Sdn Bhd") for i in range(30)]
    return documents


def test_load_reads_key_files(tmp_path: Path) -> None:
    (tmp_path / "007.json").write_text(
        json.dumps({"company": "Fictional Co", "date": "01/02/2018", "total": "9.00"}),
        encoding="utf-8",
    )
    loaded = load_documents(tmp_path)
    assert loaded == [SroieDocument("sroie:007", "Fictional Co", "01/02/2018", "9.00")]


def test_vendor_key_ignores_case_punctuation_and_suffix() -> None:
    assert vendor_key("ACME  Mart Sdn. Bhd.") == vendor_key("acme mart sdn bhd") == "acme mart"


def test_typo_variants_join_one_group() -> None:
    groups = vendor_groups([document(1, "Fictional Hardware"), document(2, "Fictional Hardwere")])
    assert groups["sroie:001"] == groups["sroie:002"]


def test_different_vendors_stay_apart() -> None:
    groups = vendor_groups([document(1, "Fictional Hardware"), document(2, "Unrelated Bakery")])
    assert groups["sroie:001"] != groups["sroie:002"]


def test_no_vendor_crosses_splits() -> None:
    documents = fixture()
    groups = vendor_groups(documents)
    splits = split_groups(groups)
    vendor_splits: dict[int, set[str]] = {}
    for document_id, group in groups.items():
        vendor_splits.setdefault(group, set()).add(splits[document_id])
    assert all(len(names) == 1 for names in vendor_splits.values())
    assert set(splits.values()) == {"train", "calibration", "test"}


def test_split_is_reproducible_and_seed_sensitive() -> None:
    groups = vendor_groups(fixture())
    assert split_groups(groups, seed=1) == split_groups(groups, seed=1)
    assert split_groups(groups, seed=1) != split_groups(groups, seed=2)


def test_payload_never_holds_company_names() -> None:
    documents = fixture()
    text = json.dumps(split_payload(documents)).casefold()
    assert "dominant" not in text
    assert "fictional" not in text
