"""Tests for text chunking — harvester.search.chunking.

Chunks must derive ONLY from item_versions.normalized_text, never from raw
HTML/payload.  This module verifies the chunking contract.
"""


from harvester.search.chunking import chunk_text


class TestChunkText:
    """Test suite for chunk_text()."""

    def test_empty_text_produces_no_chunks(self):
        """Empty string must yield zero chunks."""
        assert chunk_text("") == []

    def test_whitespace_only_produces_no_chunks(self):
        """Whitespace-only text must yield zero chunks."""
        assert chunk_text("   \n\t  ") == []

    def test_short_text_single_chunk(self):
        """Text shorter than chunk_size produces exactly one chunk."""
        text = "Hello world"
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text
        assert chunks[0]["chunk_index"] == 0

    def test_each_chunk_has_required_keys(self):
        """Every chunk dict must contain chunk_index, text, and token_count."""
        text = "word " * 600  # ~600 words
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        for chunk in chunks:
            assert "chunk_index" in chunk
            assert "text" in chunk
            assert "token_count" in chunk

    def test_chunk_indices_are_sequential(self):
        """chunk_index values must be 0, 1, 2, ..."""
        text = "word " * 1200
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_token_count_approximate(self):
        """token_count should be approximately len(text) / 4."""
        text = "a" * 100  # 100 chars
        chunks = chunk_text(text, chunk_size=200, overlap=10)
        assert len(chunks) == 1
        # Approximate: 100 / 4 = 25
        assert chunks[0]["token_count"] == 25

    def test_long_text_split_into_overlapping_chunks(self):
        """Long text must be split with overlapping windows."""
        # 1000 characters, chunk_size=300, overlap=50
        text = "abcdefghij" * 100  # 1000 chars
        chunks = chunk_text(text, chunk_size=300, overlap=50)
        assert len(chunks) > 1
        # Verify overlap: the end of chunk[i] should appear at the start of chunk[i+1]
        for i in range(len(chunks) - 1):
            end_of_current = chunks[i]["text"][-50:]
            start_of_next = chunks[i + 1]["text"][:50]
            assert end_of_current == start_of_next

    def test_chunks_cover_full_text(self):
        """All characters of the original text must appear in the chunks."""
        text = "x" * 800
        chunks = chunk_text(text, chunk_size=300, overlap=50)
        reconstructed = chunks[0]["text"]
        for c in chunks[1:]:
            # Remove overlap portion already accounted for
            reconstructed += c["text"][50:]
        assert reconstructed == text

    def test_chunk_text_never_from_raw_html(self):
        """Chunk text content must come from normalized_text, not raw HTML.

        This is a design contract test: chunk_text only accepts plain text,
        not HTML.  If HTML tags appear in the input, they are treated as plain
        text — the caller is responsible for passing already-extracted text.
        """
        html_like = "<html><body>Hello world</body></html>"
        chunks = chunk_text(html_like, chunk_size=500)
        # chunk_text treats its input as plain text; no HTML stripping occurs
        assert len(chunks) == 1
        assert chunks[0]["text"] == html_like

    def test_custom_chunk_size_and_overlap(self):
        """chunk_size and overlap must be respected."""
        text = "a" * 100
        chunks = chunk_text(text, chunk_size=40, overlap=10)
        # Step size = 40 - 10 = 30; ceil((100-40)/30) + 1 = 3 chunks (+ maybe 1)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk["text"]) <= 40 or chunk is chunks[-1]

    def test_overlap_zero(self):
        """Zero overlap should still produce valid chunks."""
        text = "a" * 100
        chunks = chunk_text(text, chunk_size=40, overlap=0)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk["text"]) <= 40
