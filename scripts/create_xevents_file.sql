-- Creates an Extended Events session that writes to event_file for robust collection
IF EXISTS (SELECT * FROM sys.server_event_sessions WHERE name = 'sqlumai_capture_file')
    DROP EVENT SESSION [sqlumai_capture_file] ON SERVER;
GO

CREATE EVENT SESSION [sqlumai_capture_file] ON SERVER 
ADD EVENT sqlserver.rpc_completed(
    ACTION(sqlserver.client_app_name, sqlserver.client_hostname, sqlserver.database_name, sqlserver.username)
    WHERE (sqlserver.is_system = 0)
),
ADD EVENT sqlserver.sql_batch_completed(
    ACTION(sqlserver.client_app_name, sqlserver.client_hostname, sqlserver.database_name, sqlserver.username)
    WHERE (sqlserver.is_system = 0)
)
ADD TARGET package0.event_file(
    SET filename = N'C:\\ProgramData\\SQLumAI\\sqlumai_capture', max_file_size=(100), max_rollover_files=(10)
)
WITH (MAX_MEMORY=4096 KB, EVENT_RETENTION_MODE=ALLOW_SINGLE_EVENT_LOSS, MAX_DISPATCH_LATENCY=5 SECONDS, TRACK_CAUSALITY=OFF, STARTUP_STATE=ON);
GO

ALTER EVENT SESSION [sqlumai_capture_file] ON SERVER STATE = START;
GO

