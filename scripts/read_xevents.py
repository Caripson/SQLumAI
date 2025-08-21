#!/usr/bin/env python3
"""
Reads XEvents ring buffer for session 'sqlumai_capture', normalizes events to JSON lines.
Stores raw JSON in data/xevents/raw/YYYYMMDD.jsonl and updates data/aggregations/field_profiles.json

Requires: pyodbc and a working ODBC driver. If not available, the script will exit with instructions.
"""
import os
import json
import datetime as dt
from pathlib import Path

MSSQL_DSN = os.getenv("MSSQL_DSN")
SQL_HOST = os.getenv("SQL_HOST", "localhost")
SQL_PORT = os.getenv("SQL_PORT", "1433")
SQL_USER = os.getenv("SQL_USER", "sa")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "Your_strong_Pa55")
SQL_DATABASE = os.getenv("SQL_DATABASE", "master")


def _connect():
    try:
        import pyodbc  # type: ignore
    except Exception:
        raise SystemExit("pyodbc not installed. Install it or run inside an environment with ODBC drivers.")

    if MSSQL_DSN:
        conn_str = MSSQL_DSN
    else:
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SQL_HOST},{SQL_PORT};DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};PWD={SQL_PASSWORD};Encrypt=no;TrustServerCertificate=yes"
        )
    return pyodbc.connect(conn_str)


XQUERY = r"""
SELECT CAST(xet.target_data as XML) as target_data
FROM sys.dm_xe_session_targets xet
JOIN sys.dm_xe_sessions xs on xs.address = xet.event_session_address
WHERE xs.name = 'sqlumai_capture' AND xet.target_name = 'ring_buffer';
"""


def parse_ring_buffer(xml_text: str):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    for event in root.iterfind('.//event'):
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
            if dn == 'statement' or dn == 'batch_text':
                statement = val
            elif dn == 'duration':
                duration = int(val)
            elif dn == 'row_count':
                row_count = int(val)
            elif dn == 'cpu_time':
                cpu_time = int(val)
            elif dn == 'error':
                error = int(val)

        yield {
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


def save_raw(events):
    date = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    out_dir = Path("data/xevents/raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{date}.jsonl"
    with out_file.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"Wrote raw events to {out_file}")


def main():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(XQUERY)
    row = cur.fetchone()
    if not row:
        raise SystemExit("No ring buffer found. Ensure session 'sqlumai_capture' is started.")
    xml_text = row[0]
    events = list(parse_ring_buffer(xml_text))
    save_raw(events)


if __name__ == "__main__":
    main()
