import pathlib, json
from agent import registry

def test_add_and_remove_instance(tmp_path):
    registry.add_instance("foo", 58000, "/tmp/foo")
    data = registry.list_instances()
    assert "foo" in data
    assert data["foo"]["port"] == 58000

    registry.remove_instance("foo")
    assert "foo" not in registry.list_instances()

def test_next_free_port_unique(monkeypatch):
    # force two calls, ensure different ports
    p1 = registry.next_free_port()
    p2 = registry.next_free_port()
    assert p1 != p2
