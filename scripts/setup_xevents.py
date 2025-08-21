#!/usr/bin/env python3
"""
Render a minimal Extended Events setup SQL for sqlumai_capture sessions.
Usage: python scripts/setup_xevents.py > scripts/create_xevents.generated.sql
"""
from typing import Literal


def render_xevents_sql(mode: Literal["ring", "file"] = "ring") -> str:
    target = (
        "ADD TARGET package0.ring_buffer(SET max_memory=4096)"
        if mode == "ring"
        else "ADD TARGET package0.event_file(SET filename='sqlumai_capture', max_file_size=(100), max_rollover_files=(5))"
    )
    return f"""
IF EXISTS (SELECT * FROM sys.server_event_sessions WHERE name = 'sqlumai_capture')
BEGIN
  ALTER EVENT SESSION [sqlumai_capture] ON SERVER STATE = STOP;
  DROP EVENT SESSION [sqlumai_capture] ON SERVER;
END

CREATE EVENT SESSION [sqlumai_capture] ON SERVER
ADD EVENT sqlserver.rpc_completed(
    ACTION(sqlserver.client_app_name, sqlserver.client_hostname, sqlserver.server_principal_name)
),
ADD EVENT sqlserver.sql_batch_completed(
    ACTION(sqlserver.client_app_name, sqlserver.client_hostname, sqlserver.server_principal_name)
)
{target}
WITH (MAX_MEMORY=4096 KB, EVENT_RETENTION_MODE=ALLOW_SINGLE_EVENT_LOSS, MAX_DISPATCH_LATENCY=5 SECONDS, STARTUP_STATE=OFF);

ALTER EVENT SESSION [sqlumai_capture] ON SERVER STATE = START;
""".strip()


def main():
    print(render_xevents_sql("ring"))


if __name__ == "__main__":
    main()

