from unittest import mock
import pathlib, os
from agent.tools import code_lookup

@mock.patch.object(code_lookup, "_run_rg", return_value="match line 1")
def test_lookup_code_reference_rg(mock_rg, tmp_path, monkeypatch):
    # mock PG_DEBUGGER_SRC
    src_path = tmp_path / "pg"
    src_path.mkdir()
    monkeypatch.setenv("PG_DEBUGGER_SRC", str(src_path))
    result = code_lookup.lookup_code_reference("MyFunc")
    assert "match line 1" in result

@mock.patch.object(code_lookup, "_run_rg", return_value="")
@mock.patch.object(code_lookup, "_run_grep", return_value="")
def test_lookup_no_match(mock_grep, mock_rg, tmp_path, monkeypatch):
    src_path = tmp_path / "pg"
    src_path.mkdir()
    monkeypatch.setenv("PG_DEBUGGER_SRC", str(src_path))
    result = code_lookup.lookup_code_reference("DoesNotExist")
    assert "No definition found" in result
