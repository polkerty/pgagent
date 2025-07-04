import pathlib, tempfile, json, os
import pytest
from unittest import mock

# Create an isolated HOME so registry writes don't pollute real machine
@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    yield
