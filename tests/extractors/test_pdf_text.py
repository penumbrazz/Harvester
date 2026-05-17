"""Tests for PDF text extraction."""

from io import BytesIO

from fpdf import FPDF

from harvester.extractors.pdf_text import PdfTextExtractor


def _make_pdf(pages: list[str]) -> bytes:
    """Build a valid PDF with the given text, one page per entry."""
    pdf = FPDF()
    for text in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _make_encrypted_pdf() -> bytes:
    """Build an encrypted PDF that requires a password to open."""
    pdf = FPDF()
    pdf.set_encryption(owner_password="owner")
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Secret content", new_x="LMARGIN", new_y="NEXT")
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


class TestPdfTextExtractor:
    """Tests for PDF text extraction from raw bytes."""

    def test_extracts_text_from_normal_pdf(self):
        """Normal PDF should produce readable text content."""
        pdf_bytes = _make_pdf(["Hello World from PDF"])
        extractor = PdfTextExtractor()
        output = extractor.extract(
            {"source_url": "https://example.com/doc.pdf"},
            pdf_bytes,
        )

        assert len(output.items) == 1
        item = output.items[0]
        assert "Hello World from PDF" in item.content_text
        assert item.item_type == "article"
        assert item.language == "zh"

    def test_empty_pdf_returns_no_items(self):
        """PDF with no text should not produce items."""
        # Blank page PDF - no text content
        pdf = FPDF()
        pdf.add_page()
        buf = BytesIO()
        pdf.output(buf)
        pdf_bytes = buf.getvalue()

        extractor = PdfTextExtractor()
        output = extractor.extract(
            {"source_url": "https://example.com/empty.pdf"},
            pdf_bytes,
        )

        assert len(output.items) == 0

    def test_corrupted_pdf_returns_no_items(self):
        """Corrupted PDF bytes should not raise, but return no items."""
        extractor = PdfTextExtractor()
        output = extractor.extract(
            {"source_url": "https://example.com/bad.pdf"},
            b"this is not a pdf at all",
        )

        assert len(output.items) == 0

    def test_encrypted_pdf_returns_no_items(self):
        """Encrypted PDF should return no items (not fail)."""
        pdf_bytes = _make_encrypted_pdf()
        extractor = PdfTextExtractor()
        output = extractor.extract(
            {"source_url": "https://example.com/encrypted.pdf"},
            pdf_bytes,
        )

        assert len(output.items) == 0

    def test_multi_page_pdf_concatenates_text(self):
        """Multi-page PDF should concatenate text from all pages."""
        pdf_bytes = _make_pdf(["Page one content", "Page two content"])
        extractor = PdfTextExtractor()
        output = extractor.extract(
            {"source_url": "https://example.com/multi.pdf"},
            pdf_bytes,
        )

        assert len(output.items) == 1
        assert "Page one content" in output.items[0].content_text
        assert "Page two content" in output.items[0].content_text

    def test_extracts_from_bytes_payload(self):
        """Extractor should handle bytes payload."""
        pdf_bytes = _make_pdf(["Bytes payload test"])
        extractor = PdfTextExtractor()
        output = extractor.extract(
            {"source_url": "https://example.com/test.pdf"},
            pdf_bytes,
        )

        assert len(output.items) == 1

    def test_extracts_from_str_payload(self):
        """Extractor should handle string payload (decoded bytes)."""
        pdf_bytes = _make_pdf(["String payload"])
        extractor = PdfTextExtractor()
        output = extractor.extract(
            {"source_url": "https://example.com/test.pdf"},
            pdf_bytes.decode("latin-1"),
        )

        assert len(output.items) == 1

    def test_extracts_with_source_metadata(self):
        """Extractor should populate item metadata from raw metadata."""
        pdf_bytes = _make_pdf(["Metadata test"])
        extractor = PdfTextExtractor()
        output = extractor.extract(
            {
                "source_url": "https://example.com/doc.pdf",
                "target_url": "https://example.com/files/doc.pdf",
                "external_item_id": "item-123",
            },
            pdf_bytes,
        )

        item = output.items[0]
        assert item.external_item_id == "item-123"
        assert item.original_url == "https://example.com/files/doc.pdf"
