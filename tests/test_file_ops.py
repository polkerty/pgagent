import tempfile, pathlib
from agent.tools import file_ops

def test_read_file_ok(tmp_path):
    file = tmp_path / "hello.txt"
    file.write_text("world")
    assert file_ops.read_file(str(file)) == "world"
