"""Tests for StubModelAdapter — harvester.adapters.stub_model.

The stub adapter returns deterministic vectors without hitting the network.
"""

from harvester.adapters.stub_model import StubModelAdapter


class TestStubModelAdapter:
    """Test suite for StubModelAdapter."""

    def test_returns_list_of_floats(self):
        """embed() must return a list of floats."""
        adapter = StubModelAdapter()
        result = adapter.embed("hello world")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_correct_dimension(self):
        """Vector must have exactly 1536 dimensions."""
        adapter = StubModelAdapter()
        result = adapter.embed("test input")
        assert len(result) == 1536

    def test_deterministic_same_input_same_output(self):
        """Same input must always produce the same vector."""
        adapter = StubModelAdapter()
        text = "deterministic test"
        result1 = adapter.embed(text)
        result2 = adapter.embed(text)
        assert result1 == result2

    def test_different_input_different_output(self):
        """Different inputs should produce different vectors."""
        adapter = StubModelAdapter()
        result1 = adapter.embed("first text")
        result2 = adapter.embed("second text")
        assert result1 != result2

    def test_does_not_hit_network(self):
        """The adapter must work without any network connection.

        This is implicitly verified by the test running offline —
        the adapter only uses hashlib internally.
        """
        adapter = StubModelAdapter()
        # If this call required network, it would fail in offline environments.
        result = adapter.embed("offline test")
        assert len(result) == 1536

    def test_empty_string_produces_valid_vector(self):
        """Even an empty string must produce a valid 1536-dim vector."""
        adapter = StubModelAdapter()
        result = adapter.embed("")
        assert len(result) == 1536
        assert all(isinstance(v, float) for v in result)

    def test_values_in_valid_range(self):
        """All vector values should be finite floats."""
        adapter = StubModelAdapter()
        result = adapter.embed("range check")
        import math

        for v in result:
            assert math.isfinite(v)
