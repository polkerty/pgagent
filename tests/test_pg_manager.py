from unittest import mock
from agent.tools import pg_manager

@mock.patch("agent.tools.pg_manager.subprocess.check_call")
@mock.patch("agent.tools.pg_manager.subprocess.run")
@mock.patch("agent.tools.pg_manager.add_instance")
def test_fresh_clone_and_launch(add_instance, run, check_call, tmp_path, monkeypatch):
    # speed up by mocking git clone & build
    monkeypatch.setattr(pg_manager, "POSTGRES_GIT", "fake_git_url")
    # make mkdtemp return tmp_path
    monkeypatch.setattr(pg_manager.tempfile, "mkdtemp", lambda prefix: str(tmp_path))
    run.return_value = mock.Mock(stdout="build ok")
    check_call.return_value = 0
    add_instance.return_value = None
    port, workdir = pg_manager.fresh_clone_and_launch("test")
    assert port >= 56000
    assert workdir == tmp_path

@mock.patch("agent.tools.pg_manager.subprocess.check_call")
def test_edit_and_rebuild(check_call, tmp_path, monkeypatch):
    # create fake instance registry
    from agent import registry
    (tmp_path / "file.c").write_text("old")
    registry.add_instance("test", 58000, tmp_path)
    pg_manager.edit_and_rebuild("file.c", "new", "test")
    assert (tmp_path / "file.c").read_text() == "new"
