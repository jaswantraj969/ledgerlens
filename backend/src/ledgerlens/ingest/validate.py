"""Upload validation, by content. The file name and declared type are never trusted."""

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath, PureWindowsPath

import pypdfium2 as pdfium
from PIL import Image, UnidentifiedImageError

from ledgerlens.core.errors import Problem

_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)
_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}
_UNSAFE = re.compile(r"[^\w.\- ]")
_NAME_LIMIT = 200
# Images are decoded in full for OCR; refuse very large pixel counts before that happens.
MAX_IMAGE_PIXELS = 40_000_000


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    mime: str
    sha256: str
    pages: int


def _reject(detail: str, code: str, status: int = 400) -> Problem:
    return Problem(status, "Upload rejected", detail, code)


def safe_filename(name: str | None) -> str:
    """Keep only a base name for display. It is never used as a path."""
    base = PureWindowsPath(PurePosixPath(name or "upload").name).name
    cleaned = _UNSAFE.sub("_", base).strip(". ")
    return cleaned[:_NAME_LIMIT] or "upload"


def _pdf_pages(data: bytes, max_pages: int) -> int:
    try:
        document = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as error:
        if "password" in str(error).casefold():
            raise _reject("Encrypted PDFs are not supported.", "pdf_encrypted") from error
        raise _reject("The PDF is damaged or incomplete.", "pdf_malformed") from error
    try:
        pages = len(document)
    finally:
        document.close()
    if pages == 0:
        raise _reject("The PDF has no pages.", "pdf_empty")
    if pages > max_pages:
        raise _reject(f"The PDF has more than {max_pages} pages.", "too_many_pages")
    return pages


def _check_image(data: bytes) -> None:
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise _reject("The image is damaged or incomplete.", "image_malformed") from error
    if width * height > MAX_IMAGE_PIXELS:
        raise _reject(f"The image has more than {MAX_IMAGE_PIXELS} pixels.", "image_too_large", 413)


def validate_upload(
    filename: str | None, data: bytes, max_bytes: int, max_pages: int
) -> ValidatedUpload:
    if not data:
        raise _reject("The file is empty.", "file_empty")
    if len(data) > max_bytes:
        raise _reject(f"The file is larger than {max_bytes} bytes.", "file_too_large", 413)
    mime = next((m for signature, m in _SIGNATURES if data.startswith(signature)), None)
    if mime is None:
        raise _reject("Only PDF, JPEG and PNG files are accepted.", "unsupported_type", 415)
    name = safe_filename(filename)
    if PurePosixPath(name).suffix.casefold() not in _EXTENSIONS[mime]:
        raise _reject("The file name does not match its contents.", "extension_mismatch", 415)
    if mime == "application/pdf":
        pages = _pdf_pages(data, max_pages)
    else:
        _check_image(data)
        pages = 1
    return ValidatedUpload(name, mime, hashlib.sha256(data).hexdigest(), pages)
