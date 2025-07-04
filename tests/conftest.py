import pathlib
import pytest, pathlib, json, os
from unittest import mock
from agent import registry

# Create an isolated HOME so registry writes don't pollute real machine
@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    yield


@pytest.fixture(autouse=True)
def _isolate_registry(monkeypatch, tmp_path):
    # Use a temp registry file so unit tests don't touch the real one
    monkeypatch.setattr(registry, "REG_PATH", tmp_path / "registry.json")
    yield
