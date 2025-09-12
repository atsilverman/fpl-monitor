-- ========================================
-- MONITORING LOG SCHEMA FOR SUPABASE
-- ========================================
-- This table tracks all monitoring service runs and status

CREATE TABLE IF NOT EXISTS monitoring_log (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    run_type VARCHAR(20) NOT NULL, -- 'heartbeat', 'full_refresh', 'price_check', 'live_monitor', etc.
    status VARCHAR(20) NOT NULL, -- 'success', 'error', 'warning'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    records_processed INTEGER DEFAULT 0,
    changes_detected INTEGER DEFAULT 0,
    notifications_sent INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB, -- Store additional context like gameweek, categories refreshed, etc.
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_monitoring_log_service ON monitoring_log(service_name);
CREATE INDEX IF NOT EXISTS idx_monitoring_log_started_at ON monitoring_log(started_at);
CREATE INDEX IF NOT EXISTS idx_monitoring_log_status ON monitoring_log(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_log_service_started ON monitoring_log(service_name, started_at);

-- Comments
COMMENT ON TABLE monitoring_log IS 'Tracks all monitoring service runs, heartbeats, and status for outage detection';
COMMENT ON COLUMN monitoring_log.service_name IS 'Name of the monitoring service (e.g., main_monitor, price_monitor, live_monitor)';
COMMENT ON COLUMN monitoring_log.run_type IS 'Type of monitoring run (heartbeat, full_refresh, price_check, live_monitor, etc.)';
COMMENT ON COLUMN monitoring_log.status IS 'Result status (success, error, warning)';
COMMENT ON COLUMN monitoring_log.duration_seconds IS 'How long the monitoring run took in seconds';
COMMENT ON COLUMN monitoring_log.records_processed IS 'Number of database records processed';
COMMENT ON COLUMN monitoring_log.changes_detected IS 'Number of changes detected during this run';
COMMENT ON COLUMN monitoring_log.notifications_sent IS 'Number of notifications sent during this run';
COMMENT ON COLUMN monitoring_log.metadata IS 'Additional context like gameweek, categories refreshed, etc.';

-- ========================================
-- USEFUL VIEWS FOR MONITORING STATUS
-- ========================================

-- View: Latest status of each service
CREATE OR REPLACE VIEW monitoring_status AS
SELECT 
    service_name,
    run_type,
    status,
    started_at,
    completed_at,
    duration_seconds,
    records_processed,
    changes_detected,
    notifications_sent,
    error_message,
    CASE 
        WHEN completed_at IS NULL THEN 'running'
        WHEN started_at > NOW() - INTERVAL '5 minutes' THEN 'recent'
        WHEN started_at > NOW() - INTERVAL '1 hour' THEN 'stale'
        ELSE 'offline'
    END as health_status
FROM monitoring_log
WHERE id IN (
    SELECT MAX(id) 
    FROM monitoring_log 
    GROUP BY service_name
)
ORDER BY started_at DESC;

-- View: Service uptime summary
CREATE OR REPLACE VIEW monitoring_uptime AS
SELECT 
    service_name,
    COUNT(*) as total_runs,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_runs,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_runs,
    ROUND(
        COUNT(CASE WHEN status = 'success' THEN 1 END)::DECIMAL / COUNT(*) * 100, 2
    ) as success_rate_percent,
    MAX(started_at) as last_run,
    MIN(started_at) as first_run
FROM monitoring_log
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY service_name
ORDER BY last_run DESC;

-- ========================================
-- HELPER FUNCTIONS
-- ========================================

-- Function: Log monitoring run start
CREATE OR REPLACE FUNCTION log_monitoring_start(
    p_service_name VARCHAR(50),
    p_run_type VARCHAR(20),
    p_metadata JSONB DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    log_id INTEGER;
BEGIN
    INSERT INTO monitoring_log (service_name, run_type, status, metadata)
    VALUES (p_service_name, p_run_type, 'running', p_metadata)
    RETURNING id INTO log_id;
    
    RETURN log_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Log monitoring run completion
CREATE OR REPLACE FUNCTION log_monitoring_complete(
    p_log_id INTEGER,
    p_status VARCHAR(20),
    p_records_processed INTEGER DEFAULT 0,
    p_changes_detected INTEGER DEFAULT 0,
    p_notifications_sent INTEGER DEFAULT 0,
    p_error_message TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE monitoring_log 
    SET 
        status = p_status,
        completed_at = NOW(),
        duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER,
        records_processed = p_records_processed,
        changes_detected = p_changes_detected,
        notifications_sent = p_notifications_sent,
        error_message = p_error_message
    WHERE id = p_log_id;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- SAMPLE QUERIES FOR MONITORING
-- ========================================

-- Check if any service is offline (no runs in last hour)
-- SELECT * FROM monitoring_status WHERE health_status = 'offline';

-- Check latest run of each service
-- SELECT * FROM monitoring_status;

-- Check service uptime over last 7 days
-- SELECT * FROM monitoring_uptime;

-- Check for recent errors
-- SELECT * FROM monitoring_log WHERE status = 'error' AND started_at > NOW() - INTERVAL '24 hours' ORDER BY started_at DESC;
