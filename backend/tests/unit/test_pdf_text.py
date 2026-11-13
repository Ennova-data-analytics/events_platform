"""CV text extraction (pypdf): best effort, and never an exception."""
import io

from reportlab.pdfgen import canvas

from domain.services.recruitment import pdf_text
from domain.services.recruitment.pdf_text import extract_text_from_pdf


def make_pdf(*pages: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for text in pages:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_text_is_read_from_every_page():
    text = extract_text_from_pdf(make_pdf("Jane Candidate", "Five years in finance"))

    assert "Jane Candidate" in text
    assert "Five years in finance" in text
    assert text.index("Jane Candidate") < text.index("Five years in finance")


def test_text_is_capped(monkeypatch):
    monkeypatch.setattr(pdf_text, "MAX_CHARS", 10)

    assert extract_text_from_pdf(make_pdf("A long line of text in a CV")) == "A long lin"


def test_pdf_without_text_gives_none():
    assert extract_text_from_pdf(make_pdf("")) is None


def test_non_pdf_gives_none():
    assert extract_text_from_pdf(b"PK\x03\x04 a word document") is None


def test_corrupt_pdf_gives_none_instead_of_raising():
    assert extract_text_from_pdf(b"%PDF-1.4\nthis is not really a pdf") is None
    assert extract_text_from_pdf(make_pdf("Jane Candidate")[:200]) is None


def test_pdf_with_editing_restrictions_is_still_read():
    """Encrypted with an owner password only: opens without asking, but needs the AES support."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(make_pdf("Jane Candidate"))))
    writer.encrypt(user_password="", owner_password="owner-secret", algorithm="AES-256")
    buffer = io.BytesIO()
    writer.write(buffer)

    assert "Jane Candidate" in extract_text_from_pdf(buffer.getvalue())


def test_password_protected_pdf_gives_none():
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(make_pdf("Jane Candidate"))))
    writer.encrypt(user_password="secret", algorithm="AES-256")
    buffer = io.BytesIO()
    writer.write(buffer)

    assert extract_text_from_pdf(buffer.getvalue()) is None
