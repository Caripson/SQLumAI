#!/usr/bin/env python3
"""
Reads XEvent .xel files using SQL Server fn_xe_file_target_read_file via pyodbc and normalizes to JSON lines.

Environment:
- XEL_PATH_PATTERN: Server-side path pattern, e.g. C:\\ProgramData\\SQLumAI\\sqlumai_capture*.xel
- MSSQL_DSN or SQL_HOST/SQL_PORT/SQL_USER/SQL_PASSWORD/SQL_DATABASE
"""
import os
import json
from pathlib import Path


MSSQL_DSN = os.getenv("MSSQL_DSN")
SQL_HOST = os.getenv("SQL_HOST", "localhost")
SQL_PORT = os.getenv("SQL_PORT", "1433")
SQL_USER = os.getenv("SQL_USER", "sa")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "Your_strong_Pa55")
SQL_DATABASE = os.getenv("SQL_DATABASE", "master")
XEL_PATH = os.getenv("XEL_PATH_PATTERN", r"C:\\ProgramData\\SQLumAI\\sqlumai_capture*.xel")


def _connect():
    try:
        import pyodbc  # type: ignore
    except Exception:
        raise SystemExit("pyodbc not installed. Install it to read .xel via SQL Server.")
    if MSSQL_DSN:
        return pyodbc.connect(MSSQL_DSN)
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SQL_HOST},{SQL_PORT};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};Encrypt=no;TrustServerCertificate=yes"
    )


XEL_QUERY = r"""
SELECT CONVERT(XML, event_data) AS event_data
FROM sys.fn_xe_file_target_read_file(?, NULL, NULL, NULL);
"""


def parse_event_xml(xml_text: str):
    import xml.etree.ElementTree as ET
    event = ET.fromstring(xml_text)
    name = event.get('name')
    ts = event.get('timestamp')
    duration = None
    row_count = None
    cpu_time = None
    error = None
    statement = None
    action = {"client_app_name": None, "client_hostname": None, "database_name": None, "username": None}

    for a in event.iterfind('action'):  # actions
        act_name = a.get('name')
        val = a.get('value')
        action[act_name] = val

    for d in event.iterfind('data'):
        dn = d.get('name')
        val = d.get('value')
        if dn in ('statement', 'batch_text'):
            statement = val
        elif dn == 'duration':
            duration = int(val)
        elif dn == 'row_count':
            row_count = int(val)
        elif dn == 'cpu_time':
            cpu_time = int(val)
        elif dn == 'error':
            error = int(val)

    return {
        "timestamp": ts,
        "event": name,
        "database": action.get("database_name"),
        "user": action.get("username"),
        "client_app": action.get("client_app_name"),
        "client_host": action.get("client_hostname"),
        "sql_text": statement,
        "duration_ms": duration,
        "row_count": row_count,
        "cpu_time_ms": cpu_time,
        "error": error,
    }


def main():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(XEL_QUERY, XEL_PATH)
    rows = cur.fetchall()
    out_dir = Path("data/xevents/file")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "events.jsonl"
    with out_file.open("a", encoding="utf-8") as f:
        for (xml_event,) in rows:
            try:
                e = parse_event_xml(xml_event)
                f.write(json.dumps(e) + "\n")
            except Exception:
                continue
    print(f"Wrote events to {out_file}")


if __name__ == "__main__":
    main()

