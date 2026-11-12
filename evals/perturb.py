"""Image perturbations for the degradation study (docs/evaluation/final-test-protocol.md).

Each perturbation is fixed in advance and deterministic: the same input bytes always give the same
output bytes, so no random seed is involved. Gaussian blur uses Pillow's GaussianBlur, whose
radius is the standard deviation in pixels; the result is saved losslessly as PNG. JPEG
compression re-encodes the image at a fixed quality with 4:2:0 chroma subsampling.
"""

import io

from PIL import Image, ImageFilter

PERTURBATIONS: dict[str, tuple[str, float]] = {
    "blur-1.5": ("gaussian_blur", 1.5),
    "blur-3.0": ("gaussian_blur", 3.0),
    "jpeg-30": ("jpeg", 30),
    "jpeg-10": ("jpeg", 10),
}


def perturb(image: bytes, name: str) -> bytes:
    kind, severity = PERTURBATIONS[name]
    with Image.open(io.BytesIO(image)) as source:
        picture = source.convert("RGB")
    output = io.BytesIO()
    if kind == "gaussian_blur":
        picture.filter(ImageFilter.GaussianBlur(radius=severity)).save(output, format="PNG")
    else:
        picture.save(output, format="JPEG", quality=int(severity), subsampling=2)
    return output.getvalue()


def ocr_key(document_id: str, perturbation: str | None) -> str:
    """OCR cache key: the clean document keeps its id, a perturbed copy gets its own entry."""
    return document_id if perturbation is None else f"{document_id}#{perturbation}"
