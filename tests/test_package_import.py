"""Test that harvester package can be imported and exposes __version__."""


def test_harvester_import():
    """Assert import harvester works and exposes a string __version__."""
    import harvester

    assert hasattr(harvester, "__version__")
    assert isinstance(harvester.__version__, str)
    assert len(harvester.__version__) > 0
