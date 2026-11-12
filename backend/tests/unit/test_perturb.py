import io

import numpy as np
import pytest
from evals.perturb import PERTURBATIONS, ocr_key, perturb
from PIL import Image


def _image() -> bytes:
    rng = np.random.default_rng(7)
    pixels = rng.integers(0, 256, size=(64, 96, 3), dtype=np.uint8)
    pixels[20:40, 10:80] = 0  # a dark bar, so blur has an edge to soften
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("name", sorted(PERTURBATIONS))
def test_each_perturbation_is_deterministic_and_changes_the_image(name: str) -> None:
    source = _image()
    first, second = perturb(source, name), perturb(source, name)
    assert first == second
    with Image.open(io.BytesIO(first)) as changed, Image.open(io.BytesIO(source)) as original:
        assert changed.size == original.size
        assert not np.array_equal(np.asarray(changed.convert("RGB")), np.asarray(original))


def test_stronger_severity_moves_further_from_the_original() -> None:
    source = _image()
    with Image.open(io.BytesIO(source)) as image:
        original = np.asarray(image.convert("RGB"), dtype=float)

    def distance(name: str) -> float:
        with Image.open(io.BytesIO(perturb(source, name))) as image:
            return float(np.abs(np.asarray(image.convert("RGB"), dtype=float) - original).mean())

    assert distance("blur-3.0") > distance("blur-1.5")
    assert distance("jpeg-10") > distance("jpeg-30")


def test_ocr_key_keeps_clean_ids_and_separates_perturbed_copies() -> None:
    assert ocr_key("cord-v2:test:1", None) == "cord-v2:test:1"
    assert ocr_key("cord-v2:test:1", "jpeg-10") == "cord-v2:test:1#jpeg-10"
