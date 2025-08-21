-- Creates an Extended Events session capturing rpc_completed and sql_batch_completed
-- Captures: timestamp, database_name, client_app_name, client_hostname, username, statement, parameter values, duration, row_count, error
IF EXISTS (SELECT * FROM sys.server_event_sessions WHERE name = 'sqlumai_capture')
    DROP EVENT SESSION [sqlumai_capture] ON SERVER;
GO

CREATE EVENT SESSION [sqlumai_capture] ON SERVER 
ADD EVENT sqlserver.rpc_completed(
    ACTION(sqlserver.client_app_name, sqlserver.client_hostname, sqlserver.database_name, sqlserver.username)
    WHERE (sqlserver.is_system = 0)
),
ADD EVENT sqlserver.sql_batch_completed(
    ACTION(sqlserver.client_app_name, sqlserver.client_hostname, sqlserver.database_name, sqlserver.username)
    WHERE (sqlserver.is_system = 0)
)
ADD TARGET package0.ring_buffer(SET max_memory = 50MB)
-- Optional file target for easier offline processing:
-- ADD TARGET package0.event_file(SET filename = N'sqlumai_capture', max_file_size=(100), max_rollover_files=(5))
WITH (MAX_MEMORY=4096 KB, EVENT_RETENTION_MODE=ALLOW_SINGLE_EVENT_LOSS, MAX_DISPATCH_LATENCY=5 SECONDS, TRACK_CAUSALITY=OFF, STARTUP_STATE=ON);
GO

ALTER EVENT SESSION [sqlumai_capture] ON SERVER STATE = START;
GO

