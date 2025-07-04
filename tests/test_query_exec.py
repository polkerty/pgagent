from unittest import mock
import json
from agent.tools import query_exec


@mock.patch("agent.tools.query_exec.psycopg.connect")
def test_execute_query_select(mock_connect):
    conn = mock_connect.return_value

    cur = conn.cursor.return_value.__enter__.return_value
    cur.description = ("col",)
    cur.fetchall.return_value = [(1,)]

    out = query_exec.execute_query("SELECT 1", port=5432)
    assert json.loads(out) == [[1]]
