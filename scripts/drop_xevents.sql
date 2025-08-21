IF EXISTS (SELECT * FROM sys.server_event_sessions WHERE name = 'sqlumai_capture')
BEGIN
    ALTER EVENT SESSION [sqlumai_capture] ON SERVER STATE = STOP;
    DROP EVENT SESSION [sqlumai_capture] ON SERVER;
END
GO

