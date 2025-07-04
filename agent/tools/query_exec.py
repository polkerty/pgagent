import psycopg, json, os

def execute_query(sql: str, port: int) -> str:
    conn = psycopg.connect(f"host=localhost port={port} dbname=postgres user=postgres")
    with conn, conn.cursor() as cur:
        cur.execute(sql)
        if cur.description:
            rows = cur.fetchall()
            return json.dumps(rows, default=str)[:4000]
        return "OK"

tool_spec = {
    "type": "function",
    "name": "execute_query",
    "description": "Run a SQL query against a managed PostgreSQL instance.",
    "parameters": {
        "type": "object",
        "properties": {
            "sql": { "type": "string" },
            "port": { "type": "integer" }
        },
        "required": ["sql", "port"],
        "additionalProperties": False
    }
}
